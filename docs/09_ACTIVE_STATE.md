# 09. Active state

> Mutable pointer. Immutable snapshots — отдельно в `evidence/`.

```yaml
protocol:
  version: "2.0"          # версия протокола; правила миграции — docs/47
  level: P0 | P1 | P2     # назначается в TRIAGE; docs/45
  enforcement: E0 | E1 | E2 | E3   # уровень среды; docs/44

checkpoint:
  lastDecisionId: DEC-XXXX
  lastAcceptedWorkItem: <ID>
  lastAcceptedAt: <ISO8601>
  lastAcceptanceReceiptSha256: <sha256>

activeWorkItem:
  id: <ID>
  stage: <STAGE>
  riskClass: R0..R5
  state: INTAKE | TRIAGE | DESIGN_READY | BOUNDARY_OWNER_ACCEPTED | PRE_CHANGE_CHECKPOINT_VERIFIED | IMPLEMENTATION_AUTHORIZED | BUILDING | EVIDENCE_READY | TECHNICAL_REVIEW_PASSED | RESULT_OWNER_ACCEPTED | POST_ACCEPTANCE_CHECKPOINT_VERIFIED | RELEASE_AUTHORIZED | RELEASED | NEXT_WORK_ITEM_LOCKED
  boundary:
    allowedScope: []
    forbiddenScope: []

rollbackAnchor:
  state: VERIFIED | NOT_VERIFIED | MISSING
  type: GIT_TAG | DB_SNAPSHOT | INFRA_SNAPSHOT | ARCHIVE
  sha256: <sha256>

nextWorkItem:
  state: LOCKED
  automaticallyOpened: false

activeMandates: []          # список MANDATE-XXXX; пусто, если deputy не действует

openBlockers:
  professional: []
  missingFacts: []
  nonClaims: []

environments:
  pilot: NOT_AUTHORIZED
  production: NOT_AUTHORIZED
  deployment: NOT_AUTHORIZED
```

## Правила

Обновляется только после recorded owner decision. Исключение: повышение protocol.level агентом при скрытом риске — с фиксацией в handoff memo (docs/45).

Alias byte-for-byte соответствует последнему snapshot.

Historical snapshot не редактируется.

Protocol level повысить можно всегда (агент обязан при обнаружении
скрытого риска / заниженного уровня); понизить — только owner decision.

Enforcement level ниже требуемого для risk class — stop condition (docs/44).
