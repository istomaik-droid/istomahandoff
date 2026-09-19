# 47. Миграция версий протокола

## Правила

1. Протокол версионируется semver (major.minor). История — docs/42.
2. In-flight work item продолжает работу по версии, зафиксированной
   в его ACTIVE_STATE, до отдельного решения MIGRATION (кроме minor-версии,
   мигрирующей автоматически по правилу 5).
3. Решение MIGRATION фиксируется в decision log: какой work item,
   с какой версии на какую, что изменилось в его границах.
4. Агент обязан сверять protocol.version при каждом context recovery
   (docs/34). Несовпадение — STOPPED_PROTOCOL_MISMATCH.
5. Major-версия (несовместимые изменения) требует явного решения
   владельца для каждого in-flight item. Minor — может мигрировать
   автоматически, если не меняет state machine и главное правило.
6. Handoff обязан включать версию протокола; внешний агент называет
   прочитанную версию при первом ответе.
7. Понижение версии для существующего work item запрещено.

## Формат решения MIGRATION

```text
DEC-XXXX type: MIGRATION
workItem: <ID>
from: <SEMVER>
to: <SEMVER>
changedBoundaries: <что изменилось для этого item>
rePreflightRequired: true | false
```
