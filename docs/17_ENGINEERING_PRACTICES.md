# 17. Инженерные практики

## Version control

Trunk-based или короткоживущие ветки.

Protected branches: main, release.

Обязательный PR/MR.

Commit signing (GPG/Sigstore).

Линейная история или squash-merge.

Никаких force-push в protected branches.

## Code review

Human reviewer обязателен.

Смотрит: корректность, читаемость, архитектуру, тесты, безопасность, производительность.

Review не заменяет owner acceptance.

Review не открывает следующий stage.

## CI/CD gates

lint, typecheck, unit, integration, e2e, architecture,
SAST, dependency scan, secret scan, license scan,
SBOM, reproducible build, container scan.

Набор обязательных gates сокращается по protocol level (docs/30).

## Provenance

Signed builds, SLSA, immutable artifacts, checksums, registry.

## Migrations

Expand-contract, dry-run, rollback plan, backward compatibility,
time limits, без блокировки traffic.

## Feature flags

Decouple deploy/release, bounded lifetime, owner и expiry, тесты обоих состояний.

## Deployment

Canary, blue-green, rolling, rehearsed rollback, post-deploy verification.

## Observability

Logs, metrics, traces, SLO, error budget, alerts с runbook, dashboard, request ID.

## Runbooks / on-call

Runbook, rotation, escalation matrix, rehearsed incidents.

## Incident response

Blameless postmortem, timeline, impact, root cause, action items.

Правило, добавленное после инцидента, ссылается на прецедент (docs/35).

## Performance

Load testing, budgets, baseline, профилирование.

## Accessibility / i18n

WCAG, локализация, RTL/LTR, длинные строки, плюрализация.
