# 20. Архитектурный закон

## Направление зависимостей

```text
Domain <- Application <- Ports <- Adapters <- HTTP/UI
```

## Разрешено

Domain: invariants, typed state.

Application: use cases, transaction boundary.

Ports: provider-neutral contracts.

Adapters: storage, clock, crypto, delivery, local synthetic.

HTTP: untrusted request -> ClientIntent.

UI: read model, intent.

## Запрещено

Domain импортирует framework, filesystem, database, UI.

UI передаёт trusted role, domain scope, membership, policy, approval.

Adapter меняет business semantics.

Background job без service identity, domain scope, purpose.

Platform layer routine access к domain content.

## Domain-first boundary

Domain — tenant и authority boundary.

Membership имеет immutable incarnation.

Position и Assignment не дают неявных полномочий.

ObjectTeam — только контекст доступа.

Project, Object, WorkPackage — внутри Production, не tenant root.

Global и domain authority разделены.

PlatformOwner не получает domain content по умолчанию.

Support content-blind; break-glass отдельно.

## Server-authoritative effect

Strict ingress validation.

Current identity/account/session.

Current Membership и authority.

Purpose, DataScope, assurance.

Transaction commit.

Append-only audit.

Immutable Receipt.

Readback или idempotent recovery.

HTTP 200, очередь, draft, animation, upload transport, письмо не равны business acceptance.
