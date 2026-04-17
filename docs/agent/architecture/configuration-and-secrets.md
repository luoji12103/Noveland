# Configuration and Secrets

## Rules

- all configuration enters through typed settings
- no raw `os.getenv` scattered through the codebase
- every new environment variable must be documented
- secrets must never be committed
- environment defaults must be conservative and local-dev safe

## Configuration layers

- platform defaults
- world overrides
- group overrides
- agent overrides

## Secret categories

- database credentials
- provider API keys
- object storage credentials
- session/auth secrets
- messaging credentials

## Local development variables

- `NOVELAND_ENV`
- `NOVELAND_DATABASE_URL`
- `NOVELAND_NATS_URL`
- `NOVELAND_OBJECT_STORAGE_ROOT`
- `NOVELAND_API_BASE_URL`
- `NOVELAND_POSTGRES_PORT`
- `NOVELAND_NATS_PORT`
- `NOVELAND_NATS_MONITOR_PORT`
- `NOVELAND_PROVIDER_API_KEYS_JSON`
- `NOVELAND_RUNTIME_LOOP_INTERVAL_SECONDS`
- `NOVELAND_RUNTIME_BATCH_LIMIT`

## Auth/session baseline

- Local password credentials are stored as Argon2id PHC hashes, not as committed secrets.
- Opaque session tokens are generated server-side and only SHA-256 token hashes are persisted.
- HTTP auth uses the `noveland_session` HttpOnly cookie and `noveland_csrf` readable CSRF cookie.
- Web auth proxy routes use `NOVELAND_API_BASE_URL` to reach the backend API from the Next server.
- Local development cookies default to `Secure=false`; production cookie hardening remains a deployment/security task.
- `NOVELAND_API_BASE_URL` is non-secret local routing configuration.

## Provider/runtime baseline

- Provider profiles are non-secret database records containing provider type, base URL, model, capabilities, and `api_key_ref`.
- Provider API keys are not persisted in the database; runtime resolves them from `NOVELAND_PROVIDER_API_KEYS_JSON`.
- Web and HTTP APIs may read and update provider profiles, but they must never return API key material.
- `NOVELAND_RUNTIME_LOOP_INTERVAL_SECONDS` controls the daemon sleep interval between iterations.
- `NOVELAND_RUNTIME_BATCH_LIMIT` caps how many due agent runs a single daemon iteration will execute.

## Required docs sync

If config changes:
- update config docs
- update example env or config templates
- update deployment docs if relevant
