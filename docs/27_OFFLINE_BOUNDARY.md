# 27. Offline boundary

## Принятая модель

Online-first и server-authoritative.

## Разрешённая bounded модель

зашифрованный минимизированный local draft;

read-only cache с freshness marker;

bounded outbox для allowlisted field intent/evidence;

stable operation ID;

повторная server-side authorization при reconnect;

explicit rejected/conflict state без automatic merge.

До server Receipt локальная операция не является отправленной, принятой,
оплаченной, подписанной, подтверждённой.

## Требуют online current authority

access/grant changes, money/accounting effects, contract/obligation activation,
acceptance и warranty event, final status, deletion/disposition,
autonomous AI action.

Full offline-first и automatic conflict resolution — отдельное field study
и owner decision.
