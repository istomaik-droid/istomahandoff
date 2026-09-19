# 08. Delivery sequence и architecture readiness

## Обязательно

1. Vertical sequence.
2. ADR.
3. Trust boundaries.
4. Fixture contract.
5. Acceptance cases.
6. Stop conditions.
7. Owner architecture acceptance.

## Результат

`ARCHITECTURE_READY` — только после этого можно отдельно разрешать локальную реализацию.
ARCHITECTURE_READY — статус готовности блока старта, не состояние state machine work item.

## Правила

1. По умолчанию — один primary work item.
2. Skip/reorder/merge/parallel — отдельное owner decision.
3. Task count, файлы, строки кода и UI не являются процентом готовности.
4. Для каждого work item в TRIAGE назначается protocol level (docs/45)
   и проверяется enforcement level среды (docs/44).
