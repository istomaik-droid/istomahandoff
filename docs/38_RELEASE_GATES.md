# 38. Release gates

Local synthetic evidence позволяет писать и проверять код, но не разрешает
реальное воздействие.

## До pilot / staging с реальными данными

1. Independent legal/privacy/security/architecture/data/ops reviews.
2. Проверка фактической implementation.
3. Production persistence и physical tenant model.
4. Реальные MFA/SSO/recovery/provider decisions.
5. Secrets/key/crypto profile.
6. Data inventory, purpose, retention, legal hold, disposition.
7. Workload, SLO, RPO, RTO.
8. Tenant isolation, revoke, CSRF, abuse, upload tests.
9. Backup/restore/export/rebuild rehearsal.
10. Incident/support/rollback rehearsal.
11. Measurement baseline и stop thresholds.
12. Явное pilot exposure decision.

## До production

1. Успешный bounded pilot или обоснованное решение.
2. Закрытые release blockers или explicit risk acceptance.
3. Production deployment architecture.
4. Monitoring, alerts, incident ownership, support.
5. Capacity, failure, recovery, data disposition evidence.
6. Security/privacy/legal release packet.
7. Go/No-Go decision.
8. Rollback authority и rehearsed path.
9. SBOM и provenance.
10. Signed release artifacts.

Ни один local verdict не заменяет эти gates.

## Pre-deploy gate (деплой из рабочего дерева)

Если деплой идёт из рабочего дерева (например, restart службы): перед деплоем
дерево по своим файлам чистое; чужие или непонятные незакоммиченные правки —
STOP (docs/33). Задеплоенное = закоммиченное.
