# 25. Browser и request integrity

Cookie: HttpOnly, Secure, подходящий SameSite.

Cross-site cookie — явный CSRF token contract.

State-changing requests: CSRF token, Origin, Fetch Metadata.

CORS: exact allowlist.

Credentialed CORS нельзя с wildcard origin.

Bearer и cookie flow не смешиваются.

Security headers: no-store, nosniff, frame denial, строгая CSP.

Sensitive response не кэшируется shared cache.

Login, invite, recovery, upload: rate limits и anti-abuse.

POST после cookie-login проверяется integration tests,
включая cross-origin topology.
