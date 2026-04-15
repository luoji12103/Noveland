# Architecture Map

## Top-level repository shape

- `web/` — Next.js application
- `backend/services/api/` — HTTP and WebSocket entrypoint
- `backend/services/runtime/` — long-running runtime host
- `backend/packages/` — business domains and adapters
- `contracts/` — shared schemas/contracts
- `infra/` — deployment and local environment assets
- `docs/agent/` — governance and implementation guidance

## Backend domain packages

- `core/` — minimal shared primitives only
- `auth/` — identity, sessions, RBAC, world-scoped ownership
- `worlds/` — world entities, scenes, world clock, transitions
- `agents/` — agent identity, config, observation shaping, tool application
- `calendar/` — private schedule and calendar logic
- `narrative/` — summarizer orchestration and artifacts
- `events/` — event contracts, event store, snapshot interfaces, replay
- `memory/` — memory abstractions and implementations
- `plugins/` — plugin interfaces, registry, manifests
- `adapters/` — provider/storage/transport implementations
- `storage/` — object storage interfaces and default implementations
- `observability/` — structured logging and context helpers

## Dependency direction

- services may depend on packages
- domain packages may depend on `core`
- adapters implement package interfaces
- packages must not depend on service entrypoints
- web must only use API/contracts, never runtime internals directly

## Sensitive areas

- `events/`
- `worlds/` world clock and orchestration
- `auth/`
- `plugins/` registry and interface definitions
- `memory/` namespace isolation
