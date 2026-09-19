# 24. Transaction, idempotency, audit, correction

## Atomic effect

```text
operation reservation
+ expected version check
+ authority fence
+ authoritative mutation
+ append-only AuditEvent
+ immutable Receipt
+ outbox/effect intent when applicable
```

Один элемент не записался — business effect откатывается.

## Retry и response loss

Stable operation ID в правильном namespace.

Повтор с тем же digest возвращает тот же результат.

Повтор с другим payload под тем же ID отклоняется.

Потеря response не создаёт второй effect.

Idempotent readback повторно проверяет authority.

Fault injection: до, внутри, после commit.

## История не переписывается

Source record и approved baseline immutable.

Исправление — linked Correction.

Изменение обязательства — successor version и diff.

Destructive deletion, silent merge, retroactive mutation запрещены.

Correction хранит reason, actor, evidence, trusted time, source link.

Dispute, suspend, terminate, supersede — явные состояния.
