# 22. Authorization и tenant isolation

## Default deny PDP

```text
Account state
+ exact Membership incarnation
+ Capability
+ Grant or Mandate
+ DataScope intersection
+ Purpose
+ Assurance / step-up
+ Policy version
+ Trusted time
+ Separation of duties
```

Отсутствующее значение = deny.

## Commit-time fence

Authority проверяется и перед commit. Revoke, block, expiry, policy change,
dispute, supersession блокируют effect.

## Защита от self-escalation

Пользователь не выдаёт себе capability.

Grant привязан к membership incarnation.

Scope выдаваемого не шире выдающего.

Delegability явная.

Sensitive changes: step-up + separation of duties.

Break-glass: purpose, срок, scope, audit.

Global capability не выводится из domain role.

## Изоляция всех путей

Domain scope применяется до item read, list, search, count, aggregate,
pagination, cache key, background job, export, restore/readback,
correction lookup, media/file access, telemetry, projection.

Проверки включают planted foreign record и cross-domain property tests.
Deny и not-found не раскрывают существование.
