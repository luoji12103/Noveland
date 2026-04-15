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
- `backend/packages/auth/`
- `backend/packages/worlds/`
- `backend/packages/agents/`
- `backend/packages/calendar/`
- `backend/packages/narrative/`
- `backend/packages/events/`
- `backend/packages/memory/`
- `backend/packages/plugins/`
- `backend/packages/adapters/`
- `backend/packages/storage/`
- `backend/packages/observability/`
- `backend/migrations/`
- `backend/tests/`
- `contracts/`
- `infra/`
- `infra/compose.yaml`
- `docs/agent/`

## Update rule

Add new structural files/modules here when they become part of the stable architecture.

## Warning

If a coding agent created a structural path that is not listed here and did not update this file, the work is incomplete.
