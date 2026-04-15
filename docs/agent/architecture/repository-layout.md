# Repository Layout

## Locked top-level layout

```text
/
  web/
  backend/
    services/
      api/
      runtime/
    packages/
      core/
      auth/
      worlds/
      agents/
      calendar/
      narrative/
      events/
      memory/
      plugins/
      adapters/
      storage/
      observability/
    migrations/
    tests/
  contracts/
  infra/
  docs/
    agent/
```

## Layout rules

- New top-level directories are forbidden unless architecture docs are updated first.
- New backend business areas must live under `backend/packages/`.
- New runtime or entrypoint processes must live under `backend/services/`.
- Shared schemas intended for cross-boundary use belong under `contracts/`.
- Tooling, compose, provisioning, and deployment assets belong under `infra/`.
- Governance docs belong under `docs/agent/`.

## Forbidden patterns

- `backend/utils2/`, `backend/helpers_new/`, `backend/final/`
- top-level `scripts/` as a dumping ground for temporary code
- unregistered experimental service directories
