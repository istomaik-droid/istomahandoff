# MCP-сервер протокола istomahandoff

MCP-сервер (stdio) поверх канона протокола: нормы в коде не дублируются,
сервер читает `docs/`, `agents/`, `skills/` из репозитория.

## Что даёт

- Resources: `protocol://docs/<NN_NAME>` — документы docs/,
  `protocol://agents/<NAME>` — инструкции agents/.
- Prompts: 5 процедур из skills/ (preflight, decision, handoff, incident,
  verify) — тела SKILL.md как prompt messages.
- Tools: `protocol_lint`, `record_decision`, `get_active_state`,
  `evidence_hash`, `validate_transition` (парсит docs/16),
  `list_expired`, `audit_sample` (docs/46), `protocol_version` (docs/42).

## Запуск

```bash
pip install "mcp<2"
python mcp_server/server.py   # stdio-транспорт
```

Подключение к рантаймам — см. `.mcp.json.example` и раздел «MCP-сервер»
в `agents/AGENT_RUNTIMES.md`. Корень репозитория — родитель `mcp_server/`
либо переменная окружения `ISTOMAHANDOFF_ROOT` (один сервер может
обслуживать другой проект без копирования).

## Ограничения (честно)

- Сервер работает с правами агента, который его вызывает; отдельной
  изоляции нет.
- Enforcement — только для добросовестного пути (E1–E2 по docs/44):
  сервер напоминает, валидирует и отказывает на уровне своих tools,
  но adversarial-агент может просто не вызывать его или править файлы
  напрямую. Это не защита от adversarial (docs/44).
- `record_decision` пишет только в docs/10 и только append; поле
  receiptSha256 сервер не вычисляет (null — заполняется владельцем).
- State machine и enum типов решений парсятся из docs/16 и docs/10 при
  каждом вызове; при смене формата этих файлов парсер нужно пересмотреть.
