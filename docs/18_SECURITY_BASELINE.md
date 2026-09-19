# 18. Security baseline

Threat modeling для R4+.

OWASP ASVS / Top 10.

Dependency scanning.

Pinned dependencies и lockfile.

Secret scanning до commit.

Secrets management: Vault, SOPS, cloud KMS.

Rotation secrets.

Least privilege для CI/CD и runtime.

Network policies: deny-by-default.

CSRF, CORS, CSP, security headers.

Rate limiting и anti-abuse.

Input validation и strict parsers.

Output encoding.

Encryption at rest и in transit.

SBOM и supply chain attestation.

Container image scanning.

Vulnerability disclosure policy.

Security review перед production.

Break-glass path с полным audit.

Регулярный security training.

Правило уровней (docs/44): R2–R3 — не ниже E1 (зависимости/сеть — E2), R4 — не ниже E2, R5 — E3; enforcement ниже требуемого — stop condition (docs/33, п. 26).
Агент не может «включить защиту» текстом; если среда не даёт sandbox,
агент обязан заявить об этом вместо заявления готовности.
