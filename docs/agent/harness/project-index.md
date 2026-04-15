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
- `backend/packages/worlds/`
- `backend/packages/agents/`
- `backend/packages/calendar/`
- `backend/packages/narrative/`
- `backend/packages/events/`
- `backend/packages/auth/`
- `backend/packages/memory/`
- `backend/packages/plugins/`
- `backend/packages/adapters/`
- `backend/packages/storage/`
- `backend/packages/observability/`

### Contracts
- `contracts/` — shared schemas and public internal contracts

### Infrastructure
- `infra/compose.yaml` — local PostgreSQL/pgvector and NATS JetStream stack

## Update rule

Whenever a new structural file or module is added, update this index.
