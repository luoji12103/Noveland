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

## Required docs sync

If config changes:
- update config docs
- update example env or config templates
- update deployment docs if relevant
