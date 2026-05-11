# Active Session Handoff

- Date: 2026-05-11T00:00:00Z
- Branch: feat/media-kernel
- Objective: Complete Media Kernel Phase 4 additive extension and merge locally back to `main`.
- Status: Implementation complete on feature branch; backend targeted and full tests pass. Full local gate and fast-forward merge remain before closeout.

## Current Context

- Phase 4 extends the existing Media Phase 1/2 foundation instead of replacing it.
- Existing `media_assets`, `media_jobs`, contexts, inputs, tags, collections, and route behavior remain intact.
- New kernel pieces are `media_objects`, `media_references`, upload/download object flows, richer job updates, turn media references, and media-side invocation links.
- `worlds.py` remains out of scope for media routes.
- Storage URIs, filesystem paths, base64, and bytes must stay out of `world_events.payload`.

## Completed Implementation

- Added migration `20260512_0033_media_kernel.py` revising `20260511_0032`.
- Added `media_objects` and `media_references`.
- Added `media_assets.source_invocation_id` and `media_jobs.source_event_id`, `source_invocation_id`, and `provider_config_json`.
- Extended `noveland.media` contracts, models, services, storage helpers, and exports.
- Extended the independent media API router with upload, object list/create/download, generic references, job patch, and turn media routes.
- Added ACL handling for new management surfaces, including platform-admin-only access to `developer_only` and `hidden` assets on object/reference/download paths.
- Added service/API/schema/Alembic tests.

## Verification So Far

- `cd backend && uv run pytest tests/test_media_service.py tests/test_api_media.py tests/test_schema_metadata.py tests/test_alembic_config.py tests/test_workspace_imports.py`
- `cd backend && uv run ruff check .`
- `cd backend && uv run mypy .`
- `cd backend && uv run pytest`

## Required Closeout

- Run the remaining full local gate:
  - `cd web && npm run lint`
  - `cd web && npm run typecheck`
  - `cd web && npm run test`
  - `cd web && npm run build`
  - `cd web && npm run check:next-env`
  - `cd web && npm run test:e2e`
  - `docker compose -f infra/compose.yaml config`
  - `git diff --check`
- Commit the Phase 4 implementation on `feat/media-kernel`.
- Fast-forward merge locally back to `main`.
- Do not push unless explicitly requested.
