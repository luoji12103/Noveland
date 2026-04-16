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
- `NOVELAND_POSTGRES_PORT`
- `NOVELAND_NATS_PORT`
- `NOVELAND_NATS_MONITOR_PORT`

## Auth/session baseline

- Local password credentials are stored as Argon2id PHC hashes, not as committed secrets.
- Opaque session tokens are generated server-side and only SHA-256 token hashes are persisted.
- HTTP auth uses the `noveland_session` HttpOnly cookie and `noveland_csrf` readable CSRF cookie.
- Local development cookies default to `Secure=false`; production cookie hardening remains a deployment/security task.
- The current auth/session and HTTP auth baselines do not add a new environment variable.

## Required docs sync

If config changes:
- update config docs
- update example env or config templates
- update deployment docs if relevant
