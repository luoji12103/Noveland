# Performance Budget v1

## Purpose

These local budgets make performance regressions visible before Noveland adds multi-host or high-concurrency deployment profiles.

## Baseline Budgets

- API health and auth session checks: under 250 ms locally.
- World overview data load: under 1 s locally for a small world.
- Runtime daemon iteration: under the configured loop interval when no provider call is due.
- Memory retrieval context build: under 1 s for local pgvector-sized development data.
- Narrative reader list/search: under 1 s for small local datasets.
- Web production build: should complete without tracked `next-env.d.ts` churn after restoration.

## Repeatable Checks

```sh
cd backend
uv run pytest tests/test_api_runtime.py tests/test_api_worlds.py tests/test_memory_backend.py
uv run noveland-runtime --once
```

```sh
cd web
npm run test
npm run build
npm run check:next-env
```

## Regression Signals

- Runtime heartbeat becomes stale while desired state is running.
- Memory queue `stalled_processing_count` or terminal failures grow.
- Provider health shifts from `ok` to `degraded` or `configuration_error`.
- E2E flows start timing out on world workspace or admin pages.

Performance work should first add a measurement or budget before changing architecture.
