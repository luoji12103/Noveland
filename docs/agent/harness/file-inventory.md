# File Inventory

## Purpose

Track key structural files and prevent unregistered sprawl.

## Registered structural areas

- `README.md`
- `.env.example`
- `web/`
- `web/app/`
- `web/app/login/`
- `web/app/api/auth/`
- `web/app/api/worlds/`
- `web/features/`
- `web/features/auth/`
- `web/features/dashboard/`
- `web/components/`
- `web/lib/`
- `web/lib/auth/`
- `web/lib/worlds/`
- `web/tests/e2e/start-with-mock-auth.mjs`
- `backend/services/api/`
- `backend/services/api/src/noveland/services/api/authorization.py`
- `backend/services/api/src/noveland/services/api/auth.py`
- `backend/services/api/src/noveland/services/api/csrf.py`
- `backend/services/api/src/noveland/services/api/dependencies.py`
- `backend/services/api/src/noveland/services/api/worlds.py`
- `backend/services/runtime/`
- `backend/packages/core/`
- `backend/packages/core/src/noveland/core/database.py`
- `backend/packages/core/src/noveland/core/models.py`
- `backend/packages/auth/`
- `backend/packages/auth/src/noveland/auth/contracts.py`
- `backend/packages/auth/src/noveland/auth/errors.py`
- `backend/packages/auth/src/noveland/auth/models.py`
- `backend/packages/auth/src/noveland/auth/seed_admin.py`
- `backend/packages/auth/src/noveland/auth/services.py`
- `backend/packages/worlds/`
- `backend/packages/worlds/src/noveland/worlds/clock.py`
- `backend/packages/worlds/src/noveland/worlds/clock_service.py`
- `backend/packages/worlds/src/noveland/worlds/models.py`
- `backend/packages/agents/`
- `backend/packages/agents/src/noveland/agents/models.py`
- `backend/packages/calendar/`
- `backend/packages/narrative/`
- `backend/packages/events/`
- `backend/packages/events/src/noveland/events/contracts.py`
- `backend/packages/events/src/noveland/events/errors.py`
- `backend/packages/events/src/noveland/events/event_store.py`
- `backend/packages/events/src/noveland/events/models.py`
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
- `backend/migrations/versions/20260416_0003_event_snapshot_baseline.py`
- `backend/migrations/versions/20260416_0004_auth_session_baseline.py`
- `backend/tests/`
- `contracts/`
- `infra/`
- `infra/compose.yaml`
- `docs/agent/`

## Update rule

Add new structural files/modules here when they become part of the stable architecture.

## Warning

If a coding agent created a structural path that is not listed here and did not update this file, the work is incomplete.
