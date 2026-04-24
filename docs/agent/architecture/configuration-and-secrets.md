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
- memory backend provider/API secrets
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
- `NOVELAND_MEMORY_BACKEND_SECRETS_JSON`
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
- Provider profiles also store non-secret reliability controls: timeout seconds, retry attempts, optional per-process rate limit, and last test status metadata.
- Provider API keys are not persisted in the database; runtime resolves them from `NOVELAND_PROVIDER_API_KEYS_JSON`.
- Web and HTTP APIs may read and update provider profiles, but they must never return API key material.
- Provider test calls use the configured `api_key_ref`, update only non-secret health fields, and record redacted diagnostics.
- `NOVELAND_RUNTIME_LOOP_INTERVAL_SECONDS` controls the daemon sleep interval between iterations.
- `NOVELAND_RUNTIME_BATCH_LIMIT` caps how many due agent runs a single daemon iteration will execute.

## Long-term memory baseline

- Memory backend profiles are platform-owned non-secret database records containing backend kind, vector-store config, LLM/embedder/reranker config, secret refs, and enablement state.
- Worlds bind to long-term memory through `memory_backend_profile_id`; world-level plugin binding remains separate from the full backend profile.
- Memory backend secrets are not persisted in the database; runtime resolves them from `NOVELAND_MEMORY_BACKEND_SECRETS_JSON`.
- Long-term memory writes are asynchronous through database-backed memory write jobs; primary runtime and conversation flows enqueue work rather than calling backend SDKs inline.
- Web and HTTP APIs may manage memory backend profiles and read health/log/eval summaries, but they must never return resolved secret material.

## Required docs sync

If config changes:
- update config docs
- update example env or config templates
- update deployment docs if relevant
