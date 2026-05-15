# Deployment Profile v1

## Purpose

This profile describes the supported local and single-host production-like deployment shape for the current v1 architecture.

It is an internal operator profile, not a public launch checklist. It should help an operator start, validate, migrate, and roll back a local/single-host Noveland stack without adding managed-cloud assumptions.

This document complements:

- `docs/agent/operations/runtime-supervision.md`
- `docs/agent/operations/runtime-recovery.md`
- `docs/agent/operations/backup-restore.md`
- `docs/agent/architecture/configuration-and-secrets.md`

## Supported Components

- PostgreSQL with pgvector, managed by `infra/compose.yaml` locally.
- NATS JetStream, managed by `infra/compose.yaml` locally.
- FastAPI API process, started with `noveland-api` or `uvicorn noveland.services.api.app:app`.
- Next.js Web process.
- Runtime daemon process, started separately with `noveland-runtime --daemon`.
- Local object storage rooted by `NOVELAND_OBJECT_STORAGE_ROOT`.
- Database-backed memory write queue.
- Provider integrations that resolve secrets through opaque refs, not persisted secret values.

## Required Configuration

The complete configuration rules live in `docs/agent/architecture/configuration-and-secrets.md`. This deployment profile expects these values to be set or consciously left at their local defaults:

- `NOVELAND_ENV`
- `NOVELAND_DATABASE_URL`
- `NOVELAND_NATS_URL`
- `NOVELAND_OBJECT_STORAGE_ROOT`
- `NOVELAND_API_BASE_URL`
- `NOVELAND_PROVIDER_API_KEYS_JSON`
- `NOVELAND_MEMORY_BACKEND_SECRETS_JSON`
- `NOVELAND_RUNTIME_LOOP_INTERVAL_SECONDS`
- `NOVELAND_RUNTIME_BATCH_LIMIT`
- `NOVELAND_AUTH_SESSION_TTL_SECONDS`
- `NOVELAND_AUTH_COOKIE_SECURE`
- `NOVELAND_AUTH_COOKIE_SAMESITE`

Provider secrets remain operator-owned environment/settings values. Database rows store reference identifiers such as `env:OPENAI_API_KEY` or entries resolvable through `NOVELAND_PROVIDER_API_KEYS_JSON`; they must not store resolved API keys.

## Startup Order

1. Validate local compose configuration:

   ```sh
   docker compose -f infra/compose.yaml config
   ```

2. Start local dependencies:

   ```sh
   docker compose -f infra/compose.yaml up -d
   ```

3. Apply migrations and confirm the resulting head:

   ```sh
   cd backend
   uv run alembic upgrade head
   uv run alembic current
   ```

4. Seed or verify a platform admin:

   ```sh
   cd backend
   uv run noveland-seed-admin
   ```

5. Start the API:

   ```sh
   cd backend
   uv run noveland-api
   ```

   The equivalent development command is:

   ```sh
   cd backend
   uv run uvicorn noveland.services.api.app:app --reload
   ```

6. Start the Web process:

   ```sh
   cd web
   npm run dev
   ```

7. Start the runtime daemon only after provider integrations, memory backend profiles, migrations, and backup readiness are understood:

   ```sh
   cd backend
   uv run noveland-runtime --daemon
   ```

## Required Validation

Run these local checks before treating the profile as ready:

```sh
docker compose -f infra/compose.yaml config
```

```sh
cd backend
uv run alembic current
uv run noveland-backup-verify
uv run noveland-runtime --once
```

Public process health:

- `GET /health`

```sh
curl -fsS http://127.0.0.1:8000/health
```

Platform-admin checks require a valid `noveland_session` cookie:

- `GET /runtime/supervision`
- `GET /runtime/status`
- `GET /provider-profiles/health`
- `GET /metrics`

```sh
curl -fsS http://127.0.0.1:8000/runtime/supervision \
  -H "Cookie: noveland_session=<session-token>"
curl -fsS http://127.0.0.1:8000/runtime/status \
  -H "Cookie: noveland_session=<session-token>"
curl -fsS http://127.0.0.1:8000/provider-profiles/health \
  -H "Cookie: noveland_session=<session-token>"
curl -fsS http://127.0.0.1:8000/metrics \
  -H "Cookie: noveland_session=<session-token>"
```

Expected checks:

- `/health` reports API process availability only.
- `/runtime/supervision` reports API/database status, desired runtime state, heartbeat freshness, and last runtime error.
- `/runtime/status` reports detailed runtime control, health, and memory queue counts.
- `/provider-profiles/health` reports provider profile health and secret-ref status without resolved secrets.
- `/metrics` returns local text metrics without secrets, storage paths, raw prompts, raw outputs, bytes, or base64.
- `noveland-backup-verify` reports database/object-storage backup readiness before backup or restore operations.
- `noveland-runtime --once` can run one bounded daemon iteration without starting a long-running loop.

## Migration Procedure

Use this procedure for local and single-host deployments:

1. Stop the runtime daemon before applying migrations if it is running.
2. Confirm backup prerequisites with `uv run noveland-backup-verify`.
3. Create a database dump and object-storage archive using `docs/agent/operations/backup-restore.md`.
4. Record the current migration revision:

   ```sh
   cd backend
   uv run alembic current
   ```

5. Apply migrations:

   ```sh
   cd backend
   uv run alembic upgrade head
   ```

6. Re-run validation:
   - `uv run alembic current`
   - `uv run noveland-backup-verify`
   - `uv run noveland-runtime --once`
   - `GET /health`
   - `GET /runtime/supervision`
   - `GET /runtime/status`
   - `GET /provider-profiles/health`

7. Restart the runtime daemon only after validation passes.

## Rollback Prerequisites

Rollback is a backup/restore operation, not an API action.

Before any rollback attempt, the operator must have:

- a verified database dump from before the migration or deployment change
- a matching object-storage archive rooted at `NOVELAND_OBJECT_STORAGE_ROOT`
- the last known good migration revision from `uv run alembic current`
- the runtime daemon stopped
- no active provider generation job that depends on the failed deployment

Use `docs/agent/operations/backup-restore.md` for the restore procedure. After restore, re-run `noveland-backup-verify`, migration status, runtime one-shot, and the platform-admin health checks before restarting the daemon.

## Boundaries

- No managed-cloud platform lock-in.
- No Kubernetes orchestration.
- No autoscaling.
- No public launch checklist.
- No remote object storage provider implementation.
- No destructive restore API.
- No Web deployment UI.
- No new runtime or deployment endpoint for this profile.
- Runtime daemon is a separate process, not an API background task.
- Memory jobs still use the database-backed v1 queue.
- Health and validation output must not expose resolved secrets, storage URIs, filesystem paths, bytes, base64, raw prompts, or raw outputs.
