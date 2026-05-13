# Provider Secrets As Opaque Auth Ref

## Status

Accepted

## Context

Real provider smoke tests require secrets, but DB rows, logs, snapshots, and API responses must not store resolved API keys.

## Decision

`provider_integrations.auth_ref` is an opaque reference string. Providers resolve actual secrets in memory at execution time through `ProviderSecretResolver`.

## Consequences

Provider config/default params reject secret-like keys. Health checks and diagnostics record only safe status such as auth missing/resolved/failed.

## Non-goals

- Vault/KMS.
- Encrypted DB secret storage.
- User-managed secret UI.

## Related files/tests

- `backend/packages/providers/src/noveland/providers/secrets.py`
- `backend/packages/providers/src/noveland/providers/registry.py`
- `backend/tests/test_provider_registry_service.py`
- `backend/tests/test_api_providers.py`
