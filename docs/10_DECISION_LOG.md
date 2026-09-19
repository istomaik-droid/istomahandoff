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
