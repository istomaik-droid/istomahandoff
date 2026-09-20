# 42. Maintenance

Документ обновляется при изменении process law, topology, sequence.

Checkpoint обновляется только после recorded owner decision.

Historical statements не переписываются.

Изменение документа не открывает implementation gate.

External agent называет прочитанную версию.

После изменения: structural, path, port, encoding, contradiction checks +
`python tools/protocol_lint.py` (0 errors — обязательно).

Изменение версии протокола НЕ мигрирует in-flight work items
автоматически, кроме minor-миграции по правилам docs/47.

## Change record

| Версия | Дата | Изменение |
| --- | --- | --- |
| 1.0 | 2026-09-13 | Создан универсальный протокол |
| 2.0 | 2026-09-14 | docs/44 границы enforcement (E0–E3); docs/45 уровни P0/P1/P2; docs/46 мандаты, evidenceReadHash, sampling audit; docs/47 миграция версий; критерий явности решения; stop conditions 24–29; антипаттерны 15–19; метрики authority |
| 2.1 | 2026-09-19 | Сверка внутренней согласованности (решение владельца, 25 исправлений): автомиграция minor (42↔47), evidenceReadHash на P1, NEXT_WORK_ITEM_LOCKED, унификация мандата deputy / preflight / checkpoint P0 / списков запретов агента; agents/AGENT_CODE_DISCIPLINE.md |
| 2.2 | 2026-09-19 | Обогащение по боевому образцу (DEC-0002, ENR-1..ENR-10): прецеденты inline, параллельные сессии, честность докладов, timing evidence, рецепт E1, pre-deploy gate, staging-паттерн, standing rules, маппинг протокол→проект, карта и грабли в RUNBOOK |
| 2.3 | 2026-09-19 | Скиллы протокола (DEC-0003): skills/preflight, decision, handoff, incident, verify — вызываемые процедуры поверх конвенций; agents/AGENT_RUNTIMES.md — подключение к Kimi Code / Claude Code / Codex |
| 2.4 | 2026-09-19 | Protocol lint (DEC-0004): tools/protocol_lint.py — самопроверка согласованности (ссылки, state machine, DEC-схема, нумерация); полный enum состояний в docs/09; lint обязателен после изменений (docs/42) |
| 2.5 | 2026-09-19 | Compression gateway (DEC-0005): включение gateway агент→LLM — provider-класс, только owner decision (docs/05); сжатый контекст ≠ evidence, фиксация gateway в evidence/handoff (docs/31); recovery только по документам (docs/34) |
