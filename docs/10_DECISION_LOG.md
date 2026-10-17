# 10. Decision log

Append-only.

```yaml
- id: DEC-XXXX
  date: <ISO8601>
  owner: <NAME>            # или deputy с mandateRef
  type: BOUNDARY | IMPLEMENTATION | ACCEPTANCE | BACKUP | RELEASE | STOP | PAUSE | CORRECTION | MIGRATION | MANDATE
  scope: <STAGE / WORKITEM>
  decision: <текст>
  allowed: []
  forbidden: []
  expiresAt: <ISO8601 | null>
  receiptSha256: <sha256>
  evidenceReadHash: <sha256 | null>   # ОБЯЗАТЕЛЕН для ACCEPTANCE/RELEASE
  mandateRef: <MANDATE-XXXX | null>   # обязателен для deputy
```

## Записи

```yaml
- id: DEC-0001
  date: 2026-09-19
  owner: OWNER
  type: CORRECTION
  scope: docs/, agents/, istomahandoff.md
  decision: Владелец одним решением утвердил сверку внутренней согласованности
    протокола: 25 исправлений (FIX-01..FIX-25) по рекомендациям аудита —
    устранение противоречий 42↔47, обязательность evidenceReadHash на P1+,
    унификация формулировок мандата deputy, preflight, checkpoint P0,
    списков запретов агента, исправление битых ссылок и состояний.
  allowed:
    - редакторские правки согласованности
  forbidden:
    - изменение главного правила
    - изменение state machine (кроме исправления имени несуществующего состояния)
    - изменение risk classes
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0002
  date: 2026-09-19
  owner: OWNER
  type: CORRECTION
  scope: docs/, agents/, templates/
  decision: Владелец утвердил обогащение протокола по боевому образцу
    реального проекта (CLAUDE.md production-системы): 10 добавок
    ENR-1..ENR-10 — прецеденты inline у правил, правила параллельных
    сессий агентов, честность докладов, timing evidence, рецепт
    минимального E1, pre-deploy gate чистого дерева, staging-паттерн,
    standing rules без переспрашивания, маппинг протокол→проект
    в PROJECT_PROFILE, карта проекта и грабли среды в RUNBOOK.
  allowed:
    - добавочные правила и поля шаблонов
  forbidden:
    - изменение главного правила
    - изменение state machine
    - изменение risk classes
    - изменение существующих норм
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0003
  date: 2026-09-19
  owner: OWNER
  type: CORRECTION
  scope: skills/, README.md, docs/42
  decision: Владелец утвердил добавление набора скиллов протокола —
    вызываемых процедур поверх конвенций: skills/preflight (чеклист
    по уровню с фактическими данными), skills/decision (оформление
    решения по docs/37 с записью в лог), skills/handoff (memo по
    docs/36 из фактического состояния), skills/incident (отчёт +
    правило-прецедент), skills/verify (verify-команда профиля,
    результат как evidence с хэшем).
  allowed:
    - новые скиллы в skills/
    - строка про skills/ в README и change record
  forbidden:
    - изменение главного правила
    - изменение state machine
    - изменение risk classes
    - изменение существующих норм
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0004
  date: 2026-09-19
  owner: OWNER
  type: CORRECTION
  scope: tools/, docs/09, docs/42, README.md
  decision: Владелец утвердил добавление protocol lint —
    tools/protocol_lint.py: самопроверка согласованности протокола
    (существование ссылок docs/NN, agents/, templates/, skills/;
    полнота enum состояний в docs/09; схема DEC-записей; непрерывность
    нумерации stop conditions; детект ссылок на несуществующие
    состояния). Lint обязателен после изменений документов (docs/42).
    Первый прогон выявил и исправлен: неполный enum состояний в docs/09.
  allowed:
    - новый скрипт в tools/
    - полный enum состояний в docs/09
    - строки про lint в docs/42 и README
  forbidden:
    - изменение главного правила
    - изменение state machine
    - изменение risk classes
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0005
  date: 2026-09-19
  owner: OWNER
  type: CORRECTION
  scope: docs/05, docs/31, docs/34, docs/42, templates/PROJECT_PROFILE.yaml
  decision: Владелец утвердил вписывание compression gateway (класс
    инструментов сжатия контекста агента, напр. Paritok) в протокол:
    включение gateway в цепочку агент→LLM — provider-класс, запрещено
    без owner decision (docs/05); сжатый контекст не является evidence,
    работа через gateway фиксируется в evidence/handoff (docs/31);
    восстановление контекста — только по документам, не по истории
    переписки, сжатой или нет (docs/34). Конкретное использование
    конкретного gateway — отдельное R5-решение.
  allowed:
    - добавочные правила про compression gateway
  forbidden:
    - изменение главного правила
    - изменение state machine
    - изменение risk classes
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0006
  date: 2026-09-19
  owner: OWNER
  type: IMPLEMENTATION
  scope: пилот compression gateway на рабочей машине владельца
  decision: Владелец разрешил установку и пилот self-host compression
    gateway Paritok (Apache 2.0) на своей машине: установка Ollama и
    pip-пакета paritok[proxy,toolselect], модель paritok-4b-v1 (~2.5GB,
    локально), прокси на 127.0.0.1:8080. Пилот — сессии ИИ-агентов на
    этой машине. Spend: 0 (self-host, без API-ключей и hosted-режима).
  allowed:
    - установка Ollama, paritok, модели на эту машину
    - запуск прокси на loopback
    - пилотное проксирование сессий агентов через gateway
    - фиксация факта работы через gateway в evidence (docs/31)
  forbidden:
    - hosted-режим gpu_server и API-ключи paritok.com
    - отправка production-секретов через gateway
    - использование вне пилота без отдельного решения
    - вывод gateway за пределы loopback
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0007
  date: 2026-09-19
  owner: OWNER
  type: IMPLEMENTATION
  scope: mcp_server/, .mcp.json.example, agents/AGENT_RUNTIMES.md, README.md, docs/42
  decision: Владелец утвердил сборку MCP-сервера протокола: resources
    (канон docs/agents), prompts (5 скиллов), tools — protocol_lint,
    record_decision (валидация схемы, автоназначение DEC-ID, отказ
    ACCEPTANCE/RELEASE без evidenceReadHash), get_active_state,
    evidence_hash, validate_transition (по docs/16), list_expired
    (просроченные решения/мандаты), audit_sample (docs/46),
    protocol_version. Enforcement для добросовестного пути (E1–E2),
    не защита от adversarial (docs/44).
  allowed:
    - новый сервер в mcp_server/
    - пример конфигурации .mcp.json.example
    - строки в README, AGENT_RUNTIMES, docs/42
  forbidden:
    - изменение главного правила
    - изменение state machine
    - изменение risk classes
    - дублирование норм протокола в коде (сервер читает канон из docs/)
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0008
  date: 2026-09-20
  owner: OWNER
  type: IMPLEMENTATION
  scope: mcp_server/, .github/workflows/, docs/42
  decision: Владелец утвердил расширение MCP-сервера enforcement-tools
    и CI: checkpoint_create (git tag с readback, норма docs/19),
    pre_deploy_check (чистое дерево, гейт docs/38), GitHub Actions
    workflow (protocol_lint + smoke-тест сервера на каждый push).
  allowed:
    - новые tools в mcp_server/server.py
    - .github/workflows/
    - строка в docs/42
  forbidden:
    - изменение главного правила
    - изменение state machine
    - изменение risk classes
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0009
  date: 2026-09-20
  owner: OWNER
  type: IMPLEMENTATION
  scope: mcp_server/, VPS владельца
  decision: Владелец разрешил network effect: размещение MCP-сервера
    на своём VPS (там уже работает VPN владельца) для личного
    использования. Режим: streamable-http, биндинг ТОЛЬКО на
    VPN-интерфейс; публичная доступность, домен и TLS не требуются.
    Spend: 0 (VPS и домен уже есть).
  allowed:
    - HTTP-транспорт в mcp_server/server.py (MCP_TRANSPORT/HOST/PORT)
    - развёртывание на VPS по SSH: клон репозитория, pip, systemd-юнит
    - биндинг на VPN-интерфейс
  forbidden:
    - биндинг на публичный интерфейс (0.0.0.0 / публичный IP)
    - открытие порта наружу (firewall)
    - hosted-режим для третьих лиц
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0010
  date: 2026-09-20
  owner: OWNER
  type: CORRECTION
  scope: mcp_server/, dl-server (187.124.114.130)
  decision: Корректировка DEC-0009 по фактуре сервера: VPN на dl-server —
    xray (прокси уровня приложения), VPN-интерфейса для биндинга нет
    (только lo и eth0). Способ изоляции меняется: MCP-сервер слушает
    только 127.0.0.1 на VPS, доступ — через SSH-туннель
    (ssh -L) с машины владельца. Публичная поверхность не увеличивается.
    Хост подтверждён владельцем: dl-server (там же VPN и статистика
    обновлений; DreamLaser и xray не затрагиваются).
  allowed:
    - клон репозитория в /opt/istomahandoff на dl-server
    - venv + pip install mcp на dl-server
    - systemd-юнит istomahandoff-mcp (127.0.0.1:8000)
    - SSH-туннель с машины владельца
  forbidden:
    - биндинг на eth0/0.0.0.0
    - открытие порта 8000 в firewall
    - изменения в сервисах dreamlaser, xray, nginx
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0011
  date: 2026-09-20
  owner: OWNER
  type: IMPLEMENTATION
  scope: mcp_server/server.py, dl-server (/opt/istomahandoff), GitHub repo
  decision: Владелец утвердил авто-синхронизацию decision log: после
    записи решения record_decision делает git commit + push (только
    docs/10_DECISION_LOG.md). На dl-server создаётся deploy key с
    write-доступом к репозиторию istomahandoff для push с VPS.
    При недоступности GitHub запись не теряется: решение остаётся
    закоммиченным локально на VPS, tool честно возвращает pushed=false.
  allowed:
    - авто commit+push docs/10 в record_decision
    - deploy key (write) для репозитория на dl-server
    - git identity в /opt/istomahandoff на dl-server
  forbidden:
    - commit чего-либо кроме docs/10_DECISION_LOG.md
    - push force, переписывание истории
    - использование deploy key для других репозиториев
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0012
  date: 2026-09-21
  owner: OWNER
  type: IMPLEMENTATION
  scope: dl-server (/opt/istomahandoff)
  decision: Развёртывание MCP-сервера на VPS завершено и проверено сквозным вызовом через SSH-туннель; включена авто-синхронизация decision log (commit+push при записи, DEC-0011). Эта запись — живой тест авто-синхронизации.
  allowed:
    - работа службы istomahandoff-mcp на 127.0.0.1:8000
  forbidden:
    - биндинг на публичный интерфейс
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0013
  date: 2026-09-20
  owner: OWNER
  type: CORRECTION
  scope: docs/05, docs/30, docs/33, docs/41
  decision: Владелец утвердил правила стоимости по анализу реальных
    журналов субагентов (расход = ходы × длина контекста; cache-read
    доминирует): модель по классу задачи — механические на дешёвой,
    расследования на сильной, дорогое финальное ревью раз на ветку
    (docs/05); лимит ~150 ходов на work item, затем handoff новому
    агенту (docs/33 п. 30); повторяемая проверка — одним гейт-скриптом
    (docs/30); метрики turns/cache-read в docs/41. Paritok: пилот
    отдельно и ПОСЛЕ внедрения этих правил, с замером по /stats;
    постоянное использование — отдельное решение по данным пилота.
  allowed:
    - добавочные правила стоимости в docs/05, 30, 33, 41
  forbidden:
    - изменение главного правила
    - изменение state machine
    - изменение risk classes
    - одновременное внедрение правил ходов и compression gateway
      без раздельного замера
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0014
  date: 2026-09-20
  owner: OWNER
  type: CORRECTION
  scope: agents/AGENT_RUNTIMES.md, docs/44
  decision: Владелец утвердил покрытие остальных рантаймов и адаптацию
    под модель: инструкции для Cursor (.cursor/rules) и Gemini CLI
    (GEMINI.md); пометка про HTTP-транспорт Codex (fallback — локальный
    stdio); правило «слабая модель → P0 + enforcement в MCP-tools,
    минимум длинных инструкций»; в docs/44 п. 6 — уровень enforcement
    определяется возможностями рантайма, а не моделью.
  allowed:
    - разделы Cursor и Gemini CLI в AGENT_RUNTIMES
    - правило адаптации под модель
    - пункт 6 в docs/44
  forbidden:
    - изменение главного правила
    - изменение state machine
    - изменение risk classes
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0015
  date: 2026-10-01
  owner: OWNER
  type: IMPLEMENTATION
  scope: docs/48_DOC_INDEX.md, docs/INDEX.md, docs/40, docs/42,
    agents/AGENT_CONTRACT.md, tools/protocol_lint.py, README.md
  decision: Владелец утвердил индекс документов и чтение по требованию
    как меру экономии контекста агента: docs/INDEX.md — оглавление
    с тирами must-read/reference, одна строка на документ; docs/48 —
    норма: не читать reference-документы «про запас», ссылка вместо
    пересказа, одно правило — один документ, запись в INDEX обязательна
    для нового документа; антипаттерны 20–22 (docs/40); обязанность
    чтения по требованию в AGENT_CONTRACT; protocol_lint проверяет
    покрытие INDEX.
  allowed:
    - docs/48_DOC_INDEX.md и docs/INDEX.md
    - правки docs/40, docs/42, README.md
    - пункт про чтение по требованию в agents/AGENT_CONTRACT.md
    - проверка INDEX в tools/protocol_lint.py
  forbidden:
    - изменение главного правила
    - изменение state machine
    - изменение risk classes
    - отмена или изменение DEC-0013 (правила стоимости, отложенный
      пилот compression gateway)
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0016
  date: 2026-10-16
  owner: OWNER
  type: IMPLEMENTATION
  scope: mcp_server/, tests/, .github/workflows/, agents/AGENT_RUNTIMES.md,
    docs/42, docs/10 (эта запись), AGENTS.md, CLAUDE.md, .gitignore;
    вне репозитория — пользовательский конфиг Kimi владельца, второй
    локальный клон протокола, ruleset ветки master на GitHub
  decision: Владелец утвердил пакет 1 по итогам анализа 15.10 — запись
    решения только туда, куда задумано (подробности — mcp_server/README.md,
    «Запись решений»). Корректирует DEC-0011: авто commit+push docs/10
    выключен по умолчанию и включается ISTOMAHANDOFF_AUTOSYNC=1 только у
    единственного писателя журнала; писатель этим решением не назначается,
    до отдельного решения переменная нигде не включается и инстанс на VPS
    не обновляется. record_decision строже проверяет поля и помечен
    requiresUserInteraction, git-tools сообщают проверенный репозиторий,
    тесты pytest и шаг в CI, mcp закреплён; собственный AGENTS.md
    протокола, образец CLAUDE.md пилота переименован и остаётся вне git.
    Вне репозитория: в пользовательском конфиге Kimi оставлены только tools
    чтения канона; во втором локальном клоне снят staged-дубль решения
    другого проекта (с бэкапом патча), клон обновляется после слияния; на
    master включается ruleset — запрет force-push и удаления. Класс риска
    R4 (путь записи полномочий); фактический enforcement — E0 плюс pytest и
    protocol_lint в CI и просмотр диффа владельцем в pull request; работа
    ниже требуемого для R4 уровня E2 принята владельцем (docs/44 п.4,
    docs/45 п.4).
  allowed:
    - правки mcp_server/server.py, mcp_server/README.md,
      mcp_server/requirements.txt
    - tests/ и шаг pytest в .github/workflows/
    - разделы «Размещение» и «Подключение» в agents/AGENT_RUNTIMES.md
    - AGENTS.md, CLAUDE.md (импорт AGENTS.md), .gitignore
    - строка 2.13 в docs/42
    - ветка, commit, push и pull request в GitHub
    - ruleset master на GitHub: запрет force-push и удаления
    - список tools сервера в пользовательском конфиге Kimi (с бэкапом)
    - второй локальный клон: снятие staged-дубля (с бэкапом) и обновление
  forbidden:
    - изменение главного правила
    - изменение state machine
    - изменение risk classes
    - изменение формата записей docs/10
    - force-push и переписывание истории
    - вызов record_decision и checkpoint_create на реальных клонах
    - включение ISTOMAHANDOFF_AUTOSYNC и обновление инстанса на VPS
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0017
  date: 2026-10-17
  owner: OWNER
  type: IMPLEMENTATION
  scope: mcp_server/server.py, mcp_server/README.md, tools/protocol_lint.py,
    tests/, .gitattributes, docs/31, skills/verify, docs/42,
    docs/10 (эта запись)
  decision: Владелец утвердил пакет «честные гейты» по итогам анализа 15.10
    (подробности — mcp_server/README.md, «Гейты»). pre_deploy_check
    считает изменения по git status -z: кириллица, пробелы, файлы внутри
    новых каталогов и обе стороны переименования без ложного STOP;
    own_files — относительно корня репозитория; длинные списки обрезаются
    со счётчиками. checkpoint_create отказывает при незакоммиченных
    изменениях отслеживаемых файлов (запись решения коммитится до
    checkpoint) и ставит annotated tag (нужна git identity репозитория).
    validate_transition: условный запрет docs/16 на шаге цепочки —
    CONDITIONAL с forbiddenWhen, аварийный переход с обобщённым источником —
    CONDITIONAL с requiresState, прыжок через стадии — FORBIDDEN (docs/33
    п.21); docs/16 не меняется. protocol_lint проверяет записи docs/10:
    все внутри блока «## Записи», DEC-ID уникальны и растут (мандат — запись
    DEC с type MANDATE, номер MANDATE-XXXX — в тексте), type из enum схемы,
    sha256 у ACCEPTANCE/RELEASE, существующая дата ISO8601 в expiresAt;
    дата раньше предыдущей — только предупреждение (история не правится).
    Хэш evidence — sha256 байтов файла в репозитории, evidence без
    EOL-конверсии (.gitattributes); skills/verify ссылается на эту норму.
    Класс риска R3 (смешанный scope R2–R3 — по высшему, docs/12 п.5);
    фактический enforcement — E0 плюс pytest и protocol_lint в CI и
    просмотр диффа владельцем в pull request; работа ниже требуемого для
    R3 уровня E1 принята владельцем (docs/44 п.4).
  allowed:
    - правки mcp_server/server.py и mcp_server/README.md
    - проверки записей docs/10 в tools/protocol_lint.py
    - tests/ (включая общий conftest.py)
    - .gitattributes с правилом evidence/** -text
    - раздел «Хэш evidence» в docs/31
    - п.5 skills/verify — ссылка на «Хэш evidence» docs/31
    - строка 2.14 в docs/42
    - ветка, commit, push и pull request в GitHub
  forbidden:
    - изменение главного правила
    - изменение state machine (docs/16)
    - изменение risk classes
    - изменение формата записей docs/10
    - ослабление вердиктов гейтов сверх перечисленного в decision
    - force-push и переписывание истории
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
- id: DEC-0018
  date: 2026-10-17
  owner: OWNER
  type: IMPLEMENTATION
  scope: mcp_server/server.py, mcp_server/README.md, tools/protocol_lint.py,
    tools/instance_init.py, tests/, agents/AGENT_RUNTIMES.md, README.md,
    AGENTS.md, .mcp.json.example, .gitignore, docs/09, docs/11, docs/33,
    docs/34, docs/47, docs/INDEX.md, docs/42, templates/PROJECT_PROFILE.yaml,
    adr/ADR-0001-kit-instance.md, docs/10 (эта запись), теги kit-vX.Y
  decision: Владелец принял ADR-0001 «кит ↔ экземпляр» (подход «два
    корня») и пакет П1 по нему. Канон — кит, в котором лежит сервер (только
    чтение); проект — абсолютный путь из ISTOMAHANDOFF_PROJECT, единственного
    ключа записи; CLAUDE_PROJECT_DIR — только чтение и сверка; с
    ISTOMAHANDOFF_ROOT сервер не стартует. Tools экземпляра без проекта, с
    проектом-китом или внутри кита (сравнение по идентичности каталогов),
    без docs/10 проекта или с docs/09, docs/10, ведущими в кит по ссылке,
    отказывают (fail-closed); канон доступен всегда.
    record_decision и checkpoint_create отказывают также, если канон лежит в
    корне проекта или его git-репозитория, кит не отдельный git-клон (без
    git запись закрыта), был изменён на месте при старте, изменён или
    обновлён после старта сервера, и при вызове по HTTP. Enum типов — из
    схемы docs/10 кита; docs/10 наружу (ресурс, read_canon) — без записей
    кита. Новое: tool read_canon; protocol_version — версия проекта и
    ревизия кита; protocol_lint --project с детектором импорта записей
    протокола; tools/instance_init.py. Minor-миграция по docs/47 п.5
    выровнена в docs/33 п.29, docs/34 п.12 (единственное исключение из п.1),
    docs/47 п.4 и docs/09; в docs/11 — событие PROTOCOL_MIGRATED; шаблоны
    docs/09 и PROJECT_PROFILE — protocol.version "<SEMVER>"; правило тегов
    kit-vX.Y — в docs/42. AGENT_RUNTIMES — установленный кит, подключение
    проектов, ключ записи только в проектном конфиге. Annotated-теги
    kit-vX.Y на коммиты, добавившие строку версии в docs/42: kit-v2.4
    (43c119f), kit-v2.5 (4e7bf4d),
    kit-v2.6 (ca74278), kit-v2.7 (18c3ea1), kit-v2.8 (8958022), kit-v2.9
    (69d53cd), kit-v2.10 (f0c85ca), kit-v2.11 (c9658be), kit-v2.12
    (966cf80), kit-v2.13 (5ad31fe), kit-v2.14 (d4c777c), kit-v2.15 — коммит
    master со строкой 2.15 после слияния; у 1.0–2.3 коммитов в истории нет —
    без тегов. Класс риска R3 (смешанный scope R2–R3 — по высшему, docs/12
    п.5); фактический enforcement — E0 плюс pytest и protocol_lint в CI и
    просмотр диффа владельцем в pull request; работа ниже требуемого для R3
    уровня E1 принята владельцем (docs/44 п.4).
  allowed:
    - правки mcp_server/server.py и mcp_server/README.md
    - режим --project и детектор импорта в tools/protocol_lint.py
    - новый tools/instance_init.py
    - tests/ (включая общий conftest.py)
    - agents/AGENT_RUNTIMES.md, README.md, AGENTS.md, .mcp.json.example, .gitignore
    - docs/09 (шаблон version, правило миграции), docs/11 (событие PROTOCOL_MIGRATED), docs/33 п.29, docs/34 п.12, docs/47 п.4, строка docs/09 в docs/INDEX.md, правило тегов в docs/42
    - templates/PROJECT_PROFILE.yaml (шаблон version)
    - adr/ADR-0001-kit-instance.md со статусом accepted
    - строка 2.15 в docs/42
    - ветка, commit, push и pull request в GitHub
    - annotated-теги kit-v2.4…kit-v2.15 и их push
  forbidden:
    - изменение главного правила
    - изменение state machine (docs/16)
    - изменение risk classes
    - изменение формата записей docs/10
    - установка кита на машине и правка конфигов рантаймов и проектов (П2)
    - миграция экземпляров (П3 и дальше)
    - обновление инстанса на VPS
    - force-push и переписывание истории
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
```

## Правила

1. Чат не единственный источник критического решения.
2. Каждое решение имеет ID.
3. Решение без scope не действительно.
4. Решение без allowed/forbidden не действительно.
5. Решение действует только в указанной границе.
6. ACCEPTANCE/RELEASE без evidenceReadHash невалидны: владелец обязан
   зафиксировать хэш evidence, который он прочитал (docs/46).
7. Решение deputy вне scope мандата или после expiry — невалидно.
8. Спор о факте решения трактуется как отсутствие решения до разрешения
   владельцем.
9. Решение типа MIGRATION фиксирует переход work item между версиями
   протокола (docs/47).
