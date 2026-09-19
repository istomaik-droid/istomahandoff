---
name: handoff
description: Генерирует handoff memo по docs/36 из фактического состояния репозитория
type: prompt
whenToUse: При передаче работы, завершении сессии, смене агента или перед длительным перерывом
---

Собери handoff memo по docs/36_HANDOFF.md и templates/HANDOFF.md.

1. Прочитай docs/09_ACTIVE_STATE.md, docs/10_DECISION_LOG.md, docs/11_HANDOFF_MEMO.md.
2. Собери фактуру: git log/status, состояние тестов, открытые blockers.
3. Заполни минимальный пакет docs/36:
   - ACTIVE_STATE (включая activeMandates, если действует deputy);
   - последние DEC-ID и verified rollback anchor (VERIFIED | NOT_VERIFIED | MISSING);
   - что сделано / что дальше / блокеры;
   - записи MANDATE-XXXX, если deputy действует (docs/46);
   - версия протокола (docs/47).
4. FAIL фиксируется до исправления; skipped/inconclusive не маскируются.
5. Запиши memo в docs/11_HANDOFF_MEMO.md (или файл по шаблону) и укажи путь в ответе.

Evidence пишется сразу, частью того же коммита — не батчем задним числом (docs/31).
