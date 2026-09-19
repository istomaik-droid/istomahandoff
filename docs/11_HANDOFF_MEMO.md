# 11. Handoff memo

Append-only.

```yaml
- at: <ISO8601>
  workItem: <ID>
  stage: <STAGE>
  event: STARTED | EVIDENCE_READY | REVIEW_PASSED | OWNER_ACCEPTED | CHECKPOINT_VERIFIED | RELEASED | STOPPED | ROLLED_BACK
  summary: <текст>
  evidenceRef: <path>
  receiptSha256: <sha256>
  nextState: <STATE>
```

## Правила

1. Каждое событие фиксируется.
2. FAIL фиксируется до исправления.
3. Skipped и inconclusive не маскируются.
4. История не переписывается.
