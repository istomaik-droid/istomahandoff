# 14. Work package contract

| Поле | Вопрос |
| --- | --- |
| PackageId | Идентификация |
| SliceId | Принадлежность slice |
| OutcomeRef | Какой вред уменьшает |
| Actor | Кто инициирует |
| DecisionAuthority | Кто принимает effect |
| Preconditions | Обязательный current state |
| AuthorityRef | Capability, DataScope, Purpose, assurance, policy version |
| DomainScope | Tenant boundary |
| AuthoritativeEffect | Что коммитится как truth |
| QueryReadback | Проверка без existence leakage |
| AuditCorrection | Source, reason, lineage |
| ReceiptIdempotency | Почему retry даёт один effect |
| ThreatRef | Abuse paths |
| PrivacyLegal | Purpose, data class, retention |
| Measurement | Provenance, freshness, missingness |
| Acceptance | Positive, negative, fault, isolation |
| RollbackRef | Как безопасно остановить |
| EvidenceLocation | Manifests, receipts, results |
| ProtocolLevel | P0/P1/P2 по риску (docs/45) |

NOT_READY, если package создаёт только schema, endpoint, экран, сервис
или инфраструктуру без end-to-end outcome и denial paths.
