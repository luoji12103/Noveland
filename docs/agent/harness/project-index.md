# Project Index

## Purpose

Fast orientation for a new coding session.

## Current entrypoints

### Web
- `web/app/` — route entrypoints
- `web/app/login/` — dedicated local sign-in route
- `web/app/api/auth/` — same-origin auth proxy route handlers for the web app
- `web/app/api/worlds/` — same-origin world management proxy route handlers
- `web/features/` — feature-oriented UI logic
  - `web/features/auth/` — login form and logout control
  - `web/features/dashboard/` — protected world management dashboard components
- `web/components/` — reusable UI components
- `web/lib/` — approved web-side helpers only
  - `web/lib/auth/` — auth types, client helpers, server subject lookup, and proxy helpers
  - `web/lib/worlds/` — world API types, browser helpers, server data loader, and proxy helpers
- `web/package.json` — frontend scripts and dependency manifest

### Backend services
- `backend/services/api/` — HTTP/WebSocket entry
  - `noveland.services.api.authorization` — platform and world access helper checks
  - `noveland.services.api.auth` — initial HTTP auth router for CSRF, login, current user, and logout
  - `noveland.services.api.csrf` — cookie and double-submit CSRF helpers
  - `noveland.services.api.dependencies` — API database/session and current-subject dependencies
  - `noveland.services.api.worlds` — initial worlds, scenes, memberships, and agents management router
- `backend/services/runtime/` — long-running runtime host
- `backend/pyproject.toml` — backend uv workspace manifest

### Backend packages
- `backend/packages/core/`
  - `noveland.core.database` — SQLAlchemy base, metadata, and session factory
  - `noveland.core.models` — platform settings ORM model
- `backend/packages/worlds/`
  - `noveland.worlds.clock` — pure world clock state and transition logic
  - `noveland.worlds.models` — world, membership, scene, and clock ORM models
- `backend/packages/agents/`
  - `noveland.agents.models` — agent identity ORM model
- `backend/packages/calendar/`
- `backend/packages/narrative/`
- `backend/packages/events/`
  - `noveland.events` — event/snapshot contracts and store exports
  - `noveland.events.models` — world event log and snapshot metadata ORM models
  - `noveland.events.event_store` — minimal world event append/list/snapshot helper
- `backend/packages/auth/`
  - `noveland.auth` — auth/session contracts, services, and typed errors
  - `noveland.auth.models` — user identity, credential, session, and platform role ORM models
  - `noveland.auth.seed_admin` — local operator command for seeding a platform admin
  - `noveland.auth.services` — password credential and opaque session service helpers
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
- `backend/migrations/` — Alembic migration entrypoint and versions, including core schema, world clock state, event/snapshot baseline, and auth/session baseline

## Update rule

Whenever a new structural file or module is added, update this index.
