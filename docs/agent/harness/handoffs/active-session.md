# Active Session Handoff

- Date: 2026-05-05T13:51:55Z
- Branch: feat/living-world-autonomous-systems
- Objective: Implement V2 living-world roadmap phases 6-15: relationship memory, organizations, memberships, faction progress, location graph, presence, daily life scheduling, offscreen queue, event importance, and GM world engine v1.
- Status: Started on feature branch from clean `main`.

## Planned Implementation

- Add migration `20260505_0024_living_world_autonomous_systems` for autonomous living-world tables and `world_events.importance`.
- Keep memory writes behind `MemoryService`, including relationship-change memory summaries.
- Extend world/admin APIs and Web workspace for organizations, faction tracks, location graph, presence, daily/offscreen events, and GM diagnostics.
- Add deterministic GM runtime component only; no provider/LLM GM calls, external tools, worldlines, or player choice systems in this bundle.
- Keep Playwright mock backend aligned with new world APIs and restore `web/next-env.d.ts` after build/e2e if it changes.

## Planned Checks

- `cd backend && uv run pytest tests/test_api_worlds.py tests/test_memory_backend.py tests/test_runtime_daemon.py tests/test_schema_metadata.py tests/test_alembic_config.py`
- `cd web && npm run test -- lib/worlds/client.test.ts features/worlds/world-overview.test.tsx features/agents/agent-builder.test.tsx`
- `cd backend && uv run ruff check .`
- `cd backend && uv run mypy .`
- `cd backend && uv run pytest`
- `cd web && npm run lint`
- `cd web && npm run typecheck`
- `cd web && npm run test`
- `cd web && npm run build`
- `cd web && npm run check:next-env`
- `cd web && npm run test:e2e`
- `docker compose -f infra/compose.yaml config`
- `git diff --check`
- `git status --short --branch`

## Risks

- This bundle crosses schema, runtime, memory, and Web surfaces; commit in functional slices and run targeted checks before final gate.
- GM v1 must stay deterministic and bounded to existing runtime/event/memory contracts.
- Persistent databases will need migration `20260505_0024` before using autonomous systems data.
