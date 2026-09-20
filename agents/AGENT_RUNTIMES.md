# Agent runtimes: как подключить протокол

Канон — файлы в этом репозитории: `agents/`, `skills/`, `docs/`, `templates/`.
Каждый рантайм получает (1) главный файл инструкций и (2) скиллы — по своему
механизму. Содержимое одинаковое, различается только размещение.

## Главный файл инструкций (минимум, одинаков для всех)

```text
Этот проект работает по протоколу istomahandoff (docs/, agents/).
Главное правило: НЕТ ЯВНОГО РЕШЕНИЯ ВЛАДЕЛЬЦА = НЕТ ПРАВА НА ДЕЙСТВИЕ.
Перед работой прочитай agents/AGENT_CONTRACT.md и выполни обязательный
первый ответ. Действия: skills/preflight, decision, handoff, incident,
verify — по ситуации (whenToUse в каждом SKILL.md).
```

## Kimi Code

- Главный файл: `AGENTS.md` в корне проекта — вставить блок выше.
- Скиллы (project scope): скопировать `skills/*` в `.kimi-code/skills/`
  проекта. Общие для всех проектов — в `~/.kimi-code/skills/` (user scope).
- Вызов: Skill `preflight`, `decision`, `handoff`, `incident`, `verify`.

## Claude Code

- Главный файл: `CLAUDE.md` в корне проекта — вставить блок выше.
- Скиллы: скопировать `skills/*` в `.claude/skills/` проекта
  (формат SKILL.md + frontmatter совместим). Либо оформить как plugin
  для установки во все проекты.
- Вызов: `/preflight`, `/decision`, `/handoff`, `/incident`, `/verify`.

## Codex / GPT

- Главный файл: `AGENTS.md` в корне проекта — вставить блок выше.
- Механизма скиллов нет: тела `skills/*/SKILL.md` включаются в AGENTS.md
  как разделы «При <условие из whenToUse> — выполни:» со ссылкой на файл
  или с inline-копией процедуры.
- Вызов: по имени процедуры в тексте («выполни preflight»).

## MCP-сервер

MCP-сервер — предпочтительный способ, скиллы-копии — fallback.
Сервер (`mcp_server/server.py`, stdio) отдаёт канон docs/ и agents/ как
resources, процедуры skills/ как prompts и добавляет tools (protocol_lint,
record_decision, validate_transition и др. — см. `mcp_server/README.md`).
Нормы в коде не дублируются: сервер читает файлы репозитория.

- Kimi Code: скопировать `.mcp.json.example` в `.mcp.json` проекта
  (stdio, `python mcp_server/server.py`, запуск из корня репозитория).
- Claude Code: тот же `.mcp.json` в корне проекта, либо
  `claude mcp add istomahandoff -- python mcp_server/server.py`.
- Codex: секция `mcp_servers` в `config.toml` с той же командой запуска.

Enforcement сервера — только для добросовестного пути (E1–E2, docs/44).

## Правила инстанцирования

1. Файлы копируются, не перемещаются: канон остаётся в репозитории протокола.
2. Расхождение копии с каноном — канон прав; копия обновляется при смене
   версии протокола (docs/42, docs/47).
3. Проектная конкретика (verify_command, staging, журнал) — только через
   `templates/PROJECT_PROFILE.yaml`, не правкой скопированных скиллов.
4. Если рантайм не поддерживает ни скиллы, ни главный файл — протокол
   работает как E0-конвенция: агент обязан прочитать agents/ сам,
   enforcement отсутствует (docs/44).
