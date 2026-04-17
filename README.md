# Noveland

Noveland is a persistent virtual-world operating system for AI agents. The repository is in its early implementation phase: the architecture and governance package is in place, and the implementation now includes a minimal backend API, auth/session baseline, protected world management dashboard, runtime host, and local infrastructure.

## Current Status

- Product and architecture source of truth: `docs/agent/`
- Backend stack: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, uv
- Frontend stack: Next.js, TypeScript, React, Tailwind CSS, Vitest, Playwright
- Local services: PostgreSQL 16 with pgvector, NATS with JetStream
- License: TBD

## Local Setup

Install `uv` before working on the backend:

```sh
python3 -m pip install --user uv
uv python install 3.12
```

Copy local configuration:

```sh
cp .env.example .env
```

Start local infrastructure:

```sh
docker compose -f infra/compose.yaml up -d
```

Apply database migrations from `backend/`:

```sh
uv run alembic upgrade head
```

Seed a local platform admin from `backend/` after migrations:

```sh
uv run noveland-seed-admin \
  --email admin@example.test \
  --password "change-me-local-only" \
  --display-name "Admin"
```

If local ports are already taken, override them before starting Compose:

```sh
NOVELAND_POSTGRES_PORT=55432 NOVELAND_NATS_PORT=44222 NOVELAND_NATS_MONITOR_PORT=48222 \
  docker compose -f infra/compose.yaml up -d
```

Use a matching database URL when running backend commands against the overridden port:

```sh
NOVELAND_DATABASE_URL=postgresql+psycopg://noveland:noveland@localhost:55432/noveland \
  uv run alembic upgrade head
```

Run backend checks from `backend/`:

```sh
uv run ruff check .
uv run mypy .
uv run pytest
```

Run the API from `backend/`:

```sh
uv run uvicorn noveland.services.api.app:app --reload
```

Run one finite runtime tick from `backend/`:

```sh
uv run noveland-runtime
```

Run frontend checks from `web/`:

```sh
npm install
npm run lint
npm run typecheck
npm run test
npm run test:e2e
```

Run the web app from `web/`:

```sh
npm run dev
```

Open `http://127.0.0.1:3000/login` and sign in with the seeded admin account.

## Stable Interfaces

The first stable backend endpoint is:

```http
GET /health
```

Expected response:

```json
{"service":"api","status":"ok","version":"0.1.0"}
```

This health endpoint does not imply database, messaging, world-clock, replay, auth, or plugin readiness.

The initial auth HTTP surface is:

```http
GET /auth/csrf
POST /auth/login
GET /auth/me
POST /auth/logout
```

Auth uses an HttpOnly opaque session cookie named `noveland_session`, a readable CSRF cookie named `noveland_csrf`, and `X-CSRF-Token` for mutating authenticated requests. The web app reaches FastAPI through same-origin Next route handlers under `/api/auth/*`; `NOVELAND_API_BASE_URL` points those handlers at the backend API.

The initial world management API is available under:

```http
GET /worlds
POST /worlds
GET /worlds/{world_id}
PATCH /worlds/{world_id}
DELETE /worlds/{world_id}
GET /worlds/{world_id}/scenes
POST /worlds/{world_id}/scenes
PATCH /worlds/{world_id}/scenes/{scene_id}
DELETE /worlds/{world_id}/scenes/{scene_id}
GET /worlds/{world_id}/memberships
PUT /worlds/{world_id}/memberships/{user_id}
DELETE /worlds/{world_id}/memberships/{user_id}
GET /worlds/{world_id}/member-candidates
GET /worlds/{world_id}/agents
POST /worlds/{world_id}/agents
PATCH /worlds/{world_id}/agents/{agent_id}
DELETE /worlds/{world_id}/agents/{agent_id}
GET /worlds/{world_id}/clock
POST /worlds/{world_id}/clock/pause
POST /worlds/{world_id}/clock/resume
POST /worlds/{world_id}/clock/advance
POST /worlds/{world_id}/clock/skip
GET /worlds/{world_id}/replay/state
GET /worlds/{world_id}/snapshots/latest
POST /worlds/{world_id}/snapshots
```

Mutating world endpoints require the same `noveland_csrf` cookie and `X-CSRF-Token` header used by auth logout. DELETE routes are soft-disable operations; they do not hard-delete world, scene, or agent rows.

The protected web dashboard reads this API through server-side helpers and same-origin `/api/worlds/*` proxy routes. It can create and update worlds, scenes, agents, memberships, world clock state, and inline snapshots according to the current user's backend permissions.

The runtime host remains finite: `noveland-runtime` performs one tick, advances active running clocks, appends `world.clock_advanced` events, and broadcasts event envelopes to NATS on `noveland.world.{world_id}.events`. It does not start an infinite loop, schedule agents, or execute plugins.

## Development Rules

Read `docs/agent/README.md` before changing structure or implementing domain behavior. New structural files must be reflected in the agent harness docs.
