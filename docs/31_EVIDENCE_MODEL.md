# 31. Evidence model

## Разделение

```text
IMMUTABLE_EXPECTED_SOURCE
!=
OBSERVED_TEST_RESULT
!=
OWNER_ACCEPTED_STATUS
```

Expected — до прогона. Observed — ссылается на expected hash.
Acceptance — на оба, не перезаписывает.

## Standard evidence checkpoint

schema version, product и stage ID, owner authorization, exact boundary,
predecessor и rollback anchor, source/build/config/fixture hashes,
files changed, dependencies/lockfile delta,
tests expected/executed/passed/failed,
negative/fault/isolation/leakage coverage,
defects и rerun history, critical stops,
professional blockers, missing production facts, non-claims,
business mutations/effects count, next stage state, owner acceptance state.

Объём checkpoint масштабируется по protocol level (docs/45).

## Timing

Evidence создаётся сразу по завершении изменения — частью того же коммита.
Одна запись на одно изменение; батч-записи задним числом запрещены
(фальсифицируют историю).

## Status aliases и snapshots

Mutable alias — текущее.

EVIDENCE_READY — immutable.

OWNER_ACCEPTED — новый snapshot.

Receipt хранит SHA-256 обоих.

Alias byte-for-byte соответствует последнему snapshot.

Historical snapshot не редактируется.

## Honest verdict

```text
PROVEN
INCONCLUSIVE
STOPPED
ROLLED_BACK
```

Недостаток данных = INCONCLUSIVE. Security incident = STOPPED.
