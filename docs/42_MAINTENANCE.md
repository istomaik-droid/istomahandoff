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

Каждая новая строка change record — annotated-тег `kit-vX.Y` на коммит
master, в котором она появилась; push тега — по решению владельца.

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
| 2.6 | 2026-09-20 | MCP-сервер протокола (DEC-0007): mcp_server/server.py — resources (канон), prompts (скиллы), tools: protocol_lint, record_decision (отказ ACCEPTANCE/RELEASE без evidenceReadHash), get_active_state, evidence_hash, validate_transition, list_expired, audit_sample, protocol_version; enforcement добросовестного пути (E1–E2) |
| 2.7 | 2026-09-20 | Enforcement-tools + CI (DEC-0008): checkpoint_create (git tag с readback, docs/19), pre_deploy_check (чистое дерево, docs/38); GitHub Actions: protocol_lint + smoke-тест сервера на push |
| 2.8 | 2026-09-20 | Размещение MCP-сервера: ISTOMAHANDOFF_ROOT — один сервер обслуживает любой проект; схема размещения (пользовательский/проектный конфиг) в AGENT_RUNTIMES |
| 2.9 | 2026-09-20 | HTTP-режим MCP-сервера (DEC-0009): streamable-http через MCP_TRANSPORT/HOST/PORT для размещения на VPS владельца; биндинг только VPN/loopback, публичный запрещён |
| 2.10 | 2026-09-20 | Правила стоимости (DEC-0013, по журналам субагентов): модель по классу задачи (docs/05), лимит ~150 ходов на work item (docs/33 п.30), гейт-скрипт (docs/30), метрики стоимости (docs/41); пилот compression gateway — отдельно и после |
| 2.11 | 2026-09-20 | Покрытие рантаймов (DEC-0014): Cursor и Gemini CLI в AGENT_RUNTIMES, пометка Codex HTTP; адаптация под возможности модели (слабая → P0 + enforcement в tools); docs/44 п. 6 — уровень от рантайма, не от модели |
| 2.12 | 2026-10-01 | Индекс документов (DEC-0015): docs/INDEX.md — оглавление с тирами must-read/reference; docs/48 — чтение по требованию, ссылка вместо пересказа, одно правило — один документ; антипаттерны 20–22; lint проверяет покрытие INDEX |
| 2.13 | 2026-10-16 | Безопасная запись решений (DEC-0016): авто commit+push docs/10 только по ISTOMAHANDOFF_AUTOSYNC=1 у единственного писателя — с отказом при отсоединённом HEAD, чужих правках docs/10 и отставании от upstream, проверкой состава коммита, push без чужих коммитов и откатом записи при сбое коммита; строгая проверка полей record_decision; requiresUserInteraction у record_decision и checkpoint_create; repo в ответах git-tools; pytest в CI, mcp закреплён; AGENT_RUNTIMES: корень сервера, пользовательский конфиг только с enabledTools чтения канона; AGENTS.md протокола |
| 2.14 | 2026-10-17 | Честные гейты (DEC-0017): pre_deploy_check по git status -z (кириллица, пробелы, новые каталоги, переименования), own_files относительно корня репозитория; checkpoint_create — отказ при незакоммиченных отслеживаемых файлах, annotated tag; validate_transition — CONDITIONAL для условного запрета на шаге цепочки (forbiddenWhen) и для аварийных переходов с обобщённым источником (requiresState), прыжок через стадии и остальные запреты docs/16 — FORBIDDEN; protocol_lint — инварианты записей docs/10; .gitattributes evidence/** -text, норма хэша evidence в docs/31, skills/verify ссылается на неё |
| 2.15 | 2026-10-17 | Кит и экземпляр (DEC-0018, ADR-0001): сервер с двумя корнями — канон из кита сервера (только чтение), проект — ISTOMAHANDOFF_PROJECT (единственный ключ записи), CLAUDE_PROJECT_DIR — только чтение и сверка, ISTOMAHANDOFF_ROOT снят; tools экземпляра fail-closed; запись закрыта, если в корне проекта лежит канон, кит не отдельный клон, изменён или обновлён после старта, а также в HTTP-режиме; enum типов — из схемы кита, docs/10 наружу — без записей кита; read_canon; protocol_version — версия проекта и ревизия кита; protocol_lint --project с детектором импорта записей протокола; tools/instance_init.py; minor-миграция по docs/47 п.5 в docs/34 п.12, docs/47 п.4 и docs/09; AGENT_RUNTIMES — установленный кит и подключение проектов |
| 2.16 | 2026-10-19 | Установка кита (DEC-0019, П2 по ADR-0001): AGENT_RUNTIMES — слои MCP-конфигов Kimi Code (пользовательский, .mcp.json корня репозитория, .kimi-code/mcp.json каталога сессии; поздний целиком заменяет запись с тем же именем, проектные — только в доверенном workspace), один .mcp.json проекта на Claude Code и Kimi Code, Claude Code передаёт CLAUDE_PROJECT_DIR stdio-серверу, ключ local scope Claude Code зависит от регистра буквы диска |
