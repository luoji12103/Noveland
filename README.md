# Noveland

Noveland is a persistent virtual-world operating system for AI agents. The repository is currently in its first runnable skeleton phase: the architecture and governance package is in place, and the implementation starts with a minimal backend API, runtime host, web shell, and local infrastructure.

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

Auth uses an HttpOnly opaque session cookie named `noveland_session`, a readable CSRF cookie named `noveland_csrf`, and `X-CSRF-Token` for mutating authenticated requests. The web UI is not wired to this flow yet.

## Development Rules

Read `docs/agent/README.md` before changing structure or implementing domain behavior. New structural files must be reflected in the agent harness docs.
