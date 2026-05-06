# Active Session Handoff

- Date: 2026-05-06T00:00:00Z
- Branch: feat/living-world-gm-choices-worldlines
- Objective: Implement V2 living-world roadmap phases 16-25: GM agenda, event proposals, deterministic resolution rules, player actor/choices/consequences, branchable worldlines, snapshot fork, worldline memory isolation, and timeline comparison.
- Status: Started from clean local `main`.

## Planned Implementation

- Add migration `20260505_0025_living_world_gm_choices_worldlines`.
- Add primary/forked worldlines and scope events, snapshots, replay, memory, GM, player choices, and Web views by worldline.
- Add deterministic GM agenda/proposal/resolution services and world-admin APIs; no provider, LLM, external tool, or sandbox execution.
- Add player actor profiles, structured choice records, consequence preview/apply, and branch comparison.
- Keep `MemoryService` as the only runtime memory boundary and prevent cross-worldline memory leakage.

## Planned Checks

- `cd backend && uv run pytest tests/test_api_worlds.py tests/test_memory_backend.py tests/test_runtime_daemon.py tests/test_replay_snapshot.py tests/test_schema_metadata.py tests/test_alembic_config.py`
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

- Worldline scoping cuts across event, snapshot, replay, memory, runtime, and Web mocks; use compatibility defaults for existing rows.
- Persistent databases must apply migration `20260505_0025` before using worldline-scoped data.
- This bundle intentionally stops before promises/hooks, plot threads, routes, secrets, and rumor/information flow.
