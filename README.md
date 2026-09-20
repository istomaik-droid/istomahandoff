# istomahandoff

Универсальный протокол управляемой разработки с ИИ-агентом.

## Что это

Набор процессуальных правил, шаблонов и handoff-документов для любых задач
по написанию кода: greenfield, bugfix, refactor, migration, infrastructure, data.

## Главное правило

НЕТ ЯВНОГО РЕШЕНИЯ ВЛАДЕЛЬЦА = НЕТ ПРАВА НА ДЕЙСТВИЕ

Критерий явности: решение оформлено по шаблону docs/37, имеет DEC-ID,
scope и allowed/forbidden. Спор о том, было ли решение, трактуется как
отсутствие решения.

## Что изменилось в 2.0

- docs/44_ENFORCEMENT_LIMITS.md — честная граница между конвенцией и
  техникой: протокол сам себя не enforced. Уровни E0–E3.
- docs/45_PROTOCOL_LEVELS.md — уровни P0 (R0–R1) / P1 (R2–R3) / P2 (R4–R5)
  вместо одного универсального чеклиста на всё.
- docs/46_OWNER_MANDATE_FATIGUE.md — мандаты замещения владельца,
  обязательный evidenceReadHash для acceptance, sampling-audit против
  rubber-stamping.
- docs/47_VERSION_MIGRATION.md — правила перехода между версиями протокола
  для незавершённых работ.
- docs/10_DECISION_LOG.md — evidenceReadHash обязателен для ACCEPTANCE/RELEASE.
- docs/09_ACTIVE_STATE.md — поля protocol.version/level/enforcement.
- Антипаттерны: «markdown-контракт = enforcement», «один чеклист на всё»,
  «acceptance одной фразой».

## Структура

- `istomahandoff.md` — полный мастер-документ.
- `docs/` — правила, разбитые по темам (00–47).
- `templates/` — шаблоны для заполнения.
- `agents/` — инструкции для ИИ-агента (контракт, preflight, progress,
  code discipline, подключение рантаймов).
- `skills/` — вызываемые процедуры протокола: preflight, decision, handoff,
  incident, verify.
- `tools/` — protocol_lint.py: самопроверка согласованности протокола.
- `mcp_server/` — MCP-сервер протокола (resources/prompts/tools поверх
  канона); подключение — `.mcp.json.example` и agents/AGENT_RUNTIMES.md.
- `evidence/` — место для receipts и snapshots.

## С чего начать

1. Прочитать `istomahandoff.md` и `docs/44_ENFORCEMENT_LIMITS.md`.
2. Заполнить `templates/PROJECT_PROFILE.yaml` (protocol, enforcement, deputy).
3. Прочитать `agents/AGENT_CONTRACT.md`; подключение к рантайму
   (Kimi Code / Claude Code / Codex) — `agents/AGENT_RUNTIMES.md`.
4. Завести `docs/09_ACTIVE_STATE.md` и `docs/10_DECISION_LOG.md`.
5. Назначить уровень enforcement не ниже E1 для любых задач от R2.
6. Не начинать implementation без owner authorization.

## Порядок доверия источников

1. `docs/10_DECISION_LOG.md`
2. `docs/09_ACTIVE_STATE.md`
3. `docs/11_HANDOFF_MEMO.md`
4. `docs/08_DELIVERY_ARCHITECTURE.md`
5. ADR
6. Immutable evidence

## Версия

2.0 от 2026-09-14. История изменений — в docs/42_MAINTENANCE.md.
