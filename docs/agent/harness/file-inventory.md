# File Inventory

## Purpose

Track key structural files and prevent unregistered sprawl.

## Registered structural areas

- `README.md`
- `.env.example`
- `web/`
- `web/app/`
- `web/features/`
- `web/components/`
- `web/lib/`
- `backend/services/api/`
- `backend/services/runtime/`
- `backend/packages/core/`
- `backend/packages/core/src/noveland/core/database.py`
- `backend/packages/core/src/noveland/core/models.py`
- `backend/packages/auth/`
- `backend/packages/auth/src/noveland/auth/models.py`
- `backend/packages/worlds/`
- `backend/packages/worlds/src/noveland/worlds/clock.py`
- `backend/packages/worlds/src/noveland/worlds/models.py`
- `backend/packages/agents/`
- `backend/packages/agents/src/noveland/agents/models.py`
- `backend/packages/calendar/`
- `backend/packages/narrative/`
- `backend/packages/events/`
- `backend/packages/memory/`
- `backend/packages/plugins/`
- `backend/packages/plugins/src/noveland/plugins/categories.py`
- `backend/packages/plugins/src/noveland/plugins/definition.py`
- `backend/packages/plugins/src/noveland/plugins/errors.py`
- `backend/packages/plugins/src/noveland/plugins/manifest.py`
- `backend/packages/plugins/src/noveland/plugins/registry.py`
- `backend/packages/adapters/`
- `backend/packages/storage/`
- `backend/packages/observability/`
- `backend/migrations/`
- `backend/migrations/versions/20260415_0001_core_schema.py`
- `backend/migrations/versions/20260415_0002_world_clock_state.py`
- `backend/tests/`
- `contracts/`
- `infra/`
- `infra/compose.yaml`
- `docs/agent/`

## Update rule

Add new structural files/modules here when they become part of the stable architecture.

## Warning

If a coding agent created a structural path that is not listed here and did not update this file, the work is incomplete.
