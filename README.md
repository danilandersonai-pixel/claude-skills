# daniil-skills

Личный набор из **17 скиллов** для Claude Code — чтобы они были доступны не только на локальной машине, но и в облачном / мобильном Claude Code.

> 📇 Живой реестр всех инструментов (скиллы, плагины, MCP-серверы) — в [`CATALOG.md`](./CATALOG.md). Обновляется скиллом `tools-catalog`.

Репозиторий устроен **универсально** и работает двумя способами:

1. **Как marketplace-плагин** — устанавливается через `/plugin` и доступен глобально в любой сессии.
2. **Как репозиторий со скиллами** — при работе с этим репо Claude Code сам подхватывает `.claude/skills/`.

---

## Состав скиллов

| Скилл | Назначение |
|-------|------------|
| `commit` | Автокоммит, пуш и бэкап `.env` |
| `deploy` | Ручной деплой проекта через Docker + Git |
| `docker` | Контейнеризация проектов |
| `install-mcp` | Установка / настройка / отладка MCP-серверов |
| `proxy` | Подключение через прокси при региональных блокировках |
| `ssh-connect` | Надёжное SSH-подключение через expect |
| `tavily` | Извлечение контента из URL и веб-поиск через Tavily API |
| `worktree` | Управление git worktrees для параллельной работы |
| `ui-ux-pro-max` | UI/UX-дизайн: стили, палитры, шрифты, стеки |
| `telegram-bot` | Разработка Telegram-ботов |
| `telegram-bot-builder` | Архитектура и масштабирование Telegram-ботов |
| `aiogram-framework` | Боты на aiogram v3 |
| `fullstack-developer` | React, Node.js, БД, fullstack-архитектура |
| `find-skills` | Поиск и установка новых скиллов |
| `game-setup-and-config` | Настройка игр на Phaser 4 |
| `agent-spec-mobile-react-native` | Спецификации мобильных приложений на React Native |
| `tools-catalog` | Картотека всех инструментов (скиллы/плагины/MCP) → `CATALOG.md` |

---

## Способ 1. Установка как плагин (глобально)

В любой сессии Claude Code (десктоп, web, мобильный):

```
/plugin marketplace add danilandersonai-pixel/claude-skills
/plugin install daniil-skills@daniil-skills
```

После установки все 17 скиллов доступны в любом проекте.

## Способ 2. Скиллы из репозитория

Если открыть/подключить этот репозиторий как рабочий проект в облачном Claude Code, скиллы автоматически читаются из `.claude/skills/` (симлинк на `plugins/daniil-skills/skills/`).

---

## Структура репозитория

```
claude-skills/
├── .claude-plugin/
│   └── marketplace.json          # манифест маркетплейса
├── plugins/
│   └── daniil-skills/
│       ├── .claude-plugin/
│       │   └── plugin.json        # манифест плагина
│       └── skills/                # 17 скиллов (источник)
│           ├── commit/SKILL.md
│           └── ...
├── .claude/
│   └── skills -> ../plugins/daniil-skills/skills   # для проектного режима
└── README.md
```

## Обновление

Изменил скилл локально — синхронизируй и запушь:

```bash
# скопировать обновлённые скиллы из ~/.claude/skills
cp -RL ~/.claude/skills/<имя> plugins/daniil-skills/skills/
git add -A && git commit -m "update: <имя>" && git push
```
