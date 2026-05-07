# Living World Release Profile

Use the release profile and beta checklist before treating a galgame living world as beta-ready.

## Scope

- Release profile records branch, backup, content review, player permission, worldline, and publication-readiness policy for a world.
- Long-run eval runs are deterministic local reviews over existing state. They do not call providers or external tools.
- Beta checklist runs collect evidence for 7-day simulation, branch/worldline saves, relationships, factions, GM/event loop, interventions, journal/notifications, and narrative output.

## Operator Flow

1. Apply migrations through `20260507_0028`.
2. Create or update the world release profile from the world admin workspace.
3. Run a long-run eval for the target worldline with a 7-day horizon.
4. Resolve blockers or record explicit operator decisions for non-blocking recommendations.
5. Run the beta checklist and review each checklist item.
6. Mark the release profile `ready` only when blockers are zero and review policies are satisfied.

## Manual Checks

```sh
cd backend && uv run alembic current
cd backend && uv run pytest tests/test_api_worlds.py::test_beta_release_readiness_apis_cover_routes_evals_authoring_and_checklist
cd web && npm run test -- lib/worlds/client.test.ts features/worlds/world-overview.test.tsx
```

Do not treat a passing checklist as a public launch. It is beta evidence for a controlled sample world.
