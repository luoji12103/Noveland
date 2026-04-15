# Ownership Map

## High-risk sensitive areas

### Event log and replay
- `backend/packages/events/`
Risk: breaking recovery, replay, or auditability

### World clock and orchestration
- `backend/packages/worlds/`
Risk: breaking time semantics and schedule resolution

### Auth and access
- `backend/packages/auth/`
Risk: breaking isolation or unauthorized access

### Plugin registry and plugin contracts
- `backend/packages/plugins/`
Risk: introducing extension chaos

### Memory namespace isolation
- `backend/packages/memory/`
Risk: cross-agent leakage

## Rule

Before changing a sensitive area:
- read relevant architecture docs
- inspect current tests
- update debug/change journal if the change is non-trivial
