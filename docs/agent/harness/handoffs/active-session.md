# Active Session Handoff

- Date: 2026-05-11T00:00:00Z
- Branch: feat/model-invocation-ledger
- Objective: Implement Model Invocation Ledger Phase 3 from `docs/agent/harness/feature-updates/v0.3.1.3-model-invocation-ledger-phase-3-plan.md`.
- Status: Backend implementation complete locally; no push performed.

## Completed In This Branch

- Added `backend/packages/invocations` as `noveland-invocations`.
- Added migration `20260511_0032_model_invocation_ledger.py`, revising `20260510_0031`.
- Added `model_invocations`, `prompt_templates`, `prompt_snapshots`, `agent_runtime_run_model_invocations`, and `model_invocation_tags`.
- Registered `noveland.invocations.models` in SQLAlchemy metadata imports and workspace imports.
- Added independent API router `noveland.services.api.invocations` under `/worlds/{world_id}/model-invocations` and `/worlds/{world_id}/prompt-templates`.
- Integrated new `AgentRuntimeRun` provider calls with ledger records, prompt snapshots, status updates, and runtime-run join rows.
- Preserved Phase 3 boundaries: no provider adapter refactor, no Web UI, no external tracing exporter, no pgvector search, no historical backfill, no `conversation_turns` schema change, and no raw prompt/output in `world_events.payload`.
- Updated migration README, project index, file inventory, task board, change journal, and this handoff.

## Checks Passed

- `cd backend && uv run pytest tests/test_invocation_ledger_service.py tests/test_api_invocations.py tests/test_runtime_daemon.py tests/test_schema_metadata.py tests/test_alembic_config.py tests/test_workspace_imports.py`
- `cd backend && uv run ruff check .`
- `cd backend && uv run mypy .`
- `cd backend && uv run pytest`

## Remaining Closeout

- Run the Web/infra portion of the final gate if not already run in the current terminal session:
  - `cd web && npm run lint`
  - `cd web && npm run typecheck`
  - `cd web && npm run test`
  - `cd web && npm run build`
  - `cd web && npm run check:next-env`
  - `cd web && npm run test:e2e`
  - `docker compose -f infra/compose.yaml config`
  - `git diff --check`
- Commit implementation on `feat/model-invocation-ledger`, then fast-forward merge to local `main` if clean.
- Do not push unless explicitly requested.
