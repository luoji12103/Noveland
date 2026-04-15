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

## Required docs sync

If config changes:
- update config docs
- update example env or config templates
- update deployment docs if relevant
