# 23. Strict ingress, commands, trusted time

## ClientIntent vs trusted context

Клиент не может назначить: domain authority, current Membership,
trusted role, policy version, approval actor, trusted timestamp,
audit issuer, server Receipt, legal effect.

Эти поля разрешает сервер в ResolvedCommandContext.

## Input controls

Strict raw-body parser.

Неизвестные поля — отклоняются.

Body/file/count limit.

Content-Type и actual content — независимо.

Canonical semantic digest после нормализации.

Error taxonomy не раскрывает чужое существование и secrets.

Trusted time через server clock port.

Expiry, effective date, anti-backdate не доверяют client clock.
