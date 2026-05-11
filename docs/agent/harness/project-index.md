# Project Index

## Purpose

Fast orientation for a new coding session.

## Planning sources

- `docs/agent/harness/roadmap.md` — completed V1 long-term roadmap and candidate mainline bundles; not the active task board.
- `docs/agent/harness/roadmap-v2-living-world.md` — V2 living-world roadmap for the galgame sequel simulation direction; not the active task board.
- `docs/agent/harness/current-system-architecture-review.md` — current architecture and implementation review for framework-design discussions.
- `docs/agent/harness/feature-updates/` — version-prefixed final feature implementation plans recorded before implementation starts.
- `docs/agent/harness/feature-updates/v0.3.1.1-media-kernel-phase-1-plan.md` — final Media Kernel Phase 1 implementation plan.
- `docs/agent/harness/feature-updates/v0.3.1.2-media-asset-catalog-phase-2-plan.md` — final Media Asset Catalog Phase 2 implementation plan.
- `docs/agent/harness/feature-updates/v0.3.1.3-model-invocation-ledger-phase-3-plan.md` — final Model Invocation Ledger Phase 3 implementation plan.
- `docs/agent/harness/feature-updates/v0.3.1.4-media-kernel-phase-4-plan.md` — final Media Kernel Phase 4 additive extension implementation plan.
- `docs/agent/harness/task-board.md` — current execution state only.
- `docs/agent/operations/runtime-recovery.md` — local operator recovery playbook for runtime, provider, memory queue, event audit, and snapshot integrity incidents.
- `docs/agent/operations/backup-restore.md` — local operator backup/restore workflow for database dumps plus object storage payload archives.
- `docs/agent/operations/deployment-profile.md` — supported local/single-host deployment shape and startup checks.
- `docs/agent/operations/runtime-supervision.md` — operator interpretation for runtime process liveness, heartbeat, and metrics.
- `docs/agent/operations/diagnostic-retention.md` — diagnostic retention dry-run/prune policy.
- `docs/agent/operations/memory-queue-readiness.md` — DB-backed memory queue readiness and backfill execution rules.
- `docs/agent/operations/performance-budget.md` — local performance budgets and regression signals.
- `docs/agent/operations/sandbox-options.md` — design-only sandbox option comparison and selection criteria.
- `docs/agent/operations/external-tool-policy.md` — policy-only external tool allow/deny boundary; no execution path.
- `docs/agent/operations/scale-readiness.md` — derived scale-readiness report interpretation.
- `docs/agent/operations/living-world-release-profile.md` — living-world release profile and beta checklist operator workflow.
- `docs/agent/harness/v2-readiness-review.md` — evidence-based closeout review for the current 50-phase roadmap.

## Current entrypoints

### Web
- `web/app/` — route entrypoints
- `web/app/login/` — dedicated local sign-in route
- `web/app/worlds/` — world-first workspace pages for world overview, agents, conversations, narrative management, and reader surfaces
- `web/app/admin/` — platform-admin pages for presets, provider profiles, and runtime control
- `web/app/admin/memory-backends/` — platform-admin memory backend profile, health, log, job retry, and eval surface
- `web/app/admin/presets/` — platform-admin preset catalog management page
- `web/app/api/auth/` — same-origin auth proxy route handlers for the web app
- `web/app/api/memory-backend-profiles/` — same-origin memory backend profile, health, log, job list, and eval proxy route handlers
- `web/app/api/memory-write-jobs/` — same-origin memory write job retry proxy route handlers
- `web/app/api/agent-presets/` — same-origin preset admin proxy route handlers
- `web/app/api/worlds/` — same-origin world management proxy route handlers
- `web/app/api/world-compositions/` — same-origin world composition validation/import proxy route handlers
- `web/app/api/runtime/` — same-origin runtime control proxy route handlers
- `web/app/api/runtime/stream/` — same-origin platform runtime SSE proxy route
- `web/app/api/plugins/catalog/` — same-origin plugin catalog proxy route handler
- `web/app/api/plugins/bindings/` — same-origin plugin binding validation proxy route handler
- `web/app/api/provider-profiles/` — same-origin provider profile and test-call proxy route handlers
- `web/app/api/worlds/[worldId]/stream/` — same-origin world SSE proxy route
- `web/app/api/worlds/[worldId]/conversations/[conversationId]/stream/` — same-origin conversation SSE proxy route
- `web/features/` — feature-oriented UI logic
  - `web/features/auth/` — login form and logout control
  - `web/features/admin/` — platform-level preset, provider, runtime, and memory backend management pages
  - `web/features/plugins/` — schema-driven plugin config controls with raw JSON fallback
  - `web/features/agents/` — agent list and focused agent builder pages with preset-aware creation and provenance display
  - `web/features/conversations/` — conversation list/detail pages, transcript controls, writer config, and narrative generation UI
  - `web/features/dashboard/` — protected world management, runtime, diagnostics, and narrative dashboard components
  - `web/features/worlds/` — world index, overview, narrative management workspace, and read-only reader components
  - `web/features/workspace/` — shared workspace shell and form helpers
- `web/components/` — reusable UI components
- `web/lib/` — approved web-side helpers only
  - `web/lib/auth/` — auth types, client helpers, server subject lookup, and proxy helpers
  - `web/lib/api-proxy.ts` — shared same-origin proxy helper for preset and composition routes
  - `web/lib/realtime/` — same-origin streaming proxy helper
  - `web/lib/realtime.ts` — browser-side EventSource and conversation live WebSocket helpers
  - `web/lib/worlds/` — world API types, browser helpers, server data loader, and proxy helpers
  - `web/lib/runtime/` — runtime/provider proxy helper shared by Next route handlers
- `web/package.json` — frontend scripts and dependency manifest

### Backend services
- `backend/services/api/` — HTTP/WebSocket entry
  - `noveland.services.api.authorization` — platform and world access helper checks
  - `noveland.services.api.auth` — initial HTTP auth router for CSRF, login, current user, and logout
  - `noveland.services.api.csrf` — cookie and double-submit CSRF helpers
  - `noveland.services.api.dependencies` — API database/session and current-subject dependencies
  - `noveland.services.api.runtime` — platform-admin runtime control, supervision, external tool policy, scale readiness, metrics, diagnostics retention, provider profile, plugin binding validation, memory backend profile, memory backfill, queue readiness, and memory write job operator router
  - `noveland.services.api.realtime` — runtime/world/conversation SSE delta routes and conversation live WebSocket control
  - `noveland.services.api.conversations` — world-scoped conversation session, participant, transcript, stop, diagnostics, and conversation narrative router
  - `noveland.services.api.media` — world-scoped media asset, job, context, tag, collection, search, reference, and lineage router
  - `noveland.services.api.invocations` — world-scoped model invocation ledger, prompt snapshot, tag, template, redaction, and search router
  - `noveland.services.api.worlds` — worlds, scenes, memberships, agents, calendar, schedule preview, memory, persona/observations, clock transition audit, replay, snapshot integrity, event audit, diagnostics, agent runs, living-world beta readiness, and filtered narrative artifact router
- `backend/services/runtime/` — long-running runtime host
  - `noveland.services.runtime.clock_tick` — finite runtime tick service for advancing running clocks and emitting world events
  - `noveland.services.runtime.agent_loop` — provider-backed agent execution with model invocation ledger/snapshot recording, memory context retrieval, async memory job enqueue, and narrative artifact creation
  - `noveland.services.runtime.conversation_loop` — deterministic round-robin conversation turn advancement for manual chains and auto dialogue, including conversation memory configuration and optional completed-session narrative auto-generation
  - `noveland.services.runtime.daemon` — database-backed runtime control state, daemon loop orchestration, and due memory job processing status
  - `noveland.services.runtime.identity` — shared runtime actor ref used by runtime-created events and service paths
- `backend/pyproject.toml` — backend uv workspace manifest

### Backend packages
- `backend/packages/core/`
  - `noveland.core.database` — SQLAlchemy base, metadata, and session factory
  - `noveland.core.models` — platform settings and runtime control ORM models
- `backend/packages/worlds/`
  - `noveland.worlds.clock` — pure world clock state and transition logic
  - `noveland.worlds.clock_service` — persistent world clock state and transition audit service
  - `noveland.worlds.beta` — deterministic route/ending, eval, authoring, release profile, and beta checklist service
  - `noveland.worlds.models` — world, membership, scene, and clock ORM models
- `backend/packages/agents/`
  - `noveland.agents.contracts` — persona, filtered observation, and agent preset DTOs
  - `noveland.agents.models` — agent identity, runtime run, persona, observation, and preset ORM models
  - `noveland.agents.services` — persona/observation helpers plus preset CRUD, provider resolution, and calendar blueprint materialization
- `backend/packages/calendar/`
  - `noveland.calendar.contracts` — calendar entry and schedule rule contracts
  - `noveland.calendar.models` — agent calendar and world schedule rule ORM models
  - `noveland.calendar.services` — calendar CRUD and due-resolution service
- `backend/packages/conversations/`
  - `noveland.conversations.contracts` — conversation session, participant, turn, policy, stop-condition, writer-config, and memory-config DTOs
  - `noveland.conversations.models` — conversation session, participant, and turn ORM models
  - `noveland.conversations.services` — deterministic round-robin conversation service, stop-condition handling, diagnostics recording, transcript persistence, writer-config mapping, and memory-config mapping
- `backend/packages/narrative/`
  - `noveland.narrative.contracts` — narrative artifact contracts plus conversation narrative generation inputs
  - `noveland.narrative.models` — narrative artifact ORM model with optional source conversation linkage
  - `noveland.narrative.services` — narrative artifact create/list helpers and conversation-first writer pipeline
- `backend/packages/events/`
  - `noveland.events` — event/snapshot contracts and store exports
  - `noveland.events.models` — world event log and snapshot metadata ORM models
  - `noveland.events.event_store` — minimal world event append/list/snapshot helper
  - `noveland.events.publisher` — world event envelope and NATS/in-memory publisher interfaces
  - `noveland.events.replay` — replay state reconstruction, object-storage-backed snapshot creation with inline fallback, and snapshot integrity reporting service
- `backend/packages/auth/`
  - `noveland.auth` — auth/session contracts, services, and typed errors
  - `noveland.auth.models` — user identity, credential, session, and platform role ORM models
  - `noveland.auth.seed_admin` — local operator command for seeding a platform admin
  - `noveland.auth.services` — password credential and opaque session service helpers
- `backend/packages/memory/`
  - `noveland.memory.contracts` — long-term memory profile, lookup, job, log, snapshot, eval, backfill, queue-readiness, and backend contracts
  - `noveland.memory.errors` — typed long-term memory validation and execution errors
  - `noveland.memory.models` — memory backend profiles, write jobs/logs, retrieval logs, agent profile snapshots, and local fallback memory ORM models
  - `noveland.memory.service` — `MemoryService` facade for profile CRUD, context retrieval, async write processing, write job listing/retry/status, backfill dry-run/execution, queue readiness, forget, health, logs, and eval flows
  - `noveland.memory.evals` — smoke-eval helpers and operator recommendations for backend contract coverage
  - `noveland.memory.backends/` — abstract backend protocol plus fake and Mem0 OSS adapters
  - `noveland.memory.local_pgvector` — local pgvector fallback backend and deterministic local search implementation
  - `noveland.memory.vector_type` — shared embedding dimension and SQLAlchemy vector type adapter
- `backend/packages/media/`
  - `noveland.media.catalog` — media asset tag, collection, search, reference, and visibility-safe lineage services
  - `noveland.media.contracts` — Media Kernel enums and DTOs for assets, jobs, contexts, inputs, tags, collections, references, search, and lineage
  - `noveland.media.models` — worldline-scoped media asset, job, context, input, tag, collection, and collection item ORM models
  - `noveland.media.service` — media asset/context/lineage service and queued media job service
  - `noveland.media.storage` — binary local media object storage facade with opaque `media://` URIs
- `backend/packages/invocations/`
  - `noveland.invocations.contracts` — invocation, prompt template, prompt snapshot, tag, search, redaction, retention, and runtime-run link DTOs
  - `noveland.invocations.models` — worldline-scoped model invocation, prompt template, prompt snapshot, runtime-run join, and invocation tag ORM models
  - `noveland.invocations.service` — invocation ledger, prompt snapshot/template, tag, redaction, worldline validation, search, and runtime-run link services
  - `noveland.invocations.redaction` — checksum and redaction mode helpers for prompt/output persistence
  - `noveland.invocations.search` — repeatable tag filter parsing helpers shared by API search
- `backend/packages/plugins/`
  - `noveland.plugins` — plugin registry, manifest, config validation, typed errors, and lazy public exports
  - `noveland.plugins.builtins` — first-party plugin implementations and built-in plugin registry
  - `noveland.plugins.constants` — stable built-in plugin identifiers used by migrations and bindings
- `backend/packages/adapters/`
  - `noveland.adapters.model_provider` — provider profile contracts, reliability settings, test-call support, services, and model-provider adapters
  - `noveland.adapters.models` — provider profile ORM model and provider health fields
- `backend/packages/storage/`
  - `noveland.storage.local` — local filesystem object storage rooted by `NOVELAND_OBJECT_STORAGE_ROOT`
  - `noveland.storage.backup` — local backup verification command for database, migration head, object root, and snapshot payload readability checks
- `backend/packages/observability/`
  - `noveland.observability.contracts` — diagnostic severity/component contracts, record DTOs, and retention DTOs, including conversation diagnostics
  - `noveland.observability.models` — runtime diagnostic event ORM model
  - `noveland.observability.services` — runtime diagnostic record/list service, retention dry-run/prune helpers, and detail redaction

### Contracts
- `contracts/` — shared schemas and public internal contracts

### Infrastructure
- `infra/compose.yaml` — local PostgreSQL/pgvector and NATS JetStream stack

### Database
- `backend/migrations/` — Alembic migration entrypoint and versions, including core schema, world clock state, event/snapshot baseline, auth/session baseline, calendar, long-term memory refactor (Mem0 OSS foundation, context integration, profiles/forget/evals), agent/runtime narrative baseline, runtime diagnostics, provider reliability, agent persona/observations, conversation workspace baseline, conversation policy/stop-condition baseline, narrative writer/summarizer baseline, agent composition presets, explicit plugin runtime bindings, narrative publications, observation traceability, agent preset versioning, plugin diagnostic component support, V2 living-world state through beta release readiness, runtime worldline memory-isolation remediation, Media Kernel/Catalog migrations, and the Model Invocation Ledger migration

## Update rule

Whenever a new structural file or module is added, update this index.
