# Deployment Profile v1

## Purpose

This profile describes the supported local and single-host deployment shape for the current v1 architecture.

## Components

- PostgreSQL with pgvector, managed by `infra/compose.yaml` locally.
- NATS JetStream, managed by `infra/compose.yaml` locally.
- FastAPI API process, started with `noveland-api` or `uvicorn noveland.services.api.app:app`.
- Next.js Web process.
- Runtime daemon process, started separately with `noveland-runtime --daemon`.
- Local object storage rooted by `NOVELAND_OBJECT_STORAGE_ROOT`.

## Startup Order

1. Start PostgreSQL and NATS.
2. Run `cd backend && uv run alembic upgrade head`.
3. Seed or verify a platform admin with `noveland-seed-admin`.
4. Start API.
5. Start Web.
6. Start runtime daemon only after provider and memory profiles are configured.

## Required Checks

```sh
cd backend
uv run alembic current
uv run noveland-backup-verify
uv run noveland-runtime --once
```

```sh
curl -fsS http://127.0.0.1:8000/health
```

Platform-admin checks:

- `GET /runtime/supervision`
- `GET /runtime/status`
- `GET /provider-profiles/health`
- `GET /metrics`

## Boundaries

- This profile does not include remote object storage, distributed workers, managed secrets, autoscaling, or hard sandboxing.
- Runtime daemon is a separate process, not an API background task.
- Memory jobs still use the database-backed v1 queue.
