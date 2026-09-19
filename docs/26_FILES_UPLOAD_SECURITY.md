# 26. Files, binary evidence, upload

Upload — в quarantine.

Allowlisted types.

Magic/content, не только extension и MIME header.

Per-file, request, count limits.

Файл сверх лимита — отклоняется до resource exhaustion.

Active rendering недоверенного content запрещён.

Parser — изолированно, bounded resources.

Malware scan — port; provider отдельным решением.

Object key генерируется сервером, без path traversal.

Download повторно проверяет domain, audience, purpose, expiry, revoke.

Secrets, credentials, recovery material, recipient proofs не в export.

Ошибка удаления blob не маскируется; reconciliation state.
