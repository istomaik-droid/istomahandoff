# 21. Identity, auth, session

Канон для identity/session; docs/04 ссылается сюда.

## Identity layers

| Сущность | Смысл |
| --- | --- |
| PersonIdentity | Человек или subject |
| Account | Login/security lifecycle |
| Membership | Связь Account с domain |
| Position | Должность |
| Assignment | Организационный контекст |
| Grant/Mandate | Явное полномочие |
| Party/Customer | Коммерческая сторона |

Party/CustomerRelationship не создаёт Account и не даёт authority.

## Account lifecycle

pending/invited, active, blocked/suspended, terminated/revoked.
Effect fail-closed.

## Правила

1. Pending account не получает protected access.
2. Blocked теряет доступ немедленно.
3. Terminated не оживает при retry.
4. JWT/cookie claims — не единственный источник.
5. Каждый protected action перепроверяет current Account/Membership/authority.
6. Account security epoch инвалидирует старые sessions.
7. Session family: lineage, rotation, revoke.
8. Logout, global block, family revoke имеют проверяемый effect.

## Enrollment и factors

Чувствительные роли — invite-only.

PlatformOwner, DomainOwner, админы — password + risk-based MFA.

SSO — дополнительный метод.

Phone, Telegram, one-time link не обходят account/membership/session.

Federation binding уникален, не создаёт JIT authority.

Recovery не понижает assurance молча.

Ошибки login/recovery не раскрывают существование.

Synthetic adapters не production credentials.
