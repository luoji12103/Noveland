# Project Index

## Purpose

Fast orientation for a new coding session.

## Current entrypoints

### Web
- `web/app/` — route entrypoints
- `web/features/` — feature-oriented UI logic
- `web/components/` — reusable UI components
- `web/lib/` — approved web-side helpers only
- `web/package.json` — frontend scripts and dependency manifest

### Backend services
- `backend/services/api/` — HTTP/WebSocket entry
- `backend/services/runtime/` — long-running runtime host
- `backend/pyproject.toml` — backend uv workspace manifest

### Backend packages
- `backend/packages/core/`
  - `noveland.core.database` — SQLAlchemy base, metadata, and session factory
  - `noveland.core.models` — platform settings ORM model
- `backend/packages/worlds/`
  - `noveland.worlds.models` — world, membership, and scene ORM models
- `backend/packages/agents/`
  - `noveland.agents.models` — agent identity ORM model
- `backend/packages/calendar/`
- `backend/packages/narrative/`
- `backend/packages/events/`
- `backend/packages/auth/`
  - `noveland.auth.models` — user identity ORM model
- `backend/packages/memory/`
- `backend/packages/plugins/`
  - `noveland.plugins` — plugin registry, manifest, config validation, and typed errors
- `backend/packages/adapters/`
- `backend/packages/storage/`
- `backend/packages/observability/`

### Contracts
- `contracts/` — shared schemas and public internal contracts

### Infrastructure
- `infra/compose.yaml` — local PostgreSQL/pgvector and NATS JetStream stack

### Database
- `backend/migrations/` — Alembic migration entrypoint and versions

## Update rule

Whenever a new structural file or module is added, update this index.
