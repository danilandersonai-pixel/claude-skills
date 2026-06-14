#!/usr/bin/env python3
"""Сканер картотеки инструментов Claude Code.

Собирает доступные СКИЛЛЫ, ПЛАГИНЫ и MCP-СЕРВЕРЫ из файловой системы
(локальный режим) и печатает их единой Markdown-таблицей.

Важно: в облачном Claude Code часть инструментов инжектится харнессом и
НЕ видна в файловой системе. Скрипт даёт базовый слой из файлов; «живые»
инструменты текущей сессии Claude добавляет поверх (см. SKILL.md).

Использование:
    python3 catalog.py                 # печать в stdout
    python3 catalog.py --out FILE ...  # ещё и записать в указанные файлы
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()


def read_frontmatter(skill_md: Path):
    """Достаёт name/description из YAML-фронтматтера SKILL.md."""
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    # тело фронтматтера между первой и второй линией '---'
    parts = text.split("\n")
    fm_lines = []
    started = False
    for line in parts:
        if line.strip() == "---":
            if not started:
                started = True
                continue
            break
        if started:
            fm_lines.append(line)
    def unquote(val):
        val = val.strip()
        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            val = val[1:-1]
        return val

    def grab(key):
        """Значение ключа из фронтматтера; поддерживает многострочные
        блочные скаляры (| >) и свёрнутые продолжения с отступом."""
        for i, line in enumerate(fm_lines):
            m = re.match(rf"^{key}:\s*(.*)$", line)
            if not m:
                continue
            inline = m.group(1).strip()
            # собрать продолжения: строки с отступом после ключа
            cont = []
            for nxt in fm_lines[i + 1:]:
                if nxt.strip() == "":
                    continue
                if nxt[:1] in (" ", "\t"):  # отступ → продолжение значения
                    cont.append(nxt.strip())
                    continue
                break  # строка без отступа → новый ключ
            if inline in ("|", ">", "|-", ">-", "|+", ">+", ""):
                return " ".join(cont)
            return unquote(" ".join([inline] + cont))
        return ""

    return {"name": grab("name"), "description": grab("description")}


def find_skill_roots():
    """Каталоги, под которыми могут лежать */SKILL.md."""
    roots = [
        HOME / ".claude" / "skills",
        HOME / ".claude" / "plugins",
        Path.cwd() / ".claude" / "skills",
    ]
    # репо-источник, если запускаемся внутри claude-skills
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "plugins" / "daniil-skills" / "skills"
        if cand.is_dir():
            roots.append(cand)
            break
    return [r for r in roots if r.exists()]


def collect_skills():
    seen = {}
    for root in find_skill_roots():
        for skill_md in root.rglob("SKILL.md"):
            fm = read_frontmatter(skill_md)
            if not fm:
                continue
            name = fm["name"] or skill_md.parent.name
            # первый найденный выигрывает (порядок roots = приоритет)
            if name not in seen:
                seen[name] = fm["description"]
    return dict(sorted(seen.items()))


def collect_plugins():
    plugins = {}
    proot = HOME / ".claude" / "plugins"
    if proot.exists():
        for pj in proot.rglob("plugin.json"):
            try:
                data = json.loads(pj.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            name = data.get("name") or pj.parent.parent.name
            plugins.setdefault(name, data.get("description", ""))
    return dict(sorted(plugins.items()))


def _merge_mcp(target, servers):
    if isinstance(servers, dict):
        for name in servers:
            target.setdefault(name, "")


def collect_mcp():
    servers = {}
    # 1) claude mcp list
    try:
        out = subprocess.run(
            ["claude", "mcp", "list"],
            capture_output=True, text=True, timeout=20,
        )
        for line in out.stdout.splitlines():
            m = re.match(r"^([A-Za-z0-9_.\-]+):\s", line)
            if m:
                servers.setdefault(m.group(1), "")
    except (OSError, subprocess.SubprocessError):
        pass
    # 2) ~/.claude.json (top-level + per-project)
    cj = HOME / ".claude.json"
    if cj.exists():
        try:
            data = json.loads(cj.read_text(encoding="utf-8"))
            _merge_mcp(servers, data.get("mcpServers"))
            for proj in (data.get("projects") or {}).values():
                if isinstance(proj, dict):
                    _merge_mcp(servers, proj.get("mcpServers"))
        except (OSError, json.JSONDecodeError):
            pass
    # 3) settings.json + project .mcp.json
    for cfg in [HOME / ".claude" / "settings.json", Path.cwd() / ".mcp.json"]:
        if cfg.exists():
            try:
                data = json.loads(cfg.read_text(encoding="utf-8"))
                _merge_mcp(servers, data.get("mcpServers"))
            except (OSError, json.JSONDecodeError):
                pass
    return dict(sorted(servers.items()))


def find_mcp_registry():
    """Путь к mcp-catalog.json из репо claude-mcp (источник правды по MCP)."""
    env = os.environ.get("CLAUDE_MCP_CATALOG")
    cands = [Path(os.path.expanduser(env))] if env else []
    cands += [
        Path("/home/user/claude-mcp/mcp-catalog.json"),
        HOME / "claude-mcp" / "mcp-catalog.json",
    ]
    # рядом с корнем репо claude-skills (../claude-mcp/…)
    here = Path(__file__).resolve()
    for parent in here.parents:
        sib = parent.parent / "claude-mcp" / "mcp-catalog.json"
        if sib.exists():
            cands.append(sib)
            break
    for c in cands:
        if c and c.exists():
            return c
    return None


def collect_mcp_registry():
    """Серверы из mcp-catalog.json репо claude-mcp: {name: description}."""
    path = find_mcp_registry()
    if not path:
        return {}, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, None
    out = {}
    for s in data.get("servers", []):
        name = s.get("name")
        if name:
            out[name] = s.get("description", "")
    return dict(sorted(out.items())), path


def trunc(text, limit=160):
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def md_table(rows):
    if not rows:
        return "_(не найдено в файловой системе — см. примечание ниже)_\n"
    out = ["| Инструмент | Описание |", "|---|---|"]
    for name, desc in rows.items():
        out.append(f"| `{name}` | {trunc(desc)} |")
    return "\n".join(out) + "\n"


def build():
    skills = collect_skills()
    plugins = collect_plugins()
    registry, reg_path = collect_mcp_registry()
    # локальные/проектные конфиги — то, чего ещё нет в реестре claude-mcp
    local_mcp = {k: v for k, v in collect_mcp().items() if k not in registry}
    mcp = {**registry, **local_mcp}
    src = f" · MCP-реестр: `{reg_path}`" if reg_path else " · MCP-реестр не найден"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    parts = [
        "# 🧰 Картотека инструментов Claude Code",
        "",
        f"_Сгенерировано: {now} · файловый слой (`catalog.py`){src}_",
        "",
        f"## Скиллы ({len(skills)})",
        "",
        md_table(skills),
        f"## Плагины ({len(plugins)})",
        "",
        md_table(plugins),
        f"## MCP-серверы ({len(mcp)})",
        "",
        md_table(mcp),
        "---",
        "> ⚠️ В облачном/мобильном Claude Code часть скиллов и MCP-серверов "
        "инжектится харнессом и не видна этому скрипту. Claude дополняет "
        "таблицу инструментами текущей сессии при генерации картотеки.",
        "> MCP-реестр читается из `mcp-catalog.json` репо `claude-mcp` "
        "(подключи его к сессии, чтобы серверы подхватывались автоматически).",
        "",
    ]
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", action="append", default=[],
                    help="путь для записи (можно несколько раз)")
    args = ap.parse_args()
    text = build()
    for raw in args.out:
        path = Path(os.path.expanduser(raw))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"[catalog] записано: {path}", file=sys.stderr)
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
