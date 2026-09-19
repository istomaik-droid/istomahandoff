# istomahandoff

## Универсальный протокол управляемой разработки с ИИ-агентом

| Поле | Значение |
| --- | --- |
| Версия | 2.0 |
| Дата | 2026-09-14 |
| Язык | Русский |
| Аудитория | Product Owner, разработчик, ИИ-агент, архитектор, QA, security/privacy/legal reviewer, аудитор выборки |
| Назначение | Единый процесс: кто решает, что разрешено, как доказывать результат, как защищаться от самовольного агента и как передавать работу |
| Область применения | Любой репозиторий, продукт, миграция, багфикс, рефакторинг, инфраструктура, data-задача |
| Сила документа | Процессуальная конвенция и handoff. Не является разрешением на implementation, deployment, spend, доступ к production или изменение данных. Не является техническим enforcement — см. docs/44 |

## 1. Главное правило

**ИИ-агент является исполнителем и аналитиком, но никогда не является источником полномочий.**

Если действие не разрешено владельцем явно, оно запрещено.

**Критерий явности.** Решение считается явным, только если оно:
1. оформлено по шаблону из docs/37 (или осмысленному эквиваленту);
2. имеет DEC-ID и записано в docs/10_DECISION_LOG.md;
3. содержит scope и allowed/forbidden;
4. для ACCEPTANCE/RELEASE — содержит evidenceReadHash прочитанного evidence.

**Спор о факте решения.** Если агент считает, что решение было, а владелец — что нет, действие запрещено до разрешения спора владельцем. Молчание владельца — не разрешение.

Следствия:

1. Активна только одна явно разрешённая граница работы.
2. Следующий stage никогда не открывается автоматически.
3. Acceptance не разрешает checkpoint автоматически.
4. Checkpoint не разрешает следующий stage автоматически.
5. Documentary readiness не есть implementation authorization.
6. Local synthetic PASS не есть pilot/production readiness.
7. UI не источник полномочий.
8. Агент не расширяет scope.
9. FAIL/STOP/INCONCLUSIVE не переименовываются в PASS.
10. История и evidence не переписываются.
11. Acceptance/RELEASE решение без evidenceReadHash невалидно.
12. Enforcement-уровень среды не ниже требуемого для risk class (docs/44).

НЕТ ЯВНОГО РЕШЕНИЯ ВЛАДЕЛЬЦА = НЕТ ПРАВА НА ДЕЙСТВИЕ

## 2. Роли

- Product Owner — единственный authority.
- Owner Deputy — действует только в пределах действующего мандата (docs/46); R5, release, product boundary и spend мандатом не покрываются.
- Agent — исполнитель без authority.
- Developer — выполняет принятый work package.
- Technical Reviewer — human code review.
- Sampling Auditor — периодическая выборочная перепроверка решений владельца (docs/46).
- Security / Privacy / Legal / Data / Ops — закрывают только свои области.

## 3. Термины

См. `docs/` — каждый термин раскрыт в соответствующем файле.

## 4. Порядок доверия источников

1. `docs/10_DECISION_LOG.md`
2. `docs/09_ACTIVE_STATE.md`
3. `docs/11_HANDOFF_MEMO.md`
4. `docs/08_DELIVERY_ARCHITECTURE.md`
5. ADR
6. Immutable evidence

При конфликте: последнее явное решение владельца → `ACTIVE_STATE` → accepted overlay → historical. Неразрешимый конфликт → `STOPPED_CONTEXT_CONFLICT`.

## 5. Ограничение рабочего пространства

Работать только в разрешённом корне. Не сканировать соседние каталоги. Каждую shell-команду — с явным cwd. Проверять resolved path. Не идти по symlink/junction. Не делать recursive delete/reset/checkout без разрешения. Не откатывать чужие изменения. При незапланированном изменении — stop.

## 6. С чего начинается работа

Шаги 0–8 описаны в `docs/00_…`–`docs/08_…`. В TRIAGE, до DESIGN_READY, фиксируются
protocol level (docs/45) и enforcement level (docs/44) в docs/09_ACTIVE_STATE.md.

## 7. Каноническая outcome-последовательность

| Порядок | Тип | Результат |
| ---: | --- | --- |
| 0 | Foundation | Domain boundary, identity, authority |
| 1 | Entry | Onboarding, intake, approval evidence |
| 2 | Commitment | Effective status, immutable baseline |
| 3 | Production Baseline | Context, actor, time/budget baseline |
| 4 | Field Truth | Fact/evidence, accept/reject/correct |
| 5 | Money & Decision | Source-linked facts, variance, decision |
| 6 | Closure | Export/recovery, offboarding, bounded telemetry |

Один primary work item. Skip/reorder/merge/parallel — отдельное owner decision. Foundation PASS не наследуется.

## 8. Risk classes и уровни протокола

| Класс | Пример | Действия | Уровень протокола |
| --- | --- | --- | --- |
| R0 | Опечатка | Trace | P0 |
| R1 | Локальный рефакторинг | Tests + review | P0 |
| R2 | Логика внутри boundary | Tests + review + acceptance | P1 |
| R3 | API/схема/миграция/зависимость | Owner review + integration + ADR | P1 |
| R4 | Данные/authority/security | Professional review + owner decision | P2 |
| R5 | Provider/license/contractor/production | Отдельное spend/release decision | P2 |

Уровни протокола P0/P1/P2 и enforcement E0–E3 определены в docs/44 и docs/45.
Смешанный scope — по высшему классу. Понизить уровень может только владелец.

## 9. State machine

INTAKE
-> TRIAGE
-> DESIGN_READY
-> BOUNDARY_OWNER_ACCEPTED
-> PRE_CHANGE_CHECKPOINT_VERIFIED
-> IMPLEMENTATION_AUTHORIZED
-> BUILDING
-> EVIDENCE_READY
-> TECHNICAL_REVIEW_PASSED
-> RESULT_OWNER_ACCEPTED
-> POST_ACCEPTANCE_CHECKPOINT_VERIFIED
-> RELEASE_AUTHORIZED
-> RELEASED
-> NEXT_WORK_ITEM_LOCKED

Недопустимо:
EVIDENCE_READY -> NEXT_WORK_ITEM_LOCKED
RESULT_OWNER_ACCEPTED -> RELEASE_AUTHORIZED (без release gate)
TECHNICAL_REVIEW_PASSED -> RESULT_OWNER_ACCEPTED (без evidence)

## 10–47. Подробности

Полные правила — в `docs/`. Разделы 44–47 — операционные приложения:
границы enforcement, уровни протокола, мандаты и усталость владельца,
миграция версий.

## 48. Финальная формула

OWNER DECIDES
AGENT EXECUTES
SERVER AUTHORIZES
TRANSACTION COMMITS
AUDIT PRESERVES
RECEIPT PROVES
TESTS CHALLENGE
CHECKPOINT PROTECTS
REVIEWERS CLEAR RELEASE
CONVENTION BINDS ONLY WHERE ENFORCEMENT EXISTS
NEXT STAGE STAYS LOCKED UNTIL A NEW DECISION
