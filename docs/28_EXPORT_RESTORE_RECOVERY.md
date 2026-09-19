# 28. Export, restore, recovery

## Export

REQUEST проверяет current authority.

GENERATE: deterministic one-domain package.

Manifest: paths, lengths, hashes, versions, semantic digests.

INTERNAL и CUSTOMER_SAFE разделены.

DELIVER повторно проверяет authority, audience, expiry, revoke.

PlatformOwner не получает domain content автоматически.

## Readback / restore

Manifest, source/version/digest references.

Reconstruction в isolated target.

Direct business mutation из readback запрещён.

Silent merge, overwrite, resurrection запрещены.

Anti-resurrection для revoked/terminated.

Reconciliation receipt: missing, unexpected, conflicts.

Export/readback не называется production backup или legal evidence
без отдельного доказательства.
