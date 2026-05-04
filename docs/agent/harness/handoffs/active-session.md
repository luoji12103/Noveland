# Active Session Handoff

- Date: 2026-05-04T23:55:00Z
- Branch: feat/access-diagnostics-scale-roadmap-plan
- Objective: Implement roadmap phases 38-47 as an Access/Diagnostics/Scale Readiness Ops bundle, then merge back to local `main` if checks pass.
- Status: Started; implementation in progress.

## Selected Roadmap Phases

- 38. World Access Review
- 39. Diagnostic Retention Policy
- 40. Metrics Export Baseline
- 41. Deployment Profile v1
- 42. Runtime Process Supervision
- 43. Performance Budget v1
- 44. Memory Evaluation v2
- 45. Memory Backfill Execution
- 46. Distributed Queue Readiness
- 47. Sandbox Options Design

## Implementation Plan

- Add world-admin access review and audit diagnostics around membership changes.
- Add platform-admin diagnostic retention dry-run/prune endpoints and retention docs.
- Add a Prometheus text metrics endpoint for local operational scraping.
- Add runtime supervision status that separates API/runtime control/heartbeat/database health.
- Add memory eval recommendations and a guarded memory backfill execution endpoint.
- Add queue-readiness reporting for current DB-backed memory jobs.
- Add operator docs for deployment profile, runtime supervision, performance budget, queue readiness, and sandbox options.

## Discovered Bug Cleanup

- Previous active handoff still described Storage/Backup/Auth Runtime Ops as active/ready; this branch refreshes it at start and will close it out at the end.
- `web/next-env.d.ts` may churn after build/e2e; restore it before final merge if needed.

## Planned Checks

- Backend targeted: `cd backend && uv run pytest tests/test_api_runtime.py tests/test_api_worlds.py tests/test_memory_backend.py`
- Backend full: `cd backend && uv run ruff check . && uv run mypy . && uv run pytest`
- Web targeted as needed for changed admin/world surfaces.
- Web full: `cd web && npm run lint && npm run typecheck && npm run test && npm run build && npm run check:next-env && npm run test:e2e`
- Infra/status: `docker compose -f infra/compose.yaml config`, `git diff --check`, `git status --short --branch`

## Risks

- Backfill execution must remain idempotent and bounded; no external queue is introduced.
- Metrics and diagnostics must not expose secrets, prompts beyond existing diagnostic redaction, or private narrative content.
- Sandbox work is design-only in this bundle.
