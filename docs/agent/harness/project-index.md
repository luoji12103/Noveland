# Project Index

## Purpose

Fast orientation for a new coding session.

## Current entrypoints

### Web
- `web/app/` — route entrypoints
- `web/app/login/` — dedicated local sign-in route
- `web/app/worlds/` — world-first workspace pages for world overview, agents, conversations, and narrative artifacts
- `web/app/admin/` — platform-admin pages for provider profiles and runtime control
- `web/app/api/auth/` — same-origin auth proxy route handlers for the web app
- `web/app/api/worlds/` — same-origin world management proxy route handlers
- `web/app/api/runtime/` — same-origin runtime control proxy route handlers
- `web/app/api/provider-profiles/` — same-origin provider profile and test-call proxy route handlers
- `web/features/` — feature-oriented UI logic
  - `web/features/auth/` — login form and logout control
  - `web/features/admin/` — platform-level provider and runtime management pages
  - `web/features/agents/` — agent list and focused agent builder pages
  - `web/features/conversations/` — conversation list/detail pages and transcript controls
  - `web/features/dashboard/` — protected world management, runtime, diagnostics, and narrative dashboard components
  - `web/features/worlds/` — world index, overview, and narrative workspace components
  - `web/features/workspace/` — shared workspace shell and form helpers
- `web/components/` — reusable UI components
- `web/lib/` — approved web-side helpers only
  - `web/lib/auth/` — auth types, client helpers, server subject lookup, and proxy helpers
  - `web/lib/worlds/` — world API types, browser helpers, server data loader, and proxy helpers
  - `web/lib/runtime/` — runtime/provider proxy helper shared by Next route handlers
- `web/package.json` — frontend scripts and dependency manifest

### Backend services
- `backend/services/api/` — HTTP/WebSocket entry
  - `noveland.services.api.authorization` — platform and world access helper checks
  - `noveland.services.api.auth` — initial HTTP auth router for CSRF, login, current user, and logout
  - `noveland.services.api.csrf` — cookie and double-submit CSRF helpers
  - `noveland.services.api.dependencies` — API database/session and current-subject dependencies
  - `noveland.services.api.runtime` — platform-admin runtime control, diagnostics, and provider profile router
  - `noveland.services.api.conversations` — world-scoped conversation session, participant, transcript, and control router
  - `noveland.services.api.worlds` — worlds, scenes, memberships, agents, calendar, memory, persona/observations, clock, replay, snapshots, diagnostics, agent runs, and narrative router
- `backend/services/runtime/` — long-running runtime host
  - `noveland.services.runtime.clock_tick` — finite runtime tick service for advancing running clocks and emitting world events
  - `noveland.services.runtime.agent_loop` — provider-backed agent execution, memory writes, and narrative artifact creation
  - `noveland.services.runtime.conversation_loop` — deterministic round-robin conversation turn advancement for manual chains and auto dialogue
  - `noveland.services.runtime.daemon` — database-backed runtime control state and daemon loop orchestration
- `backend/pyproject.toml` — backend uv workspace manifest

### Backend packages
- `backend/packages/core/`
  - `noveland.core.database` — SQLAlchemy base, metadata, and session factory
  - `noveland.core.models` — platform settings and runtime control ORM models
- `backend/packages/worlds/`
  - `noveland.worlds.clock` — pure world clock state and transition logic
  - `noveland.worlds.clock_service` — persistent world clock state and transition audit service
  - `noveland.worlds.models` — world, membership, scene, and clock ORM models
- `backend/packages/agents/`
  - `noveland.agents.contracts` — persona and filtered observation DTOs
  - `noveland.agents.models` — agent identity, runtime run, persona, and observation ORM models
  - `noveland.agents.services` — persona upsert plus filtered observation list/create/refresh helpers
- `backend/packages/calendar/`
  - `noveland.calendar.contracts` — calendar entry and schedule rule contracts
  - `noveland.calendar.models` — agent calendar and world schedule rule ORM models
  - `noveland.calendar.services` — calendar CRUD and due-resolution service
- `backend/packages/conversations/`
  - `noveland.conversations.contracts` — conversation session, participant, turn, and control DTOs
  - `noveland.conversations.models` — conversation session, participant, and turn ORM models
  - `noveland.conversations.services` — deterministic round-robin conversation service and transcript persistence
- `backend/packages/narrative/`
  - `noveland.narrative.contracts` — narrative artifact contracts
  - `noveland.narrative.models` — narrative artifact ORM model
  - `noveland.narrative.services` — narrative artifact create/list service
- `backend/packages/events/`
  - `noveland.events` — event/snapshot contracts and store exports
  - `noveland.events.models` — world event log and snapshot metadata ORM models
  - `noveland.events.event_store` — minimal world event append/list/snapshot helper
  - `noveland.events.publisher` — world event envelope and NATS/in-memory publisher interfaces
  - `noveland.events.replay` — replay state reconstruction and inline snapshot creation service
- `backend/packages/auth/`
  - `noveland.auth` — auth/session contracts, services, and typed errors
  - `noveland.auth.models` — user identity, credential, session, and platform role ORM models
  - `noveland.auth.seed_admin` — local operator command for seeding a platform admin
  - `noveland.auth.services` — password credential and opaque session service helpers
- `backend/packages/memory/`
  - `noveland.memory.contracts` — memory item and search contracts plus backend protocol
  - `noveland.memory.models` — agent memory ORM model
  - `noveland.memory.local_pgvector` — local pgvector-backed memory helper with add/list/search/disable
  - `noveland.memory.vector_type` — shared embedding dimension and SQLAlchemy vector type adapter
- `backend/packages/plugins/`
  - `noveland.plugins` — plugin registry, manifest, config validation, and typed errors
- `backend/packages/adapters/`
  - `noveland.adapters.model_provider` — provider profile contracts, reliability settings, test-call support, services, and model-provider adapters
  - `noveland.adapters.models` — provider profile ORM model and provider health fields
- `backend/packages/storage/`
- `backend/packages/observability/`
  - `noveland.observability.contracts` — diagnostic severity/component contracts and record DTOs
  - `noveland.observability.models` — runtime diagnostic event ORM model
  - `noveland.observability.services` — runtime diagnostic record/list service and detail redaction

### Contracts
- `contracts/` — shared schemas and public internal contracts

### Infrastructure
- `infra/compose.yaml` — local PostgreSQL/pgvector and NATS JetStream stack

### Database
- `backend/migrations/` — Alembic migration entrypoint and versions, including core schema, world clock state, event/snapshot baseline, auth/session baseline, calendar, memory, agent/runtime narrative baseline, runtime diagnostics, provider reliability, agent persona/observations, and conversation workspace baseline

## Update rule

Whenever a new structural file or module is added, update this index.
