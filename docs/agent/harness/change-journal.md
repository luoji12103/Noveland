# Change Journal

## Entry format

- Date:
- Branch:
- Scope:
- Summary:
- Files changed:
- Tests added/updated:
- Docs updated:
- Follow-up notes:

## Initial entry

- Date: TBD
- Branch: TBD
- Scope: docs/agent
- Summary: Initial governance package created.
- Files changed: `/docs/agent/**`
- Tests added/updated: N/A
- Docs updated: initial package
- Follow-up notes: scaffold repository next

## Storage backup auth runtime ops entry

- Date: 2026-05-04
- Branch: feat/storage-backup-auth-runtime-ops
- Scope: snapshot object storage, backup/restore ops, migration safety, auth hardening, runtime identity
- Summary: Added local object storage for new world snapshot replay payloads with inline fallback, backup verification tooling and playbook, Alembic safety checks, configurable auth session/cookie policy, seed-admin password validation, and centralized runtime actor identity for runtime-created events.
- Files changed: `/backend/packages/storage/**`, `/backend/packages/events/src/noveland/events/replay.py`, `/backend/services/api/src/noveland/services/api/{auth,csrf,worlds}.py`, `/backend/services/runtime/src/noveland/services/runtime/**`, `/backend/packages/core/src/noveland/core/settings.py`, `/backend/packages/auth/src/noveland/auth/seed_admin.py`, `/backend/packages/conversations/src/noveland/conversations/services.py`, `/backend/tests/**`, `/web/features/**`, `/web/lib/worlds/**`, `/.env.example`, `/README.md`, `/docs/agent/**`
- Tests added/updated: replay snapshot URI/integrity tests, migration safety tests, auth cookie policy tests, runtime daemon actor-ref tests, and Web snapshot metadata tests.
- Docs updated: README, backup/restore playbook, migrations README, project index, file inventory, task board, active handoff
- Follow-up notes: backup/restore remains local operator-driven; Web restore actions, remote object storage providers, and production secret/session policy enforcement remain later roadmap work.

## Access diagnostics scale readiness ops entry

- Date: 2026-05-04
- Branch: feat/access-diagnostics-scale-roadmap-plan
- Scope: access review, diagnostic retention, metrics, runtime supervision, deployment/performance ops, memory eval/backfill, queue readiness, sandbox design
- Summary: Added world access review and membership audit diagnostics, diagnostic retention dry-run/prune endpoints, platform-admin metrics and runtime supervision surfaces, memory eval recommendations, bounded memory backfill execution, DB queue readiness reporting, and ops docs for deployment, supervision, performance, diagnostics, queue readiness, and sandbox options.
- Files changed: `/backend/packages/observability/**`, `/backend/packages/memory/**`, `/backend/services/api/src/noveland/services/api/{runtime,worlds}.py`, `/backend/tests/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: runtime API tests for metrics/supervision/diagnostic retention/memory backfill/queue readiness; world API tests for access review and membership audit diagnostics; memory service tests for backfill idempotency and queue readiness.
- Docs updated: README, operations docs, project index, file inventory, task board, active handoff
- Follow-up notes: sandbox remains design-only; metrics are local text output; external queue adoption remains out of scope until a later queue migration phase.

## Runnable skeleton entry

- Date: 2026-04-15
- Branch: feat/bootstrap-runnable-skeleton
- Scope: repository scaffold
- Summary: Added runnable backend, web, contracts, and local infrastructure skeletons without implementing sensitive domain behavior.
- Files changed: `/README.md`, `/.editorconfig`, `/.gitignore`, `/.env.example`, `/backend/**`, `/web/**`, `/contracts/README.md`, `/infra/compose.yaml`, `/docs/agent/harness/**`
- Tests added/updated: backend health/import/Alembic config tests; frontend status component test; Playwright dashboard smoke test
- Docs updated: project index, file inventory, task board, debug journal, active handoff
- Follow-up notes: implement core database schema, plugin registry, world clock, event/snapshot baseline, and auth/session baseline as separate tasks.

## Core schema entry

- Date: 2026-04-15
- Branch: main
- Scope: core database schema
- Summary: Added SQLAlchemy metadata, core ORM models, first Alembic migration, and parameterized local database ports.
- Files changed: `/backend/packages/core/**`, `/backend/packages/auth/**`, `/backend/packages/worlds/**`, `/backend/packages/agents/**`, `/backend/migrations/**`, `/backend/tests/**`, `/.env.example`, `/infra/compose.yaml`, `/README.md`, `/docs/agent/**`
- Tests added/updated: schema metadata tests; workspace import coverage for ORM modules
- Docs updated: configuration/secrets, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: plugin registry, world clock state, event/snapshot baseline, and auth/session baseline remain separate tasks.

## Plugin registry skeleton entry

- Date: 2026-04-15
- Branch: feat/plugin-registry-skeleton
- Scope: plugin registry skeleton
- Summary: Added code-registered plugin contracts, manifest/config validation, typed registry errors, and contract tests.
- Files changed: `/backend/packages/plugins/**`, `/backend/tests/test_plugin_registry.py`, `/backend/tests/test_workspace_imports.py`, `/docs/agent/architecture/plugin-architecture.md`, `/docs/agent/harness/**`
- Tests added/updated: plugin registry contract tests; workspace import coverage for plugin modules
- Docs updated: plugin architecture, project index, file inventory, task board, active handoff
- Follow-up notes: world clock state model, event/snapshot baseline, and auth/session baseline remain separate tasks.

## World clock state model entry

- Date: 2026-04-15
- Branch: feat/world-clock-state-model
- Scope: world clock state model
- Summary: Added immutable world clock state transitions, current clock state persistence, transition audit persistence, and schema tests.
- Files changed: `/backend/packages/worlds/**`, `/backend/migrations/versions/20260415_0002_world_clock_state.py`, `/backend/tests/**`, `/backend/migrations/README.md`, `/docs/agent/architecture/world-clock-and-scheduling.md`, `/docs/agent/architecture/data-ownership.md`, `/docs/agent/harness/**`
- Tests added/updated: world clock pure logic tests; schema metadata coverage for clock tables; workspace import coverage for `noveland.worlds.clock`
- Docs updated: world clock scheduling, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: event/snapshot baseline and auth/session baseline remain separate tasks; runtime ticking, scheduling, calendar parsing, and UI controls are not implemented.

## Event log and snapshot baseline entry

- Date: 2026-04-16
- Branch: feat/event-snapshot-baseline
- Scope: event log and snapshot baseline
- Summary: Added world event/snapshot contracts, ORM models, Alembic migration, and a minimal transactional event store helper.
- Files changed: `/backend/packages/events/**`, `/backend/packages/core/src/noveland/core/database.py`, `/backend/migrations/versions/20260416_0003_event_snapshot_baseline.py`, `/backend/tests/**`, `/backend/migrations/README.md`, `/docs/agent/architecture/event-and-snapshot-model.md`, `/docs/agent/architecture/data-ownership.md`, `/docs/agent/harness/**`
- Tests added/updated: event contract tests; schema metadata coverage for event/snapshot tables; skipped-by-default PostgreSQL integration test for `WorldEventStore`
- Docs updated: event/snapshot architecture, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: auth/session baseline remains separate; replay engine, runtime event emission, NATS broadcast, UI controls, and object storage writes are not implemented.

## Auth/session baseline entry

- Date: 2026-04-16
- Branch: feat/auth-session-baseline
- Scope: auth/session baseline
- Summary: Added local password credential storage, opaque backend session storage, platform role assignments, typed auth contracts, and service helpers.
- Files changed: `/backend/packages/auth/**`, `/backend/migrations/versions/20260416_0004_auth_session_baseline.py`, `/backend/tests/**`, `/backend/migrations/README.md`, `/docs/agent/architecture/auth-and-access-model.md`, `/docs/agent/architecture/configuration-and-secrets.md`, `/docs/agent/architecture/data-ownership.md`, `/docs/agent/harness/**`
- Tests added/updated: auth contract tests; schema metadata coverage for auth tables; skipped-by-default PostgreSQL integration test for credential/session services
- Docs updated: auth/access model, configuration/secrets, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: login HTTP API, cookie/CSRF policy, OAuth/OIDC, password reset, MFA, auth middleware, agent runtime credential, and UI integration remain separate tasks.

## HTTP auth surface entry

- Date: 2026-04-16
- Branch: feat/http-auth-surface
- Scope: HTTP auth surface
- Summary: Added CSRF, login, current user, logout endpoints, API database dependencies, and local platform admin seed command.
- Files changed: `/backend/services/api/**`, `/backend/packages/auth/**`, `/backend/tests/test_api_auth.py`, `/backend/tests/test_api_auth_integration.py`, `/backend/tests/test_workspace_imports.py`, `/README.md`, `/docs/agent/**`
- Tests added/updated: API auth contract tests; skipped-by-default PostgreSQL seed/login/logout integration test; workspace import coverage for new API and seed modules
- Docs updated: README, auth/access model, configuration/secrets, project index, file inventory, task board, active handoff
- Follow-up notes: frontend login UI, OAuth/OIDC, password reset, MFA, authorization middleware, world access enforcement, and production cookie hardening remain separate tasks.

## Web auth integration entry

- Date: 2026-04-16
- Branch: feat/web-auth-integration
- Scope: web auth integration
- Summary: Added same-origin Next auth proxy routes, protected dashboard access, dedicated login page, current-user display, and logout flow.
- Files changed: `/web/app/**`, `/web/features/auth/**`, `/web/lib/auth/**`, `/web/tests/e2e/**`, `/.env.example`, `/README.md`, `/docs/agent/**`
- Tests added/updated: auth client tests; login/logout component tests; proxy helper tests; Playwright auth flow tests with local mock backend
- Docs updated: README, auth/access model, configuration/secrets, project index, file inventory, task board, active handoff
- Follow-up notes: authorization dependencies, world management APIs, real dashboard data, OAuth/OIDC, password reset, MFA, and production cookie hardening remain separate tasks.

## Authorization dependencies entry

- Date: 2026-04-16
- Branch: feat/authorization-dependencies
- Scope: API authorization dependencies
- Summary: Added lightweight platform-admin, world-member, and world-admin checks for backend route dependencies.
- Files changed: `/backend/services/api/**`, `/backend/packages/worlds/**`, `/backend/packages/agents/**`, `/backend/tests/**`, `/docs/agent/**`
- Tests added/updated: authorization dependency tests; workspace import coverage for authorization helpers
- Docs updated: auth/access model, project index, file inventory, task board, active handoff
- Follow-up notes: world management APIs, real dashboard data, broad policy engine, and frontend world access UI remain separate tasks.

## World management API entry

- Date: 2026-04-16
- Branch: feat/world-management-api
- Scope: world management API
- Summary: Added backend endpoints for worlds, scenes, memberships, and agents using the authorization dependency baseline.
- Files changed: `/backend/services/api/**`, `/backend/tests/test_api_worlds.py`, `/backend/tests/test_api_worlds_integration.py`, `/README.md`, `/docs/agent/**`
- Tests added/updated: SQLite-backed world management API tests; skipped-by-default PostgreSQL integration smoke; workspace import coverage for world router
- Docs updated: README, auth/access model, project index, file inventory, task board, active handoff
- Follow-up notes: real dashboard data, runtime loops, event emission, world clock controls, plugin execution, and Web world management UI remain separate tasks.

## World dashboard data entry

- Date: 2026-04-16
- Branch: feat/world-dashboard-data
- Scope: world dashboard data and management console
- Summary: Connected the protected web dashboard to the backend world API, added same-origin world proxy routes, added admin management controls, and extended backend world routes with CSRF, member candidates, membership user summaries, and soft-disable DELETE routes.
- Files changed: `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/test_api_worlds.py`, `/web/app/**`, `/web/features/dashboard/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: backend world API CSRF/member-candidate/soft-disable tests; world client/proxy/component tests; Playwright dashboard management flows with local mock backend
- Docs updated: README, auth/access model, project index, file inventory, task board, active handoff
- Follow-up notes: runtime clock service, event emission, replay, calendar rules, memory backend, and agent loop remain separate tasks.

## Runtime clock service entry

- Date: 2026-04-17
- Branch: feat/runtime-clock-service
- Scope: runtime clock service
- Summary: Added persistent world clock service, automatic clock initialization on world creation, clock control HTTP endpoints, and Web clock controls in the dashboard.
- Files changed: `/backend/packages/worlds/**`, `/backend/services/api/**`, `/backend/tests/**`, `/web/features/dashboard/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: clock service persistence tests; clock API permission/CSRF tests; Web client/component/E2E coverage for clock controls
- Docs updated: README, world clock architecture, project index, file inventory, task board, active handoff
- Follow-up notes: runtime event emission, NATS broadcast, replay, calendar rules, memory backend, and agent loop remain separate tasks.

## Runtime event emission and NATS baseline entry

- Date: 2026-04-17
- Branch: feat/runtime-event-nats-baseline
- Scope: runtime event emission and NATS broadcast baseline
- Summary: Added world event publisher interfaces, NATS event envelope broadcasting, and a finite runtime tick service that advances active running clocks and appends `world.clock_advanced` events.
- Files changed: `/backend/packages/events/**`, `/backend/services/runtime/**`, `/backend/tests/test_runtime_event_emission.py`, `/README.md`, `/docs/agent/**`
- Tests added/updated: runtime tick tests for running/paused clocks, event log append behavior, in-memory publisher envelopes, publish failure visibility, and workspace import coverage
- Docs updated: README, event/snapshot model, world clock architecture, project index, file inventory, task board, active handoff
- Follow-up notes: replay/snapshot restore, infinite runtime loop, external scheduler, agent loop, calendar rules, memory backend, and plugin execution remain separate tasks.

## Replay and snapshot restore baseline entry

- Date: 2026-04-17
- Branch: feat/replay-snapshot-restore
- Scope: replay and snapshot restore baseline
- Summary: Added `world_state.v1` replay reconstruction, inline snapshot creation, replay/snapshot HTTP endpoints, and a Web dashboard replay/snapshot panel.
- Files changed: `/backend/packages/events/**`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/**`, `/web/features/dashboard/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: replay service tests for empty state, latest snapshot plus incremental events, snapshot creation; API tests for replay/snapshot auth and CSRF; Web client/component/E2E coverage for replay and snapshots
- Docs updated: README, event/snapshot model, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: destructive restore, object-storage snapshot payload writes, calendar rules, memory backend, agent loop, narrative behavior, and plugin execution remain separate tasks.

## Calendar and schedule rules baseline entry

- Date: 2026-04-17
- Branch: feat/calendar-schedule-baseline
- Scope: agent calendar entries and world schedule rules
- Summary: Added world-scoped agent calendar entries, weekday/weekend/timetable schedule rules, service-level due resolution, backend APIs, and Web dashboard panels.
- Files changed: `/backend/packages/calendar/**`, `/backend/migrations/versions/20260417_0005_calendar_schedule_baseline.py`, `/backend/services/api/**`, `/backend/tests/**`, `/web/features/dashboard/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: calendar contract/service tests, schema metadata tests, world API tests, Web client/component/E2E coverage
- Docs updated: README, data ownership, world clock/scheduling, project index, file inventory, task board, active handoff
- Follow-up notes: memory vectors, provider profiles, runtime agent loop, narrative artifacts, and plugin execution remain separate tasks.

## Memory backend and local pgvector baseline entry

- Date: 2026-04-17
- Branch: feat/memory-pgvector-baseline
- Scope: private agent memory baseline
- Summary: Added the local pgvector-backed memory contract and ORM model, world-admin memory APIs, migration coverage, and a Web dashboard panel for viewing, adding, searching, and disabling agent memory items.
- Files changed: `/backend/packages/memory/**`, `/backend/migrations/versions/20260417_0006_memory_pgvector_baseline.py`, `/backend/services/api/**`, `/backend/tests/**`, `/web/features/dashboard/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: memory backend contract tests, world API memory tests, schema metadata tests, Web client/component/E2E coverage
- Docs updated: README, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: provider profiles, runtime agent loop, narrative artifacts, and plugin execution remain separate tasks.

## Agent loop and narrative baseline entry

- Date: 2026-04-17
- Branch: feat/agent-loop-narrative-baseline
- Scope: provider profiles, runtime daemon control, agent loop execution, and narrative artifacts
- Summary: Added non-secret provider profiles, database-backed runtime control, a daemon-aware agent loop, manual agent-run and narrative APIs, and Web dashboard panels for runtime/provider/run/artifact operations.
- Files changed: `/backend/packages/adapters/**`, `/backend/packages/agents/src/noveland/agents/models.py`, `/backend/packages/core/**`, `/backend/packages/narrative/**`, `/backend/services/api/**`, `/backend/services/runtime/**`, `/backend/migrations/versions/20260417_0007_agent_narrative_runtime_baseline.py`, `/backend/tests/**`, `/web/app/**`, `/web/features/dashboard/**`, `/web/lib/runtime/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/.env.example`, `/README.md`, `/docs/agent/**`
- Tests added/updated: provider adapter contract tests; runtime daemon iteration test; world API tests for agent runs and narrative artifacts; schema/import coverage for runtime/provider/narrative modules; Web client/component/E2E coverage for runtime controls, provider profiles, agent runs, and narrative artifacts
- Docs updated: README, configuration/secrets, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: production process supervision, richer prompt/runtime policy, provider retry/rate-limit handling, plugin execution, and advanced narrative reader flows remain separate tasks.

## Runtime observability and diagnostics entry

- Date: 2026-04-17
- Branch: feat/runtime-observability-diagnostics
- Scope: runtime/provider/agent diagnostics baseline
- Summary: Added runtime diagnostic event persistence, redacted diagnostic contracts/services, runtime/provider/agent/event-publisher diagnostic writes, admin diagnostics APIs, and Web dashboard diagnostics panels.
- Files changed: `/backend/packages/observability/**`, `/backend/packages/core/src/noveland/core/database.py`, `/backend/services/api/**`, `/backend/services/runtime/**`, `/backend/migrations/versions/20260417_0008_runtime_diagnostics_baseline.py`, `/backend/tests/**`, `/web/app/api/runtime/diagnostics/**`, `/web/features/dashboard/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: observability service/contract tests; runtime/event-publisher diagnostic tests; API diagnostics permission tests; schema/import coverage; Web client/component/mock-backend diagnostics coverage
- Docs updated: README, data ownership, architecture map, project index, file inventory, task board, active handoff
- Follow-up notes: provider timeout/retry/rate-limit hardening, provider test-call health state, and agent observation/persona policy remain separate tasks.

## Plugin runtime wiring entry

- Date: 2026-04-22
- Branch: feat/plugin-runtime-wiring
- Scope: explicit plugin bindings and runtime wiring
- Summary: Added built-in plugin identifiers and registry-backed implementations for model providers, memory backend, world rules, persona policy, and narrative writer; added explicit DB/plugin bindings plus plugin-aware Web configuration surfaces.
- Files changed: `/backend/packages/plugins/**`, `/backend/packages/adapters/**`, `/backend/packages/agents/**`, `/backend/packages/narrative/**`, `/backend/packages/worlds/**`, `/backend/services/api/**`, `/backend/services/runtime/**`, `/backend/migrations/versions/20260422_0015_plugin_runtime_wiring.py`, `/web/app/api/plugins/catalog/**`, `/web/features/admin/**`, `/web/features/agents/**`, `/web/features/conversations/**`, `/web/features/worlds/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/docs/agent/harness/**`
- Tests added/updated: plugin runtime regression through backend `ruff`, `mypy`, and full `pytest`; frontend `lint`, `typecheck`, `vitest`, `playwright`, and production build coverage updated for plugin-aware loaders and forms
- Docs updated: project index, file inventory, task board, active handoff
- Follow-up notes: plugin execution still uses code-registered built-ins only; marketplace, hot reload, and remote installation remain future work.

## Mem0 OSS-first long-term memory entry

- Date: 2026-04-24
- Branch: feat/memory-mem0-oss-foundation
- Scope: long-term memory refactor
- Summary: Replaced the old synchronous pgvector CRUD memory baseline with a Mem0 OSS-first long-term memory stack, including platform memory backend profiles, async memory write jobs/logs, conversation and runtime memory context integration, read-only web memory surfaces, profile snapshots, forget flows, and eval/health operators.
- Files changed: `/.env.example`, `/README.md`, `/backend/packages/core/src/noveland/core/settings.py`, `/backend/packages/memory/**`, `/backend/packages/plugins/**`, `/backend/packages/worlds/**`, `/backend/packages/conversations/**`, `/backend/services/api/**`, `/backend/services/runtime/**`, `/backend/migrations/versions/20260423_0016_memory_mem0_oss_foundation.py`, `/backend/migrations/versions/20260423_0017_memory_context_integration.py`, `/backend/migrations/versions/20260423_0018_memory_profiles_forget_evals.py`, `/backend/tests/**`, `/web/app/admin/memory-backends/**`, `/web/app/api/memory-backend-profiles/**`, `/web/features/admin/memory-backend-admin.tsx`, `/web/features/agents/agent-builder.tsx`, `/web/features/conversations/conversation-detail.tsx`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/docs/agent/harness/**`
- Tests added/updated: backend memory backend/service/API/runtime/schema/import tests; web type/client/component coverage for read-only memory and admin memory backend flows; Playwright mock backend updated for memory profiles and read-only memory behavior
- Docs updated: README, long-memory architecture, technical stack, configuration/secrets, data ownership, module boundaries, plugin architecture, architecture map, project index, file inventory, task board, active handoff
- Follow-up notes: Mem0 remains behind `MemoryService`; raw event storage still reuses existing world events, conversation turns, and agent runs; distributed job execution and richer profile derivation remain future work.

## Provider reliability hardening entry

- Date: 2026-04-17
- Branch: feat/provider-reliability-hardening
- Scope: provider timeout/retry/rate-limit and health-test baseline
- Summary: Added non-secret provider reliability fields, timeout/retry/error classification behavior, per-process rate limiting, provider test-call API, diagnostic recording, and Web provider panel controls.
- Files changed: `/backend/packages/adapters/**`, `/backend/services/api/src/noveland/services/api/runtime.py`, `/backend/migrations/versions/20260417_0009_provider_reliability.py`, `/backend/tests/**`, `/web/app/api/provider-profiles/[profileId]/test-call/**`, `/web/features/dashboard/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: provider adapter reliability tests, API test-call coverage, schema metadata checks, Web client/component/mock-backend coverage for reliability fields and provider test calls
- Docs updated: README, configuration/secrets, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: provider rate limiting is process-local; distributed rate limiting, richer provider health dashboards, agent observation/persona policy, and plugin runtime execution remain separate tasks.

## Agent observation and persona baseline entry

- Date: 2026-04-17
- Branch: feat/agent-observation-persona
- Scope: agent persona policy, filtered observations, prompt context convergence
- Summary: Added agent persona and filtered observation persistence, typed contracts/services, world-admin persona/observation APIs, runtime prompt enrichment, and Web dashboard persona/observation controls.
- Files changed: `/backend/packages/agents/**`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/services/runtime/src/noveland/services/runtime/agent_loop.py`, `/backend/migrations/versions/20260417_0010_agent_observation_persona.py`, `/backend/tests/**`, `/web/features/dashboard/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: persona/observation service tests, API permission and flow tests, schema/import coverage, runtime daemon prompt-context coverage, Web client/component/E2E coverage for persona and observations
- Docs updated: README, architecture map, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: observations are filtered derived records and do not alter event log semantics; same-scene multi-agent dialogue, public reader UI, plugin runtime execution, and advanced prompt policy remain future work.

## Conversation workspace baseline entry

- Date: 2026-04-19
- Branch: feat/conversation-workspace-baseline
- Scope: multi-agent conversation substrate and world-first Web workspace
- Summary: Added world/scene-scoped conversation sessions, deterministic round-robin participants and transcript turns, conversation API routes, runtime auto-dialogue ticking, explicit agent provider profile mapping, and a multi-page Web workspace for worlds, agents, conversations, narrative, providers, and runtime.
- Files changed: `/backend/packages/conversations/**`, `/backend/migrations/versions/20260419_0011_conversation_workspace_baseline.py`, `/backend/services/api/src/noveland/services/api/conversations.py`, `/backend/services/runtime/src/noveland/services/runtime/conversation_loop.py`, `/backend/tests/**`, `/web/app/worlds/**`, `/web/app/admin/**`, `/web/features/{admin,agents,conversations,workspace,worlds}/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: conversation service/API tests; runtime daemon auto-dialogue test; schema/import coverage; Web auth/E2E updates for multi-page workspace and conversations
- Docs updated: README, architecture map, module boundaries, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: conversation v1 uses deterministic round-robin only; LLM speaker selection, policy guardrails, richer stop conditions, and narrative writer consumption remain future tasks.

## Conversation policies and stop conditions entry

- Date: 2026-04-21
- Branch: feat/conversation-policies-stop-conditions
- Scope: per-session conversation policy, stop/failure guards, and diagnostics visibility
- Summary: Added explicit per-session policy config and terminal reason fields, skip/retry/fail stop-condition handling, conversation diagnostics over the existing observability store, new stop/diagnostics API routes, and Web policy editing plus diagnostic display in the conversation detail view.
- Files changed: `/backend/packages/conversations/**`, `/backend/packages/observability/**`, `/backend/services/api/src/noveland/services/api/conversations.py`, `/backend/services/runtime/src/noveland/services/runtime/conversation_loop.py`, `/backend/migrations/versions/20260421_0012_conversation_policies_stop_conditions.py`, `/backend/tests/**`, `/web/features/{agents,conversations,worlds}/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/docs/agent/**`
- Tests added/updated: conversation service policy coverage, API stop/diagnostics coverage, runtime daemon retry handling, schema metadata assertions, Web conversation detail policy/diagnostics tests, and mock-backend E2E updates for stopped/max-turn sessions
- Docs updated: project index, file inventory, task board, active handoff, change journal
- Follow-up notes: richer distributed conversation diagnostics, memory-aware conversation context, and writer consumption of transcripts remain separate future work.

## Narrative writer and summarizer pipeline entry

- Date: 2026-04-21
- Branch: feat/narrative-writer-summarizer
- Scope: conversation-first narrative generation pipeline
- Summary: Added per-session writer config, conversation-linked narrative artifact storage, manual and auto-on-complete summary/chapter generation, runtime hook-up for completed conversations, new conversation narrative API routes, and Web controls for writer config and generation.
- Files changed: `/backend/packages/conversations/**`, `/backend/packages/narrative/**`, `/backend/services/api/src/noveland/services/api/{conversations,worlds}.py`, `/backend/services/runtime/src/noveland/services/runtime/conversation_loop.py`, `/backend/migrations/versions/20260421_0013_narrative_writer_summarizer.py`, `/backend/tests/**`, `/web/features/conversations/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: narrative writer service tests, conversation API narrative generation/listing tests, runtime auto-generate coverage, schema metadata assertions, world client tests for conversation narrative routes, conversation detail component coverage, and mock-backend E2E narrative generation flow
- Docs updated: README, architecture map, module boundaries, data ownership, project index, file inventory, task board, active handoff, change journal
- Follow-up notes: dedicated reader routes, richer writer prompt controls, artifact publishing workflow, and transcript-to-memory integration remain future tasks.

## Dedicated narrative reader surface entry

- Date: 2026-04-21
- Branch: feat/narrative-reader-surface
- Scope: authenticated world-member narrative reader
- Summary: Added filtered narrative artifact list/detail APIs, a read-only reader surface under `/worlds/{worldId}/reader`, reader navigation, source-conversation linking, and Web test coverage for member access and reader rendering.
- Files changed: `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/test_api_worlds.py`, `/web/app/worlds/[worldId]/reader/**`, `/web/features/worlds/**`, `/web/features/workspace/workspace-shell.tsx`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: narrative artifact API filter/detail coverage for world members; reader component tests; world client tests for filtered narrative list/detail; mock-backend E2E coverage for reader redirects and member-readable narrative pages
- Docs updated: README, project index, file inventory, task board, active handoff, change journal
- Follow-up notes: public sharing, reader search/sorting, reader timeline views, and realtime narrative updates remain future tasks.

## Realtime updates entry

- Date: 2026-04-22
- Branch: feat/realtime-updates
- Scope: hybrid SSE updates and conversation live control
- Summary: Added platform/world/conversation SSE delta routes, conversation live WebSocket control with origin checks, same-origin Next streaming proxies, and local live hydration for runtime, world overview, and conversation detail views.
- Files changed: `/backend/services/api/src/noveland/services/api/realtime.py`, `/backend/services/api/src/noveland/services/api/app.py`, `/backend/tests/test_api_realtime.py`, `/web/app/api/runtime/stream/**`, `/web/app/api/worlds/[worldId]/stream/**`, `/web/app/api/worlds/[worldId]/conversations/[conversationId]/stream/**`, `/web/features/admin/**`, `/web/features/conversations/**`, `/web/features/worlds/**`, `/web/lib/auth/**`, `/web/lib/realtime.ts`, `/web/lib/realtime/**`, `/web/lib/worlds/types.ts`, `/.env.example`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: realtime API/auth/origin tests; streaming proxy tests; runtime admin and conversation detail component coverage for live updates; full backend/web regression suite
- Docs updated: README, project index, file inventory, task board, change journal
- Follow-up notes: Stage 1 adds incremental streaming and live conversation control without replacing existing SSR/REST loaders; world members remain read-only on the live WebSocket channel.

## Agent composition presets entry

- Date: 2026-04-22
- Branch: feat/agent-composition-presets
- Scope: platform-managed presets and world composition import/export
- Summary: Added `agent_presets`, preset-aware agent materialization, world composition export/import routes, preset admin UI, preset-aware agent creation, and composition controls in the world overview.
- Files changed: `/backend/packages/agents/**`, `/backend/services/api/src/noveland/services/api/{app,worlds}.py`, `/backend/migrations/versions/20260422_0014_agent_composition_presets.py`, `/backend/tests/**`, `/web/app/admin/presets/**`, `/web/app/api/agent-presets/**`, `/web/app/api/world-compositions/**`, `/web/features/{admin,agents,worlds}/**`, `/web/lib/{api-proxy.ts,worlds/**}`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: preset API/schema tests; world composition export/import API tests; world client tests for preset/composition routes; component tests for preset admin and agent preset creation flow; Playwright mock-backend coverage for preset management and composition import/export
- Docs updated: README, project index, file inventory, task board, change journal, active handoff
- Follow-up notes: presets are materialized only at agent creation/import time, and world composition import always creates a new world instead of merging into an existing one.

## Runtime memory ops entry

- Date: 2026-05-01
- Branch: feat/runtime-memory-ops
- Scope: memory write job observability and retry operators
- Summary: Added platform-admin memory write job listing/retry APIs, runtime status memory job counts, daemon loop processed-memory-job result reporting, and Web memory backend job/failure controls.
- Files changed: `/backend/packages/memory/**`, `/backend/services/api/src/noveland/services/api/runtime.py`, `/backend/services/runtime/src/noveland/services/runtime/daemon.py`, `/backend/tests/**`, `/web/app/api/memory-backend-profiles/[profileId]/jobs/**`, `/web/app/api/memory-write-jobs/**`, `/web/features/admin/memory-backend-admin.tsx`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: memory service job list/summary/retry tests; runtime API permission/retry/status tests; runtime daemon processed-memory-job assertions; Web client and Playwright mock-backend coverage for memory job listing/retry.
- Docs updated: README, project index, file inventory, task board, active handoff, change journal
- Follow-up notes: Memory jobs still use the v1 database-backed queue; distributed workers, production queue coordination, and richer backfill remain future work.

## Long-term roadmap document entry

- Date: 2026-05-01
- Branch: main
- Scope: docs/agent roadmap planning
- Summary: Added a long-term Noveland roadmap with 50 mainline-sized phases, candidate bundles, and maintenance rules while keeping debug, checks, tests, and docs as phase acceptance criteria instead of separate roadmap stages.
- Files changed: `/docs/agent/harness/roadmap.md`, `/docs/agent/README.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: N/A; documentation-only planning update.
- Docs updated: roadmap, README, project index, file inventory, task board, active handoff, change journal
- Follow-up notes: Select the next implementation mainline from the roadmap when ready; do not treat all 50 phases as active task-board work.

## Runtime/provider/memory ops hardening entry

- Date: 2026-05-02
- Branch: main
- Scope: roadmap phases 1-5 ops hardening
- Summary: Implemented the first roadmap bundle across runtime status health, memory queue reliability metadata, memory backfill dry-run planning, and provider health summaries without adding a new queue or bypassing `MemoryService`.
- Files changed: `/backend/packages/core/src/noveland/core/settings.py`, `/backend/packages/memory/**`, `/backend/packages/adapters/**`, `/backend/services/api/src/noveland/services/api/{runtime,realtime}.py`, `/backend/tests/**`, `/web/app/api/{memory-backfill,provider-profiles}/**`, `/web/features/admin/**`, `/web/lib/worlds/**`, `/web/features/dashboard/world-management-dashboard.test.tsx`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: runtime API/realtime tests for health payloads; memory backend tests for retryable, terminal, stalled, and dry-run behavior; provider/admin Web tests; world client tests; mock backend coverage for new admin routes.
- Docs updated: README, task board, change journal, active handoff.
- Follow-up notes: Memory backfill remains planning-only; processing still uses the v1 database-backed queue. Next likely roadmap candidate is provider secret validation and recovery playbooks.

## Provider secrets and runtime recovery entry

- Date: 2026-05-02
- Branch: main
- Scope: provider secret-ref validation and runtime recovery playbook
- Summary: Added explicit provider health secret-ref metadata, preserved compatibility for `missing_secret_ref`, updated the provider admin surface, and added a local runtime recovery playbook for runtime, provider, memory queue, event audit, and snapshot checks.
- Files changed: `/backend/packages/adapters/**`, `/backend/services/api/src/noveland/services/api/runtime.py`, `/backend/tests/test_api_runtime.py`, `/web/features/admin/provider-admin.tsx`, `/web/features/admin/provider-admin.test.tsx`, `/web/lib/worlds/types.ts`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/README.md`, `/docs/agent/README.md`, `/docs/agent/git/workflow.md`, `/docs/agent/operations/runtime-recovery.md`, `/docs/agent/harness/**`
- Tests added/updated: provider health API coverage for configured, missing, and empty secret refs; provider admin rendering coverage for secret-ref status; Web client coverage remains aligned with provider health route mapping.
- Docs updated: README, runtime recovery playbook, project index, file inventory, task board, change journal, active handoff, and git workflow branch naming rule.
- Follow-up notes: Future branches must be named by feature/outcome rather than roadmap phase numbers. Next planned mainline is `Event/Replay/Clock Ops` on `feat/event-replay-clock-ops`, covering roadmap phases 8-12.

## Event/replay/clock ops entry

- Date: 2026-05-02
- Branch: feat/event-replay-clock-ops
- Scope: roadmap phases 8-12 event audit, snapshot integrity, replay workspace, clock ops visibility, and schedule preview
- Summary: Added a world-admin event audit API and Web panel; derived snapshot integrity reporting; a richer replay/snapshot workspace that separates live clock state from reconstructed replay state; clock transition audit visibility; and dry-run schedule rule preview without persisting rules or runtime work.
- Files changed: `/backend/packages/events/**`, `/backend/packages/calendar/**`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/**`, `/web/features/worlds/**`, `/web/features/dashboard/world-management-dashboard.test.tsx`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: event audit API filtering/permission tests; snapshot integrity service/API tests; clock transition API tests; schedule preview service/API tests; world overview component coverage; Web client route mapping; full mock-backend alignment.
- Docs updated: README endpoint list, project index, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Snapshot integrity is read-only and does not restore data. Schedule preview is dry-run only. Next likely mainline is `Agent/Conversation Diagnostics Ops` covering roadmap phases 13-17.

## Calendar/agent diagnostics ops entry

- Date: 2026-05-03
- Branch: feat/calendar-agent-diagnostics-ops
- Scope: roadmap phases 13-17 calendar conflicts, agent run inspection, persona policy validation, observation traceability, and conversation diagnostics
- Summary: Added read-only calendar conflict detection, world-admin agent run inspection, reusable persona policy validation, persisted observation traceability fields, and conversation diagnostics summaries.
- Files changed: `/backend/packages/{agents,calendar}/**`, `/backend/services/api/src/noveland/services/api/{worlds,conversations}.py`, `/backend/services/runtime/src/noveland/services/runtime/agent_loop.py`, `/backend/migrations/versions/20260503_0019_observation_traceability.py`, `/backend/tests/**`, `/web/features/{agents,conversations,dashboard,worlds}/**`, `/web/lib/worlds/**`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: calendar conflict service/API tests; agent run detail API and Web client tests; persona validation API/Web client coverage; observation schema/runtime/API tests; conversation diagnostics summary API/component/client coverage.
- Docs updated: README endpoint list, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Calendar conflict detection is read-only and hourly-sampled. Observation traceability requires applying migration `20260503_0019`. Next roadmap mainline is not selected yet.

## Conversation/narrative quality ops entry

- Date: 2026-05-04
- Branch: feat/conversation-narrative-quality-ops
- Scope: roadmap phases 18-22 conversation policy, memory controls, narrative prompt controls, and publishing workflow
- Summary: Added deterministic hybrid speaker policy preview, stronger conversation guardrails, operator-visible conversation memory controls, narrative writer prompt controls with dry-run preview, and a publication-backed narrative publishing workflow. Also closed stale gate docs, replaced deprecated FastAPI 422 constants, and added `next-env.d.ts` build-churn checking.
- Files changed: `/backend/packages/conversations/**`, `/backend/packages/narrative/**`, `/backend/services/api/src/noveland/services/api/{conversations,worlds}.py`, `/backend/migrations/versions/20260504_0020_narrative_publications.py`, `/backend/tests/**`, `/web/features/{conversations,worlds,dashboard}/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: conversation service/API tests for speaker policy, guardrails, memory controls, and prompt preview; narrative writer and publication API tests; schema metadata coverage for `narrative_publications`; Web component/client tests for conversation controls, prompt preview, narrative workspace publication controls, and reader visibility.
- Docs updated: README endpoint list, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Narrative publishing uses a separate `narrative_publications` table. Reader surfaces expose only published, reader-visible artifacts to non-editors; draft artifacts remain admin-visible. Apply migration `20260504_0020` before using the publishing workflow on persistent databases.

## Narrative reader/composition ops entry

- Date: 2026-05-04
- Branch: feat/narrative-reader-composition-ops
- Scope: roadmap phases 23-27 narrative reader search/timeline/realtime, world composition validation, and preset versioning
- Summary: Added publication-aware narrative reader search and timeline controls, realtime narrative artifact updates through the existing world stream, platform-admin composition import dry-run validation, richer composition export metadata, and explicit preset version provenance for materialized agents.
- Files changed: `/backend/packages/agents/**`, `/backend/services/api/src/noveland/services/api/{realtime,worlds}.py`, `/backend/migrations/versions/20260504_0021_agent_preset_versioning.py`, `/backend/tests/**`, `/web/app/api/world-compositions/validate/**`, `/web/features/{admin,agents,conversations,dashboard,worlds}/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: narrative API and Web tests for search/timeline; realtime API and reader/workspace tests for publication metadata; composition validation API/client/component/mock-backend tests; preset versioning API/schema/UI tests.
- Docs updated: README endpoint list, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Push of `main` remains blocked by missing GitHub HTTPS credentials in this environment. Apply migration `20260504_0021` before using preset version provenance on persistent databases.

## Plugin/preset evolution ops entry

- Date: 2026-05-04
- Branch: feat/plugin-preset-evolution-ops
- Scope: roadmap phases 28-32 preset update strategy, plugin binding persistence, plugin contract harness, plugin config UI schema, and plugin runtime diagnostics
- Summary: Added platform-admin preset update preview, derived plugin binding validation across existing persisted binding fields, built-in plugin contract harness coverage, schema-driven provider plugin config controls with JSON fallback, and plugin runtime diagnostics backed by a new diagnostic component.
- Files changed: `/backend/packages/observability/**`, `/backend/services/api/src/noveland/services/api/runtime.py`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/migrations/versions/20260504_0022_plugin_diagnostic_component.py`, `/backend/tests/**`, `/web/app/api/{agent-presets,plugins}/**`, `/web/features/{admin,plugins}/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: preset update preview API/UI/client tests; plugin binding API permission/validation tests; built-in plugin contract harness; provider plugin diagnostic API tests; provider admin schema/diagnostic rendering tests; mock backend routes for preset preview and plugin bindings.
- Docs updated: README endpoint list, project index, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Plugin bindings continue to use existing persisted fields rather than a new plugin layer. Persistent databases need migration `20260504_0022` before writing plugin diagnostics.

## Tool policy / scale / v2 readiness entry

- Date: 2026-05-05
- Branch: feat/tool-policy-scale-v2-readiness
- Scope: roadmap phases 48-50 external tool policy, scale readiness, and v2 expansion review
- Summary: Added policy-only external tool reporting, a derived platform-admin scale-readiness report, runtime admin visibility for both reports, and an evidence-based v2 readiness review that closes the current 50-phase roadmap without selecting a binding v2 direction.
- Files changed: `/backend/services/api/src/noveland/services/api/runtime.py`, `/backend/tests/test_api_runtime.py`, `/web/app/api/runtime/{tool-policy,scale-readiness}/**`, `/web/features/admin/runtime-admin.tsx`, `/web/lib/worlds/**`, `/README.md`, `/docs/agent/operations/{external-tool-policy,scale-readiness}.md`, `/docs/agent/harness/**`
- Tests added/updated: runtime API tests for tool policy permissions and scale readiness sections/blockers; runtime admin component and world client tests for policy/readiness rendering and routes.
- Docs updated: README, project index, file inventory, task board, change journal, active handoff, and v2 readiness review.
- Follow-up notes: External tool execution remains disabled. Scale readiness is a derived operator report, not a load test. The 50-phase roadmap is complete; next work should start from the v2 readiness review and real operator feedback.

## V2 living world roadmap entry

- Date: 2026-05-05
- Branch: docs/v2-living-world-roadmap
- Scope: long-term roadmap planning for the galgame sequel-style living world direction
- Summary: Added a new 50-phase V2 roadmap focused on world bible, canon continuity, relationships, organizations/factions, GM world engine, offscreen events, player choice consequences, branchable worldlines, route systems, information flow, and living-world beta validation.
- Files changed: `/docs/agent/harness/roadmap-v2-living-world.md`, `/docs/agent/README.md`, `/docs/agent/harness/{project-index,file-inventory,task-board,change-journal,handoffs/active-session}.md`
- Tests added/updated: N/A; documentation-only planning update.
- Docs updated: agent README read order, project index, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Do not treat all 50 V2 phases as active tasks. Select one V2 mainline bundle in `task-board.md` only when implementation starts.
