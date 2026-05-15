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

## v0.5 Authoring & Import Studio archive entry

- Date: 2026-05-15
- Branch: main
- Scope: OpenSpec archive, v0.5 current specs, release notes, and harness bookkeeping
- Summary: Archived the completed v0.5 Authoring & Import Studio OpenSpec change, synced implemented authoring/import capabilities into current OpenSpec specs, and added v0.5 release notes.
- Files changed: `/openspec/specs/**`, `/openspec/changes/archive/2026-05-15-v0-5-authoring-import-studio/**`, `/docs/agent/harness/**`
- Tests added/updated: N/A
- Docs updated: OpenSpec current specs, OpenSpec archive, v0.5 release notes, project index, file inventory, task board, active handoff
- Follow-up notes: Start v0.6 with feasibility review only; do not implement v0.6 until architecture scope is accepted.

## v0.6 Runtime Narrative Quality feasibility review entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.6 OpenSpec feasibility review
- Summary: Reviewed the proposed v0.6 Runtime Narrative Quality change against current main and identified required OpenSpec revisions before implementation.
- Files changed: `/docs/agent/harness/feature-updates/v0.6-runtime-narrative-quality-feasibility-review.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A
- Docs updated: v0.6 feasibility review, project index, change journal, task board, active handoff
- Follow-up notes: Update v0.6 OpenSpec before implementation; provider text execution alignment and narrative artifact worldline strategy are the main pre-implementation decisions.

## v0.6.1 Runtime Context Contract v2 planning entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.6 Runtime Narrative Quality Phase 1 planning
- Summary: Added the Phase 1 implementation checkpoint for runtime context contracts and the dedicated narrative quality package/router boundary.
- Files changed: `/docs/agent/harness/feature-updates/v0.6.1-runtime-context-contract-v2-plan.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A
- Docs updated: project index, file inventory, change journal, active handoff
- Follow-up notes: Implement Phase 1 on `feat/runtime-context-contract-v2`; do not add Web UI or broad `worlds.py` routes.

## v0.6.5 Narrative Writer v2 planning entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.6 Runtime Narrative Quality Phase 5 planning
- Summary: Added the Phase 5 implementation checkpoint for Narrative Writer v2, including first-class narrative artifact/publication worldline strategy and provider-kernel text generation boundaries.
- Files changed: `/docs/agent/harness/feature-updates/v0.6.5-narrative-writer-v2-plan.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A
- Docs updated: project index, file inventory, change journal, task board, active handoff
- Follow-up notes: Implement Phase 5 on `feat/narrative-writer-v2`; do not add Web UI, broad `worlds.py` routes, legacy provider profile expansion, automatic publication, or world event writes.

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

## Living world character foundation entry

- Date: 2026-05-05
- Branch: feat/living-world-character-foundation
- Scope: V2 living-world roadmap phases 1-5 story world bible, canon continuity, character roster metadata, character profile sheets, and relationship graph v1.
- Summary: Added a world-scoped bible with continuity configuration, continuity metadata on event/narrative API responses, structured galgame character roster/profile fields on agents, and a world-scoped directed relationship edge table/API. Web world overview now exposes world bible editing, agent creation/builder flows expose structured character fields, and agent detail shows relationship graph create/update controls.
- Files changed: `/backend/migrations/versions/20260505_0023_living_world_character_foundation.py`, `/backend/packages/{agents,worlds}/src/noveland/*/models.py`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/{test_api_worlds,test_schema_metadata,test_alembic_config}.py`, `/backend/migrations/README.md`, `/web/features/{agents,worlds,workspace}/**`, `/web/lib/worlds/**`, `/docs/agent/harness/**`
- Tests added/updated: world bible API/access tests; continuity metadata API tests; agent metadata compatibility tests; relationship graph same-world/self-edge/update tests; schema metadata/alembic head tests; Web client route tests; agent list/builder/world overview component tests.
- Docs updated: task board, change journal, active handoff.
- Follow-up notes: Apply migration `20260505_0023` before using V2 character foundation on persistent databases. Relationship memory integration, organizations/factions, location graph, GM engine, worldlines, and player choices remain future V2 phases.

## Living world autonomous systems entry

- Date: 2026-05-05
- Branch: feat/living-world-autonomous-systems
- Scope: V2 living-world roadmap phases 6-15 relationship memory integration, organizations, memberships, faction progress, location graph, character presence, daily life scheduler, offscreen queue, event importance, and deterministic GM world engine v1.
- Summary: Added relationship-change memory write integration through `MemoryService`; organization, membership, faction track, location edge, presence, daily-life candidate, and offscreen queue persistence/API surfaces; world-event importance metadata and filters; deterministic GM runtime resolution for due offscreen events; and dense Web/admin panels plus Playwright mock routes for the new living-world autonomy surfaces.
- Files changed: `/backend/migrations/versions/20260505_0024_living_world_autonomous_systems.py`, `/backend/packages/{events,memory,worlds}/src/noveland/**`, `/backend/services/{api,runtime}/src/noveland/services/**`, `/backend/tests/{test_api_worlds,test_memory_backend,test_runtime_daemon,test_schema_metadata,test_alembic_config}.py`, `/backend/migrations/README.md`, `/web/features/{agents,dashboard,worlds}/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/docs/agent/harness/**`
- Tests added/updated: relationship memory write-job coverage; organization/membership/faction/presence/daily/offscreen/world-event importance API tests; deterministic GM runtime daemon tests; schema metadata/alembic coverage for `20260505_0024`; Web client/component tests; e2e mock backend coverage for new world APIs.
- Docs updated: migration README, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Apply migration `20260505_0024` before using autonomous living-world data on persistent databases. GM v1 is deterministic and does not call providers, external tools, or direct memory backend SDKs. V2 phases 16-20 remain the next candidate bundle.

## Living world GM choices worldlines entry

- Date: 2026-05-06
- Branch: feat/living-world-gm-choices-worldlines
- Scope: V2 living-world roadmap phases 16-25 GM agenda, event proposals, deterministic resolution rules, player actor/choices/consequences, branchable worldlines, snapshot fork, worldline memory isolation, and timeline comparison.
- Summary: Added primary/forked worldlines with compatibility defaults; scoped events, snapshots, replay, memory, relationships, faction tracks, presence, daily candidates, and offscreen queue by worldline; added GM agendas, event proposals, resolution-rule dry-runs, player actor profiles, choice records, consequence preview/apply, worldline fork copying, and timeline comparison; exposed dense Web/admin controls and Playwright mock routes for the new surfaces.
- Files changed: `/backend/migrations/versions/20260505_0025_living_world_gm_choices_worldlines.py`, `/backend/packages/{events,memory,worlds}/src/noveland/**`, `/backend/services/{api,runtime}/src/noveland/services/**`, `/backend/tests/**`, `/web/features/worlds/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: worldline API/fork/compare tests; GM agenda/proposal/review/rule dry-run tests; player actor/choice/consequence tests; replay/snapshot/event/memory worldline-scope tests; schema metadata/Alembic coverage for `20260505_0025`; Web client/component tests; full Playwright mock alignment for new worldline and GM routes.
- Docs updated: README endpoint list, migration README, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Apply migration `20260505_0025` before using worldline-scoped living-world data on persistent databases. GM work remains deterministic and does not call providers, external tools, subprocesses, or direct memory backend SDKs. V2 phases 26-35 are the next likely mainline bundle.

## Living world plot route rumor flow entry

- Date: 2026-05-06
- Branch: feat/living-world-plot-route-rumor-flow
- Scope: V2 living-world roadmap phases 26-35 promise/foreshadowing tracking, plot threads, route affinity, event flags, scene beats, daily episodes, group interactions, relationship suggestions, organization conflict, and rumor/information flow v1.
- Summary: Added worldline-scoped plot/route/rumor persistence and services; deterministic trigger dry-runs, scene beat and daily episode draft generation, relationship suggestion generation, organization conflict resolution, and rumor delivery; world-admin API surfaces; and dense Web/admin controls plus Playwright mock alignment.
- Files changed: `/backend/migrations/versions/20260506_0026_living_world_plot_route_rumor_flow.py`, `/backend/packages/{agents,worlds}/src/noveland/**`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/{test_api_worlds,test_schema_metadata,test_alembic_config}.py`, `/backend/migrations/README.md`, `/web/features/worlds/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/docs/agent/harness/**`
- Tests added/updated: world-admin API coverage for plot/route/rumor flows, worldline scoping, trigger dry-run, deterministic drafts, relationship suggestions, organization conflict event emission, rumor delivery, schema metadata, Alembic head, Web client routes, world overview rendering, and e2e mock backend route alignment.
- Docs updated: migration README, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Apply migration `20260506_0026` before using plot/route/rumor data on persistent databases. Rumor flow is v1 propagation/visibility only; character knowledge state, secrets, emotional state, relationship decay/repair, player journal, notifications, intervention controls, and GM style/continuity review remain later V2 phases.

## Living world knowledge player guardrails entry

- Date: 2026-05-07
- Branch: feat/living-world-knowledge-player-guardrails
- Scope: V2 living-world roadmap phases 36-45 character knowledge state, secrets/revelations, emotional state, relationship decay/repair, world-state dashboard v2, player-facing journal, in-world notifications, intervention controls, GM style guardrails, and narrative continuity review.
- Summary: Added worldline-scoped knowledge facts, secrets/reveals, emotional states, relationship repair records, player journal entries, notifications, interventions, GM style diagnostics, and narrative continuity reviews. Closed natural V2 phases 1-35 acceptance gaps by logging `apply=false` choices as events, propagating runtime memory worldline scope, rejecting unsupported historical worldline forks, expanding deterministic dry-run context, turning rumor delivery into knowledge state, generating daily episode drafts from resolved low-risk offscreen events, and passing group interaction context into conversation writer config.
- Files changed: `/backend/migrations/versions/20260507_0027_living_world_knowledge_player_guardrails.py`, `/backend/packages/{memory,worlds}/src/noveland/**`, `/backend/services/{api,runtime}/src/noveland/services/**`, `/backend/tests/{test_api_worlds,test_schema_metadata,test_alembic_config}.py`, `/backend/migrations/README.md`, `/web/features/worlds/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/docs/agent/harness/**`
- Tests added/updated: backend API/schema/Alembic coverage for knowledge, secrets, emotional state, relationship repair, journal, notification, intervention, style review, continuity review, dashboard, daily episode generation, memory write jobs, and fork rejection; Web client route tests; world overview rendering tests; Playwright mock backend alignment.
- Docs updated: migration README, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Apply migration `20260507_0027` before using knowledge/player/guardrail state on persistent databases. Review work is deterministic diagnostics only; it does not hard-block publication by default and does not call providers, external tools, subprocesses, or sandbox execution. V2 phases 46-50 remain as the next candidate bundle.

## Living world beta release readiness entry

- Date: 2026-05-07
- Branch: feat/living-world-beta-release-readiness
- Scope: V2 living-world roadmap phases 46-50 route/ending planning, long-run simulation evaluation, authoring toolchain v2, living-world release profile, and galgame living-world beta validation.
- Summary: Added worldline-scoped route milestones and ending candidates, deterministic ending dry-runs, long-run evaluation runs with recommendations/blockers, sequel-world authoring templates with preview/apply import jobs, release profile records, and beta checklist runs/items for sample-world readiness evidence. Web world overview now exposes dense beta-readiness panels, and the Playwright mock backend covers all new routes.
- Files changed: `/backend/migrations/versions/20260507_0028_living_world_beta_release_readiness.py`, `/backend/packages/worlds/src/noveland/worlds/{models,beta}.py`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/{test_api_worlds,test_schema_metadata,test_alembic_config}.py`, `/backend/migrations/README.md`, `/web/features/worlds/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/docs/agent/operations/living-world-release-profile.md`, `/docs/agent/harness/**`
- Tests added/updated: backend API/schema/Alembic coverage for route milestones, endings, long-run evals, authoring templates/imports, release profiles, and beta checklist evidence; Web client route mapping and world overview rendering tests; Playwright mock backend alignment.
- Docs updated: migration README, release profile operator note, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Apply migration `20260507_0028` before using beta readiness state on persistent databases. Long-run eval and beta validation are deterministic local evidence capture, not provider generation, external tool execution, or a public production launch.

## V2 runtime worldline memory isolation remediation entry

- Date: 2026-05-08
- Branch: fix/v2-runtime-worldline-memory-isolation
- Scope: V2 acceptance remediation bundle 1 for runtime run worldline scope, conversation session propagation, memory profile snapshots, memory backfill, memory forget/delete, fake/local memory backend filtering, and player-choice audit semantics.
- Summary: Added first-class `worldline_id` to runtime runs, conversation sessions, and agent profile snapshots; resolved omitted worldlines to each world's primary worldline for compatibility; propagated conversation worldline scope into runtime agent turns; scoped memory context, profile snapshots, delete/forget scrubbing, fake backend storage, retrieval logs, write jobs, and backfill candidates by worldline; exposed worldline metadata on runtime and memory ops API responses; and preserved legacy NULL rows as primary-worldline data.
- Files changed: `/backend/migrations/versions/20260507_0029_runtime_worldline_memory_isolation.py`, `/backend/packages/{agents,conversations,memory}/src/noveland/**`, `/backend/services/{api,runtime}/src/noveland/services/**`, `/backend/tests/{test_alembic_config,test_api_conversations,test_api_worlds,test_conversation_services,test_memory_backend,test_runtime_daemon,test_schema_metadata}.py`, `/backend/migrations/README.md`, `/web/features/admin/memory-backend-admin.test.tsx`, `/web/lib/worlds/types.ts`, `/docs/agent/harness/**`
- Tests added/updated: backend coverage for fork-scoped runtime run events and memory jobs, cross-world worldline rejection, conversation session/event worldline propagation, API run filtering by worldline, fake/local memory worldline isolation, memory build/delete scope isolation, backfill worldline preservation, legacy primary NULL compatibility, schema metadata, and Alembic head. Web memory-admin fixture updated for worldline-aware write jobs.
- Docs updated: migration README, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Apply migration `20260507_0029` before relying on runtime run, conversation session, or profile snapshot worldline scope in persistent databases. Remaining remediation bundles should proceed in order: prompt leak/publish guardrails, runtime GM/narrative execution depth, then beta acceptance gate hardening.

## V2 prompt leak publish guardrails remediation entry

- Date: 2026-05-08
- Branch: feat/v2-prompt-leak-publish-guardrails
- Scope: V2 acceptance remediation bundle 2 for leak-safe prompt context selection, speaker-scoped conversation prompts, narrative prompt/review boundaries, and publish-time blocker handling.
- Summary: Added a shared living-world context selector that admits only public facts, agent-visible knowledge, holder/revealed secrets, bounded emotional state, and relationship summaries into prompts; integrated it into agent runtime, conversation speaker prompts, and narrative writer generation/preview; expanded continuity review to detect hidden secret leaks without persisting secret text in diagnostics; and added a publish gate that blocks failed/leaky narrative artifacts while recording review metadata on successful publication.
- Files changed: `/backend/packages/worlds/src/noveland/worlds/living_context.py`, `/backend/packages/{conversations,narrative,worlds}/src/noveland/**`, `/backend/services/{api,runtime}/src/noveland/services/**`, `/backend/tests/{test_api_worlds,test_conversation_services,test_narrative_writer,test_runtime_daemon}.py`, `/web/features/{workspace,worlds}/**`, `/web/lib/worlds/**`, `/docs/agent/harness/**`
- Tests added/updated: backend coverage for runtime holder/non-holder secret filtering, conversation speaker-specific context filtering, narrative writer leak-safe prompts, publish blocker 422 behavior, and warning-override publication gate metadata; Web client/workspace coverage for structured blocker summaries and publication gate display.
- Docs updated: task board, change journal, and active handoff.
- Follow-up notes: Bundle 3 should build on this selector for world bible/open-hook context packs, group interaction execution, expanded trigger evaluation, and deterministic GM proposal planning.

## V2 runtime GM narrative execution remediation entry

- Date: 2026-05-08
- Branch: feat/v2-runtime-gm-narrative-execution
- Scope: V2 acceptance remediation bundle 3 for living-world runtime/narrative consumption depth, group interaction execution, expanded condition evaluation, and deterministic GM macro planning.
- Summary: Added a shared world condition evaluator for GM rules and event triggers; added living-world context packs that carry bounded world bible constraints, forbidden changes, open hooks, plot threads, route states, and continuity warnings into runtime/narrative prompts and metadata; added deterministic GM macro planning/execution and low-risk GM proposal draft conversion; and added group interaction execution into conversation sessions with participant roles, organization refs, scene constraints, and writer group context metadata.
- Files changed: `/backend/packages/worlds/src/noveland/worlds/{conditions,living_context,gm,plot,autonomous}.py`, `/backend/packages/narrative/src/noveland/narrative/**`, `/backend/services/{api,runtime}/src/noveland/services/**`, `/backend/tests/{test_api_worlds,test_api_conversations,test_narrative_writer,test_runtime_daemon}.py`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/docs/agent/harness/**`
- Tests added/updated: backend coverage for context-pack narrative metadata, group interaction execution, centralized trigger/rule condition evaluation, GM macro planning/execution, and low-risk daily draft conversion; Web client route mapping tests; Playwright mock backend route alignment for macro planning, draft conversion, and group execution.
- Docs updated: task board, change journal, file inventory, and active handoff.
- Follow-up notes: Bundle 4 should harden beta acceptance gates using the now-reliable worldline scope, leak-safe prompt/review boundary, and richer GM/narrative execution evidence. GM macro planning remains deterministic and does not call providers, external tools, subprocesses, or sandbox execution.

## V2 beta acceptance gating hardening remediation entry

- Date: 2026-05-08
- Branch: feat/v2-beta-acceptance-gating-hardening
- Scope: V2 acceptance remediation bundle 4 for beta readiness gate hardening, evidence metrics, checklist evidence refs, route/ending validation, and authoring import audit semantics.
- Summary: Hardened release profiles so `ready` requires latest passing checklist, latest completed long-run eval, resolvable structured evidence refs for snapshot/worldline/publication/continuity review/checklist/eval, and explicit warning decisions; kept `released` blocked behind a future launch gate. Expanded long-run eval metrics with distribution, traceability, snapshot/event refs, proposal/review counts, and warning counts. Added checklist item/run evidence refs, ending requirement validation, forbidden flag dry-runs, authoring target worldline/duplicate policy support, preview diff/audit metadata, applied refs, and authoring audit world events. Updated Web beta panels, route-mapping tests, overview tests, and Playwright mock backend evidence shapes.
- Files changed: `/backend/packages/worlds/src/noveland/worlds/beta.py`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/test_api_worlds.py`, `/web/features/worlds/world-overview.tsx`, `/web/features/worlds/world-overview.test.tsx`, `/web/lib/worlds/types.ts`, `/web/lib/worlds/client.test.ts`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/docs/agent/harness/{task-board.md,change-journal.md,handoffs/active-session.md}`
- Tests added/updated: backend API coverage for blocked/allowed release profile gates, long-run eval evidence metrics, structured checklist refs, invalid/cross-worldline ending requirements, and authoring preview/apply audit refs; Web client body mapping tests; Web overview rendering tests for gate/evidence/audit summaries; Playwright mock backend alignment.
- Docs updated: task board, change journal, and active handoff. No new structural files were introduced, so `file-inventory.md` did not need a path update.
- Follow-up notes: This closes the planned four-bundle V2 acceptance remediation sequence locally. Future hardening should be driven by fresh acceptance reports, beta evidence, operator feedback, and production-readiness decisions rather than roadmap phase numbers.

## V2 acceptance contract hardening entry

- Date: 2026-05-09
- Branch: fix/v2-acceptance-contract-hardening
- Scope: Fresh post-remediation acceptance hardening for Web mock/backend contract parity, reader query coverage, beta/release form payload tests, release gate blocker enforcement, and stale handoff cleanup.
- Summary: Refreshed the active handoff after the completed remediation sequence; aligned the Playwright mock backend with real API behavior for narrative publication blockers and release profile gate blockers; expanded narrative artifact listing filters for search, source kind, publication status, published ordering, and limit; added e2e coverage for blocked publication visibility, reader filtering/ordering, and release gate enforcement; and added component coverage for V2 beta, release, route, ending, and worldline form payloads. Confirmed that omitted/null `worldline_id` is an intentional primary-worldline contract, so no selector code change was needed.
- Files changed: `/docs/agent/harness/{task-board.md,change-journal.md,handoffs/active-session.md}`, `/web/features/worlds/world-overview.test.tsx`, `/web/tests/e2e/{auth.spec.ts,start-with-mock-auth.mjs}`
- Tests added/updated: Web world overview form contract tests; Playwright coverage for publication blockers, reader query filters, published ordering, and release gate blockers; mock syntax and diff whitespace checks.
- Docs updated: task board, change journal, and active handoff.
- Follow-up notes: The auth e2e spec now runs serially because the mock backend uses shared mutable in-memory state. Future e2e additions should either keep shared-state tests serial or isolate mock state per test.

## V2 post-remediation source-of-record refresh entry

- Date: 2026-05-10
- Branch: docs/v2-post-remediation-source-of-record
- Scope: Documentation refresh after the follow-up release evidence, beta GM loop, Web mock parity, Mem0 isolation, and release-evidence e2e stabilization commits landed on local `main`.
- Summary: Updated the active handoff and task board so they no longer describe closed post-remediation risks as upcoming work. Added a debug-journal closure report that maps the 2026-05-09 remaining-risk bullets to the follow-up commits that closed them.
- Files changed: `/docs/agent/harness/{task-board.md,debug-journal.md,change-journal.md,handoffs/active-session.md}`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: task board, debug journal, change journal, and active handoff.
- Follow-up notes: Next preparation hardening should focus on Web runtime/SSE mock parity and Playwright mock state isolation before starting the next feature bundle.

## Current system architecture review entry

- Date: 2026-05-10
- Branch: main
- Scope: Architecture review documentation for planning the next framework update with an external architecture reviewer.
- Summary: Added `docs/agent/harness/current-system-architecture-review.md`, a current-state overview covering product direction, source-of-record files, stack, backend/Web architecture, core data model families, V2 living-world capabilities, major runtime flows, Web surfaces, tests, operations, known constraints, and recommended next framework work.
- Files changed: `/docs/agent/harness/current-system-architecture-review.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Use the architecture review together with the V2 roadmap and debug journal when deciding whether the next implementation should prioritize service decomposition, command/event/evidence framework consolidation, provider-backed generation boundaries, or Web surface modularization.

## Media Kernel Phase 1 plan entry

- Date: 2026-05-10
- Branch: main
- Scope: Final feature implementation plan for Media Kernel Phase 1.
- Summary: Added the version-prefixed feature update plan for backend-only Media Kernel Foundation work. The plan fixes the Phase 1 boundaries around narrative artifact context rejection, asset status semantics, generated storage URIs, no provider profile FK on media jobs, no media-created world events, and no public download/file-serving API.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.1-media-kernel-phase-1-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/media-kernel-foundation` after this docs-only work is committed on `main`.

## Media Kernel Foundation implementation entry

- Date: 2026-05-10
- Branch: feat/media-kernel-foundation
- Scope: Backend-only Media Kernel Phase 1 foundation.
- Summary: Added `noveland-media`, worldline-scoped media asset/job/context/input tables, binary local media storage with opaque `media://` URIs, media services, an independent `/worlds/{world_id}/media/*` API router, and backend coverage for schema, storage, service, API, ACL, and worldline isolation. Phase 1 records media jobs only; it does not execute providers, add upload/download routes, add Web UI, or create world events from media operations.
- Files changed: `/backend/packages/media/**`, `/backend/services/api/src/noveland/services/api/{app,media}.py`, `/backend/migrations/versions/20260510_0030_media_kernel_foundation.py`, `/backend/tests/{test_api_media.py,test_media_service.py,test_media_storage.py,test_schema_metadata.py,test_alembic_config.py,test_workspace_imports.py}`, `/backend/{pyproject.toml,uv.lock}`, `/backend/services/api/pyproject.toml`, `/backend/packages/core/src/noveland/core/database.py`, `/backend/migrations/README.md`, `/docs/agent/harness/**`
- Tests added/updated: Media storage tests, MediaService tests, Media API tests, schema metadata registration, Alembic head, workspace import coverage, plus backend lint/type/test gates.
- Docs updated: migration README, project index, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Narrative artifact media contexts remain schema-reserved but rejected by service/API until `narrative_artifacts` gains first-class `worldline_id`. Later media phases should add asset catalog/search, invocation ledger, performance annotation, provider integrations, binary upload/download policy, and Web media surfaces.

## Media Asset Catalog Phase 2 plan entry

- Date: 2026-05-10
- Branch: main
- Scope: Final feature implementation plan for Media Asset Catalog Phase 2.
- Summary: Added the version-prefixed Phase 2 plan for media asset tags, collections, collection items, asset search, and visibility-safe references/lineage enrichment. The plan fixes tag query parsing, `contains_text` bounds, asset/tag/collection visibility rules, member-safe counts, route ordering, and explicit non-goals around providers, upload/download, Web UI, invocation ledger, performance annotations, and pgvector search.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.2-media-asset-catalog-phase-2-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/media-asset-catalog` after this docs-only work is committed on `main`.

## Media Asset Catalog Phase 2 implementation entry

- Date: 2026-05-10
- Branch: feat/media-asset-catalog
- Scope: Backend-only Media Asset Catalog / Tag Index Phase 2.
- Summary: Added worldline-scoped media asset tags, collections, collection items, asset search, and visibility-safe reference/lineage enrichment. Search supports bounded title/description text filtering, repeatable AND tag filters with colon-safe value parsing, context filters, collection filters, and member-safe visibility rules across assets, tags, and collections. Phase 2 does not add providers, upload/download APIs, Web UI, invocation ledger, performance annotations, or pgvector search.
- Files changed: `/backend/packages/media/src/noveland/media/{catalog,contracts,models,__init__}.py`, `/backend/services/api/src/noveland/services/api/media.py`, `/backend/migrations/versions/20260510_0031_media_asset_catalog.py`, `/backend/tests/{test_media_catalog_service.py,test_api_media_catalog.py,test_schema_metadata.py,test_alembic_config.py,test_workspace_imports.py,test_api_media.py,test_media_service.py}`, `/backend/migrations/README.md`, `/docs/agent/harness/**`
- Tests added/updated: Media catalog service tests, Media catalog API tests, schema metadata registration, Alembic head coverage, workspace import coverage, and existing media API/service table setup coverage.
- Docs updated: migration README, project index, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Later media phases should add provider integrations, upload/download policy, invocation ledger, performance annotations, asset embeddings/similarity search, and Web media surfaces in separate feature-named branches.

## Model Invocation Ledger Phase 3 plan entry

- Date: 2026-05-11
- Branch: main
- Scope: Final feature implementation plan for Model Invocation Ledger Phase 3.
- Summary: Added the version-prefixed Phase 3 plan for a new `noveland-invocations` package, worldline-scoped `model_invocations`, prompt templates, prompt snapshots, invocation tags, runtime-run join table, redaction/retention/visibility policy, independent `/worlds/{world_id}/model-invocations` API router, and new-runtime integration. The plan explicitly excludes provider adapter refactors, Web UI, external tracing exporters, pgvector search, legacy backfill, `conversation_turns` schema changes, and raw prompt/output writes to world events.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.3-model-invocation-ledger-phase-3-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/model-invocation-ledger` after this docs-only work is committed on `main`.

## Model Invocation Ledger Phase 3 implementation entry

- Date: 2026-05-11
- Branch: feat/model-invocation-ledger
- Scope: Backend-only Model Invocation Ledger Phase 3.
- Summary: Added `noveland-invocations`, worldline-scoped invocation ledger tables, prompt templates, prompt snapshots, runtime-run join table, invocation tags, bounded search, redaction/retention/visibility controls, an independent `/worlds/{world_id}/model-invocations` API router, and new `AgentRuntimeRun` provider-call recording. Existing runtime runs remain source records for agent execution; canonical raw prompt/output for new calls is stored in invocation/snapshot records, not in `world_events.payload`.
- Files changed: `/backend/packages/invocations/**`, `/backend/services/api/src/noveland/services/api/{app,invocations}.py`, `/backend/services/runtime/src/noveland/services/runtime/agent_loop.py`, `/backend/migrations/versions/20260511_0032_model_invocation_ledger.py`, `/backend/tests/{test_invocation_ledger_service.py,test_api_invocations.py,test_runtime_daemon.py,test_api_conversations.py,test_api_worlds.py,test_schema_metadata.py,test_alembic_config.py,test_workspace_imports.py}`, `/backend/{pyproject.toml,uv.lock}`, `/backend/services/{api,runtime}/pyproject.toml`, `/backend/packages/core/src/noveland/core/database.py`, `/backend/migrations/README.md`, `/docs/agent/harness/**`
- Tests added/updated: Invocation ledger service tests, invocation API tests, runtime ledger integration assertions, schema metadata registration, Alembic head coverage, workspace import coverage, and legacy API fixture table coverage for runtime/conversation paths.
- Docs updated: migration README, project index, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Provider adapter refactors, external tracing exporters, Web invocation browser, pgvector/similarity search, retention purge jobs, historical `AgentRuntimeRun` backfill, and provider-integration-specific invocation enrichment remain deferred.

## Media Kernel Phase 4 plan entry

- Date: 2026-05-11
- Branch: main
- Scope: Final feature implementation plan for Media Kernel Phase 4 additive extension.
- Summary: Added the version-prefixed Phase 4 plan to extend the existing Media Phase 1/2 foundation with media objects, generic media references, upload/download routes, richer media job updates, and Phase 3 invocation links without replacing existing media tables or APIs.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.4-media-kernel-phase-4-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/media-kernel` after this docs-only work is committed on `main`.

## Media Kernel Phase 4 implementation entry

- Date: 2026-05-11
- Branch: feat/media-kernel
- Scope: Backend-only Media Kernel Phase 4 additive extension.
- Summary: Extended the existing `noveland-media` foundation with multi-object asset records, generic media references, upload/download support, richer media job list/update/cancel flows, turn media attachment routes backed by `media_references`, and media-side Phase 3 invocation links. The implementation preserves existing media tables and route behavior, keeps storage URIs and bytes out of world events, and does not add provider adapters, Web UI, public reader routes, or background media job execution.
- Files changed: `/backend/packages/media/src/noveland/media/{contracts,models,service,storage,__init__}.py`, `/backend/services/api/src/noveland/services/api/{app,media}.py`, `/backend/migrations/versions/20260512_0033_media_kernel.py`, `/backend/tests/{test_media_service.py,test_api_media.py,test_schema_metadata.py,test_alembic_config.py}`, `/backend/{pyproject.toml,uv.lock}`, `/backend/services/api/pyproject.toml`, `/backend/migrations/README.md`, `/docs/agent/harness/**`
- Tests added/updated: Media service coverage for upload/object variants/references/turn media/job updates/source invocation and memory job validation; Media API coverage for upload/download ACL, generic refs, turn media, job patch/cancel, malformed upload metadata, and cross-worldline rejection; schema metadata and Alembic head coverage.
- Docs updated: migration README, file inventory, change journal, and active handoff.
- Follow-up notes: Provider-specific image/audio/video adapters, public reader media serving, S3/GCS storage, media embeddings/search, Web media management UI, and background media job execution remain deferred.

## Provider Execution Kernel Phase 5 plan entry

- Date: 2026-05-11
- Branch: main
- Scope: Final feature implementation plan for Provider Execution Kernel Phase 5.
- Summary: Added the version-prefixed Phase 5 plan for a new `noveland-providers` package, provider integration/capability/health tables, explicit `adapter_kind` execution dispatch, fake provider execution, model invocation ledger writes, media job/asset linkage, and an independent `/worlds/{world_id}/providers` API router.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.5-provider-execution-kernel-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/provider-execution-kernel` after this docs-only work is committed on `main`.

## Provider Execution Kernel Phase 5 implementation entry

- Date: 2026-05-11
- Branch: feat/provider-execution-kernel
- Scope: Backend-only Provider Execution Kernel Phase 5.
- Summary: Added `noveland-providers`, provider integration/capability/health tables, explicit `adapter_kind` routing, world-over-global provider resolution, fake text/image/STT/TTS execution, Phase 3 invocation and prompt snapshot writes, Phase 4 media job/asset/object writes for fake image/audio, and an independent `/worlds/{world_id}/providers` API router. The implementation leaves legacy `provider_profiles` unchanged and does not add real external provider adapters.
- Files changed: `/backend/packages/providers/**`, `/backend/services/api/src/noveland/services/api/{app,providers}.py`, `/backend/migrations/versions/20260512_0034_provider_execution_kernel.py`, `/backend/tests/{test_provider_registry_service.py,test_provider_execution_service.py,test_api_providers.py,test_schema_metadata.py,test_alembic_config.py,test_workspace_imports.py}`, `/backend/{pyproject.toml,uv.lock}`, `/backend/services/api/pyproject.toml`, `/backend/packages/core/src/noveland/core/database.py`, `/backend/migrations/README.md`, `/docs/agent/harness/**`
- Tests added/updated: Provider registry service tests, provider execution service tests, provider API tests, schema metadata registration, Alembic head coverage, workspace import coverage, plus backend lint/type/targeted gates.
- Docs updated: migration README, project index, file inventory, change journal, and active handoff.
- Follow-up notes: Real OpenAI image/speech, OpenAI-compatible image, ComfyUI, MiMo, OmniVoice, GPT-SoVITS, streaming, retry/load balancing, Web provider UI, and provider-profile refactors remain deferred to later phases.

## Image Provider & Visual Asset Pipeline Phase 6 plan entry

- Date: 2026-05-11
- Branch: main
- Scope: Final feature implementation plan for Image Provider & Visual Asset Pipeline Phase 6.
- Summary: Added the version-prefixed Phase 6 plan for image generation/edit/compose routes, media image services, deterministic composition, OpenAI/OpenAI-compatible image adapters, ComfyUI workflow adapter mapping, provider execution integration, and visual asset writeback through Phase 3 and Phase 4 foundations.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.6-image-provider-visual-pipeline-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/image-provider-visual-pipeline` after this docs-only work is committed on `main`.

## Image Provider & Visual Asset Pipeline Phase 6 implementation entry

- Date: 2026-05-11
- Branch: feat/image-provider-visual-pipeline
- Scope: Backend-only Image Provider & Visual Asset Pipeline Phase 6.
- Summary: Added image generation/edit/compose contracts and services, an independent `/worlds/{world_id}/images` router, Pillow-backed deterministic PNG composition, OpenAI/OpenAI-compatible image adapters, a ComfyUI remote workflow adapter with dry-run support, and provider execution dispatch for image adapters. Provider-backed image calls reuse media jobs, write model invocations and prompt snapshots, and store outputs through media assets/objects without writing prompts, bytes, paths, base64, or storage URIs to world events.
- Files changed: `/backend/packages/media/src/noveland/media/{image_contracts,image_service,composer,__init__}.py`, `/backend/packages/providers/src/noveland/providers/{service,fake}.py`, `/backend/packages/providers/src/noveland/providers/adapters/**`, `/backend/services/api/src/noveland/services/api/{app,images}.py`, `/backend/tests/{test_image_service.py,test_api_images.py,test_openai_image_adapter.py,test_comfyui_adapter.py,test_image_composer.py,test_workspace_imports.py}`, `/backend/{pyproject.toml,uv.lock}`, `/backend/packages/{media,providers}/pyproject.toml`, `/docs/agent/harness/**`
- Tests added/updated: Image service/API tests, OpenAI image adapter mocked HTTP tests, ComfyUI adapter mocked/dry-run tests, deterministic composer tests, and workspace import coverage.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: No schema migration was needed for Phase 6. Public reader delivery, Web image management UI, complex image editing, rembg/SAM2/IP-Adapter/ControlNet integrations, predictive background scheduling, and ComfyUI installation/model management remain deferred.

## Speech Provider & Voice Profile Pipeline Phase 7 plan entry

- Date: 2026-05-11
- Branch: main
- Scope: Final feature implementation plan for Speech Provider & Voice Profile Pipeline Phase 7.
- Summary: Added the version-prefixed Phase 7 plan for voice profiles, agent voice bindings, speech transcripts, style mappings, TTS/STT service orchestration, OpenAI speech adapters, MiMo TTS/ASR configurable HTTP contracts, OmniVoice/GPT-SoVITS configurable HTTP contracts, media writeback, invocation ledger integration, and conversation-turn media attachment via references.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.7-speech-provider-voice-profile-pipeline-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/speech-provider-voice-profile-pipeline` after this docs-only work is committed on `main`.

## Speech Provider & Voice Profile Pipeline Phase 7 implementation entry

- Date: 2026-05-12
- Branch: feat/speech-provider-voice-profile-pipeline
- Scope: Backend-only Speech Provider & Voice Profile Pipeline Phase 7.
- Summary: Added `noveland-speech`, voice profile and agent voice binding services, speech transcripts, style mappings, an independent `/worlds/{world_id}/speech` API router, OpenAI speech adapter mapping, configurable MiMo TTS/ASR and OmniVoice/GPT-SoVITS HTTP contract adapters, and provider execution dispatch for speech adapters. TTS/STT flows write model invocations and prompt snapshots, media jobs/assets/objects/references, and transcripts without mutating conversation turn text, auto-enqueueing memory writes, or writing audio bytes, paths, storage URIs, raw prompts, or raw outputs to world events.
- Files changed: `/backend/packages/speech/**`, `/backend/packages/providers/src/noveland/providers/{service,adapters/**}`, `/backend/services/api/src/noveland/services/api/{app,speech}.py`, `/backend/migrations/versions/20260512_0036_speech_voice_pipeline.py`, `/backend/tests/{test_speech_service.py,test_api_speech.py,test_openai_speech_adapter.py,test_mimo_speech_adapters.py,test_voice_profiles.py,test_schema_metadata.py,test_alembic_config.py,test_workspace_imports.py}`, `/backend/{pyproject.toml,uv.lock}`, `/backend/services/api/pyproject.toml`, `/backend/packages/core/src/noveland/core/database.py`, `/backend/migrations/README.md`, `/docs/agent/harness/**`
- Tests added/updated: Voice profile tests, speech service tests, speech API tests, OpenAI speech adapter mocked HTTP tests, MiMo/OmniVoice/GPT-SoVITS adapter contract tests, schema metadata registration, Alembic head coverage, workspace import coverage, plus backend lint/type/full pytest gates.
- Docs updated: migration README, project index, file inventory, change journal, and active handoff.
- Follow-up notes: Streaming speech, real-time calls, local MiMo/OmniVoice/GPT-SoVITS deployment, voice clone training, public reader audio delivery, Web recording/player UI, speaker identity/authentication, and memory auto-write remain deferred.

## Real Provider Configuration & Smoke Validation Phase 8 plan entry

- Date: 2026-05-12
- Branch: main
- Scope: Final feature implementation plan for Real Provider Configuration & Smoke Validation Phase 8.
- Summary: Added the version-prefixed Phase 8 plan for treating provider `auth_ref` as an opaque secret reference, resolving provider secrets from environment/settings at execution time, rejecting secret-like provider config fields, sanitizing provider API/health/ledger payloads, and adding safe provider smoke-test and health-check listing APIs without adding a vault, Web UI, provider marketplace, streaming, fallback routing, or new media product features.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.8-real-provider-smoke-validation-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/real-provider-smoke-validation` after this docs-only work is committed on `main`.

## Real Provider Configuration & Smoke Validation Phase 8 implementation entry

- Date: 2026-05-12
- Branch: feat/real-provider-smoke-validation
- Scope: Backend-only provider secret boundary and smoke validation hardening.
- Summary: Added provider secret reference resolution, recursive sensitive-key rejection for provider config/default params and execution payloads, sanitized provider API/health/ledger responses, health-check history listing, and safe provider smoke-test execution. Real OpenAI/OpenAI-compatible/MiMo/OmniVoice/GPT-SoVITS adapter execution now receives resolved secrets only in memory and treats missing required credentials as safe `auth_missing` failures with failed invocation records. Provider `auth_ref` remains an opaque reference string, restricted provider visibility is platform-admin-only, and OpenAI image/speech adapters no longer read `config_json.api_key`.
- Files changed: `/backend/packages/providers/src/noveland/providers/{secrets,contracts,health,registry,service}.py`, `/backend/packages/providers/src/noveland/providers/adapters/{openai_image,openai_speech}.py`, `/backend/services/api/src/noveland/services/api/providers.py`, `/backend/tests/{test_api_providers.py,test_provider_execution_service.py,test_provider_registry_service.py,test_openai_speech_adapter.py,test_workspace_imports.py}`, `/docs/agent/harness/**`
- Tests added/updated: Provider registry secret rejection/resolver tests, provider execution auth-missing/secret-leak tests, provider API smoke/health/ACL tests, OpenAI speech adapter in-memory secret mapping update, and workspace import coverage for `noveland.providers.secrets`.
- Docs updated: change journal and active handoff.
- Follow-up notes: No schema migration was needed for Phase 8. Full vault/KMS, encrypted DB secret storage, provider marketplace/UI, streaming, fallback/load balancing, and live provider tests beyond env-gated smoke coverage remain deferred.

## Character Sprite / Scene Asset System Phase 9 plan entry

- Date: 2026-05-12
- Branch: main
- Scope: Final feature implementation plan for Character Sprite / Scene Asset System Phase 9.
- Summary: Added the version-prefixed Phase 9 plan for strict-worldline visual binding records, character sprite sets/variants, scene background profiles, deterministic sprite/background resolution, and scene composition through the existing Phase 6 image composer without adding Web UI, provider generation, public reader delivery, or `worlds.py` route growth.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.9-character-sprite-scene-asset-system-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/visual-asset-system` after this docs-only work is committed on `main`.

## Character Sprite / Scene Asset System Phase 9 implementation entry

- Date: 2026-05-12
- Branch: feat/visual-asset-system
- Scope: Backend-only strict-worldline visual asset binding and resolver foundation.
- Summary: Added `noveland-visual`, strict-worldline character sprite sets/variants, scene background profiles, deterministic sprite/background resolution, a safe visual API router, and compose-scene orchestration through the existing Phase 6 `ImageService.compose_image()` path. Visual API responses use safe asset/object references that omit storage URIs while records continue to point at existing `media_assets` and `media_objects`.
- Files changed: `/backend/packages/visual/**`, `/backend/services/api/src/noveland/services/api/{app,visual}.py`, `/backend/migrations/versions/20260512_0037_visual_asset_system.py`, `/backend/tests/{test_visual_service.py,test_api_visual.py,test_schema_metadata.py,test_alembic_config.py,test_workspace_imports.py}`, `/backend/{pyproject.toml,uv.lock}`, `/backend/services/api/pyproject.toml`, `/backend/packages/core/src/noveland/core/database.py`, `/docs/agent/harness/**`
- Tests added/updated: Visual service tests, visual API tests, schema metadata registration, Alembic head coverage, workspace import coverage, plus backend lint/type targeted checks.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: No Web UI, background generation, public reader delivery, nullable worldline defaults, second media framework, or second composer was added.

## Multimodal Conversation Turn Integration Phase 10 plan entry

- Date: 2026-05-12
- Branch: main
- Scope: Final feature implementation plan for Multimodal Conversation Turn Integration Phase 10.
- Summary: Added the version-prefixed Phase 10 plan for canonical conversation turn presentation state, visual render orchestration through Phase 9/Phase 6 services, speech render/transcription orchestration through Phase 7 services, media reference attachment, and same-worldline validation without adding Web preview/playback UI, public reader delivery, streaming, runtime daemon orchestration, or memory auto-write.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.10-multimodal-conversation-turn-integration-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/multimodal-turn-presentation` after this docs-only work is committed on `main`.

## Multimodal Conversation Turn Integration Phase 10 implementation entry

- Date: 2026-05-12
- Branch: feat/multimodal-turn-presentation
- Scope: Backend-only canonical turn presentation and render orchestration.
- Summary: Added `conversation_turn_presentations`, conversation presentation contracts/service, and an independent API router for presentation CRUD plus visual, speech, and transcription render actions. Visual rendering reuses Phase 9 `VisualResolver` and Phase 6 deterministic composition through `VisualCompositionService`; speech rendering and transcription reuse Phase 7 `SpeechService`; rendered assets attach through Phase 4 `media_references` without mutating turn text or auto-writing STT transcripts to memory.
- Files changed: `/backend/packages/conversations/src/noveland/conversations/{contracts,models,presentation,__init__}.py`, `/backend/services/api/src/noveland/services/api/{app,conversation_presentations}.py`, `/backend/migrations/versions/20260512_0038_conversation_turn_presentations.py`, `/backend/tests/{test_conversation_presentation_service.py,test_api_conversation_presentations.py,test_schema_metadata.py,test_alembic_config.py,test_workspace_imports.py}`, `/docs/agent/harness/**`
- Tests added/updated: Presentation service tests, presentation API render orchestration tests, schema metadata registration, Alembic head coverage, and workspace import coverage.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: No Web preview/playback UI, public reader delivery, streaming, runtime daemon orchestration, second composer, or memory auto-write was added.

## Background Asset Generation Orchestrator Phase 11 plan entry

- Date: 2026-05-12
- Branch: main
- Scope: Final feature implementation plan for Background Asset Generation Orchestrator Phase 11.
- Summary: Added the version-prefixed Phase 11 plan for admin-reviewed asset generation policies, preview runs, persisted proposals, explicit apply into queued media jobs, and media job reprioritize/cancel-superseded helpers. The plan explicitly reuses existing media jobs, visual/speech/presentation/provider capability records and excludes daemon hooks, automatic provider execution, Web UI, streaming, and public reader delivery.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.11-background-asset-generation-orchestrator-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/asset-generation-orchestrator` after this docs-only work is committed on `main`.

## Background Asset Generation Orchestrator Phase 11 implementation entry

- Date: 2026-05-12
- Branch: feat/asset-generation-orchestrator
- Scope: Backend-only admin-reviewed asset generation proposal orchestrator.
- Summary: Added `noveland-asset-generation`, strict-worldline asset generation policies/runs/proposals, preview analysis for missing visual/speech assets, explicit admin apply into queued `media_jobs`, and media job reprioritize/cancel-superseded helpers. Preview/apply do not execute providers, do not hook a daemon, and do not write to `world_events.payload`.
- Files changed: `/backend/packages/asset_generation/**`, `/backend/services/api/src/noveland/services/api/{app,asset_generation}.py`, `/backend/migrations/versions/20260512_0039_asset_generation_orchestrator.py`, `/backend/tests/{test_asset_generation_service.py,test_api_asset_generation.py,test_schema_metadata.py,test_alembic_config.py,test_workspace_imports.py}`, `/backend/{pyproject.toml,uv.lock}`, `/backend/services/api/pyproject.toml`, `/backend/packages/core/src/noveland/core/database.py`
- Tests added/updated: Asset generation service tests, asset generation API tests, schema metadata registration, Alembic head coverage, workspace import coverage, plus full local gate.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: No Web UI, runtime daemon hook, automatic provider execution, streaming, public reader delivery, or hidden background spend was added.

## Multimodal Evaluation And Diagnostics Phase 12 plan entry

- Date: 2026-05-12
- Branch: main
- Scope: Final feature implementation plan for Multimodal Evaluation And Diagnostics Phase 12.
- Summary: Added the version-prefixed Phase 12 plan for backend-only multimodal safety/cost/quality diagnostics, `multimodal-smoke` eval runs stored in existing `long_run_eval_runs`, diagnostics APIs, provider/media/invocation/visual/speech leak checks, and sample-world regression coverage without creating a duplicate release framework.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.12-multimodal-eval-diagnostics-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/multimodal-eval-diagnostics` after this docs-only work is committed on `main`.

## Architecture Freeze & Regression Fixture Phase 13 plan entry

- Date: 2026-05-13
- Branch: main
- Scope: Final feature implementation plan for Architecture Freeze & Regression Fixture Phase 13.
- Summary: Added the version-prefixed Phase 13 plan for freezing Phase 3-12 architecture boundaries, adding architecture/API/data model inventories, concise ADRs, a multimodal sample-world fixture, and a regression test entrypoint without adding new product features, providers, Web UI, daemon execution, streaming, schema normalization, or release gate semantic changes.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.13-architecture-freeze-regression-fixture-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/architecture-freeze-regression-fixture` after this docs-only work is committed on `main`.

## Architecture Freeze & Regression Fixture Phase 13 implementation entry

- Date: 2026-05-13
- Branch: feat/architecture-freeze-regression-fixture
- Scope: Architecture freeze docs, ADRs, sample-world fixture, and regression entrypoint.
- Summary: Added Phase 3-12 architecture contract documentation, API and data model inventories, concise accepted ADRs, sample-world fixture documentation, a deterministic backend fixture helper, and a regression test that verifies worldline isolation, media integrity, resolver behavior, provider secret hygiene, access control, event payload hygiene, asset-generation admin control, and multimodal diagnostics.
- Files changed: `/docs/agent/architecture/{current-system-contracts.md,api-contract-inventory.md,data-model-inventory.md,adr/*.md}`, `/docs/agent/fixtures/multimodal-sample-world.md`, `/backend/tests/fixtures/multimodal_sample_world.py`, `/backend/tests/test_multimodal_sample_world_regression.py`, `/docs/agent/harness/**`
- Tests added/updated: `test_multimodal_sample_world_regression.py` plus targeted Phase 13 regression command.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: No new provider capability, business feature, Web UI, daemon execution, streaming, release gate semantic change, schema migration, or `worlds.py` refactor should be introduced in this phase.

## v0.4 Admin UX Foundation plan entry

- Date: 2026-05-13
- Branch: main
- Scope: Final implementation plan for v0.4 Operator/Admin UX Phase 1.
- Summary: Added the v0.4.1 plan for shared admin shell conventions, route guards, loading/error/empty states, admin API client conventions, and table/detail/action patterns. The phase explicitly avoids backend behavior changes, schema migrations, concrete provider/media/visual/speech business consoles, public reader UI, and daemon or streaming behavior.
- Files changed: `/docs/agent/harness/feature-updates/v0.4.1-admin-ux-foundation-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, task board, and active handoff.
- Follow-up notes: Implementation should start on `feat/admin-ux-foundation` after this docs-only work is committed on `main`.

## v0.4 Admin UX Foundation implementation entry

- Date: 2026-05-13
- Branch: feat/admin-ux-foundation
- Scope: Shared Web admin foundation for v0.4 Operator/Admin UX.
- Summary: Added reusable admin notice, state, section, metric, table, description-list, action-bar components; added a platform-admin route guard helper; added a small admin request helper that preserves CSRF and same-origin fetch conventions; and wired existing platform admin pages through the shared guard without changing backend behavior or adding new business consoles.
- Files changed: `/web/features/admin/admin-foundation.tsx`, `/web/features/admin/admin-route-guard.ts`, `/web/lib/admin/api-client.ts`, `/web/app/admin/**/page.tsx`, `/web/app/globals.css`, `/web/features/admin/*.test.tsx`, `/web/lib/admin/api-client.test.ts`, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: `admin-foundation`, `admin-route-guard`, and `admin/api-client` Web tests; targeted admin tests; full local gate.
- Docs updated: OpenSpec tasks, change journal, file inventory, project index, task board, and active handoff.
- Follow-up notes: Phase 2 should build the provider admin console on top of these shared admin patterns. No backend behavior, migrations, provider adapters, Web reader UI, daemon behavior, streaming, or public media delivery was added.

## v0.4 Provider Admin Console plan entry

- Date: 2026-05-13
- Branch: main
- Scope: Final implementation plan for v0.4 Operator/Admin UX Phase 2.
- Summary: Added the v0.4.2 plan for a world-scoped provider integration admin console at `/worlds/{worldId}/providers`, while leaving the legacy `/admin/providers` provider-profile page unchanged. The plan covers provider integration CRUD, capabilities, health-check history/action, smoke-test action, auth_ref reference display, and restricted visibility handling without backend kernel changes, migrations, resolved secret display, new adapters, public reader provider exposure, or provider boundary changes.
- Files changed: `/docs/agent/harness/feature-updates/v0.4.2-provider-admin-console-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, task board, and active handoff.
- Follow-up notes: Implementation should start on `feat/provider-admin-console` after this docs-only work is committed on `main`.

## v0.4 Provider Admin Console implementation entry

- Date: 2026-05-13
- Branch: feat/provider-admin-console
- Scope: World-scoped Web admin console for Phase 5+ provider integrations.
- Summary: Added `/worlds/{worldId}/providers`, provider integration client helpers, server-side provider admin data loader, and a provider integration admin component for list/detail, create/update/delete, capabilities, health-check history/action, smoke-test action, auth_ref reference display, and restricted visibility notices. The legacy `/admin/providers` provider-profile page remains unchanged.
- Files changed: `/web/app/worlds/[worldId]/providers/page.tsx`, `/web/features/admin/provider-integration-admin.tsx`, `/web/lib/worlds/provider-integrations.ts`, `/web/lib/worlds/server.ts`, `/web/features/workspace/workspace-shell.tsx`, related Web tests, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: Provider integration client tests and provider integration admin component tests.
- Docs updated: OpenSpec tasks, change journal, file inventory, project index, task board, and active handoff.
- Follow-up notes: No backend provider kernel changes, migrations, new provider adapters, resolved secret display, public reader provider exposure, or provider execution boundary changes were added.

## v0.4 Provider Admin Console merge entry

- Date: 2026-05-13
- Branch: main
- Scope: Fast-forward merge completion for v0.4 Operator/Admin UX Phase 2.
- Summary: Fast-forward merged `feat/provider-admin-console` into local `main` after the full local gate passed. OpenSpec Phase 2 tasks now mark full gate and merge complete, and the active handoff points to Phase 3 Media Asset Admin Console.
- Files changed: `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 2 full local gate.
- Docs updated: OpenSpec tasks, change journal, and active handoff.
- Follow-up notes: Start Phase 3 from clean local `main`; do not push unless explicitly requested.

## v0.4 Media Asset Admin Console plan entry

- Date: 2026-05-13
- Branch: main
- Scope: Final implementation plan for v0.4 Operator/Admin UX Phase 3.
- Summary: Added the v0.4.3 plan for a world-scoped media asset admin console at `/worlds/{worldId}/media`. The plan covers asset list/detail, object list/download actions, job list/status, reference browser, upload flow, visibility/status filters, safe metadata summaries, and reuse of existing media APIs without backend media kernel changes.
- Files changed: `/docs/agent/harness/feature-updates/v0.4.3-media-admin-console-plan.md`, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, task board, and active handoff.
- Follow-up notes: Implementation should start on `feat/media-admin-console` after this docs-only work is committed on `main`.

## v0.4 Media Asset Admin Console implementation entry

- Date: 2026-05-13
- Branch: feat/media-admin-console
- Scope: World-scoped Web admin console for media assets, objects, jobs, references, uploads, and safe download actions.
- Summary: Added `/worlds/{worldId}/media`, media client helpers, server-side media admin data loader, and a media admin component for asset list/detail, object list/download actions, job status/actions, reference browsing, upload flow, and filters. The UI summarizes metadata and request JSON without rendering internal object storage references, file paths, raw bytes, base64, raw prompts, or raw outputs.
- Files changed: `/web/app/worlds/[worldId]/media/page.tsx`, `/web/features/admin/media-admin.tsx`, `/web/lib/worlds/media.ts`, `/web/lib/worlds/server.ts`, `/web/features/workspace/workspace-shell.tsx`, related Web tests, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: Media client tests, media admin component tests, and e2e stabilization for slow mock-server action/navigation waits.
- Docs updated: OpenSpec tasks, change journal, file inventory, project index, task board, and active handoff.
- Verification: Targeted tests passed; full local gate passed with backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`88 passed`), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: No backend media kernel behavior, migrations, storage backend, public reader media delivery, provider execution, asset generation, daemon behavior, or `worlds.py` change was added. Fast-forward merge to local `main` remains next.

## v0.4 Media Asset Admin Console merge entry

- Date: 2026-05-13
- Branch: main
- Scope: Fast-forward merge completion for v0.4 Operator/Admin UX Phase 3.
- Summary: Fast-forward merged `feat/media-admin-console` into local `main` after the targeted tests and full local gate passed. OpenSpec Phase 3 tasks now mark the fast-forward merge complete, and the active handoff points to Phase 4 Visual Asset Admin Console planning.
- Files changed: `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 3 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 4 from clean local `main`; do not push unless explicitly requested.

## v0.4 Visual Asset Admin Console plan entry

- Date: 2026-05-13
- Branch: main
- Scope: Final implementation plan for v0.4 Operator/Admin UX Phase 4.
- Summary: Added the v0.4.4 plan for a world-scoped visual asset admin console at `/worlds/{worldId}/visual`. The plan covers strict-worldline sprite sets, sprite variants, scene backgrounds, sprite/background resolver previews, and explicit compose-scene actions using existing visual and media APIs without backend visual behavior changes.
- Files changed: `/docs/agent/harness/feature-updates/v0.4.4-visual-admin-console-plan.md`, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, task board, and active handoff.
- Follow-up notes: Implementation should start on `feat/visual-admin-console` after this docs-only work is committed on `main`.

## v0.4 Visual Asset Admin Console implementation entry

- Date: 2026-05-13
- Branch: feat/visual-admin-console
- Scope: World-scoped Web admin console for strict-worldline sprite sets, sprite variants, scene backgrounds, resolver previews, and explicit compose-scene actions.
- Summary: Added `/worlds/{worldId}/visual`, visual client helpers, server-side visual admin data loader, and a visual admin component for selecting a worldline, managing sprite/background records, running deterministic resolver previews, and explicitly composing scenes through the existing visual compose endpoint. The UI displays safe media identifiers, dimensions, checksums, statuses, visibility, and fallback reasons without rendering storage URIs, filesystem paths, raw bytes, base64 payloads, raw prompts, or raw outputs.
- Files changed: `/web/app/worlds/[worldId]/visual/page.tsx`, `/web/features/admin/visual-admin.tsx`, `/web/lib/worlds/visual.ts`, `/web/lib/worlds/server.ts`, `/web/features/workspace/workspace-shell.tsx`, related Web tests, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: Visual client tests, visual admin component tests, and workspace navigation test.
- Docs updated: OpenSpec tasks, change journal, file inventory, project index, task board, and active handoff.
- Verification: Targeted tests passed with `npm run test -- visual-admin visual workspace-shell` (3 files, 8 tests), plus web lint, web typecheck, and `git diff --check`. Full local gate passed with backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`96 passed` after standalone rerun), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: No backend visual behavior, migrations, automatic sprite/background generation, asset generation orchestration, nullable-worldline visual defaults, public reader delivery, provider execution, daemon behavior, streaming, or `worlds.py` change was added. `web npm run test` timed out once when run concurrently with backend pytest due to Vitest worker startup timeouts; the standalone rerun passed.

## v0.4 Visual Asset Admin Console merge entry

- Date: 2026-05-13
- Branch: main
- Scope: Fast-forward merge completion for v0.4 Operator/Admin UX Phase 4.
- Summary: Fast-forward merged `feat/visual-admin-console` into local `main` after the targeted tests and full local gate passed. OpenSpec Phase 4 tasks now mark the fast-forward merge complete, and the active handoff points to Phase 5 Speech Admin Console planning.
- Files changed: `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 4 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 5 from clean local `main`; do not push unless explicitly requested.

## v0.4 Speech Admin Console plan entry

- Date: 2026-05-13
- Branch: main
- Scope: Final implementation plan for v0.4 Operator/Admin UX Phase 5.
- Summary: Added the v0.4.5 plan for a world-scoped speech admin console at `/worlds/{worldId}/speech`. The plan covers voice profile CRUD, agent voice bindings, style mappings, transcript browsing, and explicit TTS/STT test actions using existing speech, provider, media, and invocation APIs without backend speech behavior changes.
- Files changed: `/docs/agent/harness/feature-updates/v0.4.5-speech-admin-console-plan.md`, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, task board, and active handoff.
- Follow-up notes: Implementation should start on `feat/speech-admin-console` after this docs-only work is committed on `main`.

## v0.4 Speech Admin Console implementation entry

- Date: 2026-05-13
- Branch: feat/speech-admin-console
- Scope: World-scoped Web admin console for voice profiles, agent voice bindings, speech style mappings, transcripts, and explicit TTS/STT test actions.
- Summary: Added `/worlds/{worldId}/speech`, speech client helpers, server-side speech admin data loader, and a speech admin component for managing voice profiles, binding agents to voices, editing style mappings, browsing transcripts, and running explicit TTS/STT tests through existing speech APIs. The UI displays safe media job, media asset/object, transcript, and invocation IDs without rendering storage URIs, filesystem paths, raw bytes, base64 payloads, raw prompts, raw outputs, or resolved secrets.
- Files changed: `/web/app/worlds/[worldId]/speech/page.tsx`, `/web/features/admin/speech-admin.tsx`, `/web/lib/worlds/speech.ts`, `/web/lib/worlds/server.ts`, `/web/features/workspace/workspace-shell.tsx`, related Web tests, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: Speech client tests, speech admin component tests, and workspace navigation test.
- Docs updated: OpenSpec tasks, change journal, file inventory, project index, task board, and active handoff.
- Verification: Targeted tests passed with `npm run test -- speech-admin speech workspace-shell` (3 files, 7 tests). Full local gate passed with backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`102 passed`), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: No backend speech behavior, migrations, realtime voice, streaming, local voice server deployment, automatic STT memory writes, public reader audio delivery, provider adapter changes, daemon behavior, or `worlds.py` change was added.

## v0.4 Speech Admin Console merge entry

- Date: 2026-05-13
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.4 Operator/Admin UX Phase 5.
- Summary: Fast-forward merged `feat/speech-admin-console` into local `main` after the targeted tests and full local gate passed. OpenSpec Phase 5 tasks now mark the full gate, fast-forward merge, and harness update complete, and the active handoff points to Phase 6 Invocation Ledger Browser planning.
- Files changed: `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 5 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 6 from clean local `main`; do not push unless explicitly requested.

## v0.4 Invocation Ledger Browser plan entry

- Date: 2026-05-13
- Branch: main
- Scope: Final implementation plan for v0.4 Operator/Admin UX Phase 6.
- Summary: Added the v0.4.6 plan for a world-scoped invocation ledger browser at `/worlds/{worldId}/invocations`. The plan covers invocation list/detail, prompt snapshot evidence, tag management, redaction actions, visibility, and retention display using existing invocation APIs without backend ledger behavior changes.
- Files changed: `/docs/agent/harness/feature-updates/v0.4.6-invocation-ledger-browser-plan.md`, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, task board, and active handoff.
- Follow-up notes: Implementation should start on `feat/invocation-ledger-browser` after this docs-only work is committed on `main`.

## v0.4 Invocation Ledger Browser implementation entry

- Date: 2026-05-13
- Branch: feat/invocation-ledger-browser
- Scope: World-scoped Web admin console for model invocation ledger records, prompt snapshots, tags, redaction actions, visibility, and retention state.
- Summary: Added `/worlds/{worldId}/invocations`, invocation ledger client helpers, server-side invocation admin data loader, and an invocation ledger browser component for filtering invocations, inspecting selected records, viewing prompt snapshot checksums/evidence, creating/deleting tags, and running explicit redaction actions through existing invocation APIs. The UI recursively redacts secret-like keys, storage URI/path values, and base64-like payloads before rendering evidence summaries.
- Files changed: `/web/app/worlds/[worldId]/invocations/page.tsx`, `/web/features/admin/invocation-ledger-admin.tsx`, `/web/lib/worlds/invocations.ts`, `/web/lib/worlds/server.ts`, `/web/features/workspace/workspace-shell.tsx`, related Web tests, `/web/app/globals.css`, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: Invocation ledger client tests, invocation ledger admin component tests, and workspace navigation test.
- Docs updated: OpenSpec tasks, change journal, file inventory, project index, task board, and active handoff.
- Verification: Targeted tests passed with `npm run test -- invocation-ledger invocation workspace-shell` (3 files, 6 tests). Full local gate passed with backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`107 passed`), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: No backend invocation behavior, migrations, external tracing export, reader/member raw prompt exposure, provider execution changes, daemon behavior, or `worlds.py` change was added.

## v0.4 Invocation Ledger Browser merge entry

- Date: 2026-05-13
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.4 Operator/Admin UX Phase 6.
- Summary: Fast-forward merged `feat/invocation-ledger-browser` into local `main` after the targeted tests and full local gate passed. OpenSpec Phase 6 tasks now mark the full gate, fast-forward merge, and harness update complete, and the active handoff points to Phase 7 Multimodal Diagnostics Dashboard planning.
- Files changed: `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 6 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 7 from clean local `main`; do not push unless explicitly requested.

## v0.4 Multimodal Diagnostics Dashboard plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.4 Operator/Admin UX Phase 7.
- Summary: Added the v0.4.7 plan for a world-scoped multimodal diagnostics dashboard at `/worlds/{worldId}/diagnostics`. The plan covers current diagnostics, blocker/warning summaries, safe evidence references, recent multimodal eval runs, cost/latency summaries, provider/media/invocation/visual/speech status summaries, and an explicit multimodal smoke eval action using existing backend APIs without backend diagnostic rule changes.
- Files changed: `/docs/agent/harness/feature-updates/v0.4.7-multimodal-diagnostics-dashboard-plan.md`, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, task board, and active handoff.
- Follow-up notes: Implementation should start on `feat/multimodal-diagnostics-dashboard` after this docs-only work is committed on `main`.

## v0.4 Multimodal Diagnostics Dashboard implementation entry

- Date: 2026-05-14
- Branch: feat/multimodal-diagnostics-dashboard
- Scope: World-scoped Web admin dashboard for Phase 12 multimodal diagnostics, findings, safe evidence references, metrics, and eval runs.
- Summary: Added `/worlds/{worldId}/diagnostics`, multimodal diagnostics client helpers, server-side diagnostics admin data loader, and a dashboard component for current diagnostic status, blocker/warning tables, recommendations, provider/media/invocation/visual/speech/event summaries, and explicit multimodal smoke eval runs through existing backend APIs.
- Files changed: `/web/app/worlds/[worldId]/diagnostics/page.tsx`, `/web/features/admin/multimodal-diagnostics-admin.tsx`, `/web/lib/worlds/diagnostics.ts`, `/web/lib/worlds/server.ts`, `/web/features/workspace/workspace-shell.tsx`, related Web tests, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: Multimodal diagnostics client tests, multimodal diagnostics admin component tests, and workspace navigation test.
- Docs updated: OpenSpec tasks, change journal, file inventory, project index, task board, and active handoff.
- Verification: Targeted tests passed with `npm run test -- multimodal-diagnostics diagnostics workspace-shell` (3 files, 6 tests). Full local gate passed with backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`112 passed` after standalone rerun; initial concurrent run with `next build` timed out), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: No backend diagnostic rule changes, migrations, duplicate release/eval framework, public launch gate changes, provider execution changes, daemon behavior, streaming, public reader delivery, or `worlds.py` change was added.

## v0.4 Multimodal Diagnostics Dashboard merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.4 Operator/Admin UX Phase 7.
- Summary: Fast-forward merged `feat/multimodal-diagnostics-dashboard` into local `main` after the targeted tests and full local gate passed. OpenSpec Phase 7 tasks now mark the full gate, fast-forward merge, and harness update complete, completing the v0.4 Operator/Admin UX implementation sequence locally.
- Files changed: `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 7 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: No push was performed. Archive the OpenSpec v0.4 change only if explicitly requested.

## v0.4 Operator/Admin UX archive entry

- Date: 2026-05-14
- Branch: main
- Scope: OpenSpec archive and release notes for the completed v0.4 Operator/Admin UX sequence.
- Summary: Promoted the seven v0.4 admin capabilities into current OpenSpec specs, archived `v0-4-operator-admin-ux`, and added release notes summarizing the completed operator/admin Web surfaces and validation evidence.
- Files changed: `/openspec/specs/admin-ux-foundation/spec.md`, `/openspec/specs/provider-admin-console/spec.md`, `/openspec/specs/media-admin-console/spec.md`, `/openspec/specs/visual-admin-console/spec.md`, `/openspec/specs/speech-admin-console/spec.md`, `/openspec/specs/invocation-ledger-browser/spec.md`, `/openspec/specs/multimodal-diagnostics-dashboard/spec.md`, `/openspec/changes/archive/2026-05-14-v0-4-operator-admin-ux/**`, `/docs/agent/harness/release-notes/v0.4-operator-admin-ux.md`, `/docs/agent/harness/**`
- Tests added/updated: Documentation/spec-only change; validate with OpenSpec validation and `git diff --check`.
- Docs updated: current OpenSpec specs, release notes, project index, file inventory, task board, change journal, and active handoff.
- Follow-up notes: v0.5 must begin with feasibility review only; no v0.5 implementation should start until its review is accepted.

## v0.5 Authoring subsystem architecture decision entry

- Date: 2026-05-14
- Branch: main
- Scope: OpenSpec planning update for v0.5 Authoring & Import Studio.
- Summary: Updated v0.5 OpenSpec docs to require a dedicated `backend/packages/authoring/` package and `authoring.py` API router, move import run/proposal/review/source-traceability preview/apply foundation into Phase 1, treat legacy authoring templates/jobs and world composition import as compatibility inputs/references, and keep lore/world-bible extraction proposal-only.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/proposal.md`, `/openspec/changes/v0-5-authoring-import-studio/design.md`, `/openspec/changes/v0-5-authoring-import-studio/phase-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/openspec/changes/v0-5-authoring-import-studio/specs/**`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation/spec-only change; validate with OpenSpec validation and `git diff --check`.
- Docs updated: v0.5 OpenSpec proposal, design, phase plan, tasks, capability specs, change journal, and active handoff.
- Follow-up notes: Do not start v0.5 implementation until explicitly requested; Phase 1 should implement only Authoring Import Core.

## v0.5 Authoring Import Core plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.5 Authoring & Import Studio Phase 1.
- Summary: Added the v0.5.1 plan for a dedicated authoring package/router and source registry plus import run/proposal/review/source-traceability preview/apply foundation. The plan explicitly avoids provider-backed extraction, automatic memory writes, direct lore/world-bible apply, new media/provider/memory frameworks, Web UI, and new `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.5.1-authoring-import-core-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, and change journal.
- Follow-up notes: Implementation should start on `feat/authoring-import-core` after this docs-only checkpoint is committed.

## v0.5 Authoring Import Core implementation entry

- Date: 2026-05-14
- Branch: feat/authoring-import-core
- Scope: Dedicated authoring package/router plus source registry and proposal/review/preview/apply foundation.
- Summary: Added `backend/packages/authoring/`, the app-level `/worlds/{world_id}/authoring` router, migration `20260514_0040`, source batch/asset/fragment records, import run/proposal/review decision/source traceability records, safe JSON validation, media same-worldline validation, preview without provider execution, and explicit proposal-kind-gated trace-only apply. Unsupported kinds such as lore remain blocked in Phase 1.
- Files changed: `/backend/packages/authoring/**`, `/backend/services/api/src/noveland/services/api/authoring.py`, `/backend/services/api/src/noveland/services/api/app.py`, `/backend/migrations/versions/20260514_0040_authoring_import_core.py`, backend workspace/config files, `/backend/tests/test_authoring_service.py`, `/backend/tests/test_api_authoring.py`, schema/import/Alembic tests, OpenSpec tasks, and harness docs.
- Tests added/updated: Authoring service/API tests, schema metadata registration, workspace imports, and Alembic latest-revision coverage.
- Docs updated: OpenSpec Phase 1 task status, project index, file inventory, and change journal.
- Verification: Targeted tests passed with `cd backend && uv run pytest tests/test_authoring_service.py tests/test_api_authoring.py tests/test_schema_metadata.py tests/test_alembic_config.py tests/test_workspace_imports.py` (`32 passed`). Full local gate passed with backend ruff, backend mypy, backend pytest (`298 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: No provider-backed extraction, direct lore/world-bible apply, automatic memory writes, new media/provider/memory framework, Web UI, daemon behavior, public reader delivery, streaming, or new `worlds.py` routes were added.

## v0.5 Authoring Import Core merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.5 Authoring & Import Studio Phase 1.
- Summary: Fast-forward merged `feat/authoring-import-core` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 1 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 1 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 2 from clean local `main`; do not push unless explicitly requested.

## v0.5 Script Parser & Dialogue Extractor plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.5 Authoring & Import Studio Phase 2.
- Summary: Added the v0.5.2 plan for deterministic parsing of existing authoring source fragments into reviewable Phase 1 proposals. The plan explicitly avoids provider-backed parsing, new migrations unless required, Web UI, direct canonical mutation, raw full source persistence, world events, and new `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.5.2-script-parser-dialogue-extractor-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, and change journal.
- Follow-up notes: Implementation should start on `feat/script-parser-dialogue-extractor` after this docs-only checkpoint is committed.

## v0.5 Script Parser & Dialogue Extractor implementation entry

- Date: 2026-05-14
- Branch: feat/script-parser-dialogue-extractor
- Scope: Backend-only deterministic script parser and dialogue extractor for v0.5 Authoring & Import Studio Phase 2.
- Summary: Added a deterministic authoring parser that converts existing source fragment excerpts into traceable Phase 1 authoring proposals for dialogue, unresolved quoted dialogue, scenes, choices, routes, and events. Added `parse-script` on the dedicated authoring router. The implementation does not call providers, does not add migrations, does not mutate canonical world state, does not write world events, and does not add Web UI or `worlds.py` routes.
- Files changed: `/backend/packages/authoring/src/noveland/authoring/parser.py`, `/backend/packages/authoring/src/noveland/authoring/contracts.py`, `/backend/packages/authoring/src/noveland/authoring/service.py`, `/backend/services/api/src/noveland/services/api/authoring.py`, `/backend/tests/test_authoring_service.py`, `/backend/tests/test_api_authoring.py`, `/backend/tests/test_workspace_imports.py`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Authoring service parser coverage, authoring API parser endpoint coverage, and workspace import coverage.
- Docs updated: OpenSpec Phase 2 task status, change journal, task board, and file inventory.
- Verification: Targeted tests passed with `cd backend && uv run pytest tests/test_authoring_service.py tests/test_api_authoring.py tests/test_workspace_imports.py tests/test_alembic_config.py` (`10 passed`). Full local gate passed with backend ruff, backend mypy (`233 source files`), backend pytest (`300 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, `git diff --check`, and `openspec validate v0-5-authoring-import-studio --strict --json`.
- Follow-up notes: Fast-forward merge Phase 2 to local `main`, then update merge bookkeeping before starting Phase 3. Do not push unless explicitly requested.

## v0.5 Script Parser & Dialogue Extractor merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.5 Authoring & Import Studio Phase 2.
- Summary: Fast-forward merged `feat/script-parser-dialogue-extractor` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 2 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 2 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 3 from clean local `main`; do not push unless explicitly requested.

## v0.5 Character & Relationship Extractor plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.5 Authoring & Import Studio Phase 3.
- Summary: Added the v0.5.3 plan for deterministic extraction of character, alias, faction, identity, relationship, and emotional-baseline candidates into reviewable Phase 1 authoring proposals. The plan explicitly avoids provider-backed extraction, migrations unless required, Web UI, direct agent/relationship/memory/world-bible mutation, world events, and new `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.5.3-character-relationship-extractor-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, and change journal.
- Follow-up notes: Implementation should start on `feat/character-relationship-extractor` after this docs-only checkpoint is committed.

## v0.5 Character & Relationship Extractor implementation entry

- Date: 2026-05-14
- Branch: feat/character-relationship-extractor
- Scope: Backend-only deterministic character and relationship extractor for v0.5 Authoring & Import Studio Phase 3.
- Summary: Added a deterministic authoring extractor that converts existing source fragment excerpts and optional Phase 2 dialogue speaker proposals into traceable Phase 1 authoring proposals for characters, aliases, factions, identities, relationships, and emotional baselines. Added `extract-characters` on the dedicated authoring router. The implementation does not call providers, does not add migrations, does not mutate canonical agents/relationships/memory/world-bible records, does not write world events, and does not add Web UI or `worlds.py` routes.
- Files changed: `/backend/packages/authoring/src/noveland/authoring/character_extractor.py`, `/backend/packages/authoring/src/noveland/authoring/contracts.py`, `/backend/packages/authoring/src/noveland/authoring/service.py`, `/backend/services/api/src/noveland/services/api/authoring.py`, `/backend/tests/test_authoring_service.py`, `/backend/tests/test_api_authoring.py`, `/backend/tests/test_workspace_imports.py`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Authoring service extractor coverage, authoring API extractor endpoint coverage, and workspace import coverage.
- Docs updated: OpenSpec Phase 3 task status, project index, change journal, and task board.
- Verification: Targeted tests passed with `cd backend && uv run pytest tests/test_authoring_service.py tests/test_api_authoring.py tests/test_workspace_imports.py tests/test_alembic_config.py` (`12 passed`). Full local gate passed with backend ruff, backend mypy (`234 source files`), backend pytest (`302 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, `git diff --check`, and `openspec validate v0-5-authoring-import-studio --strict --json`.
- Follow-up notes: Fast-forward merge Phase 3 to local `main`, then update merge bookkeeping before starting Phase 4. Do not push unless explicitly requested.

## v0.5 Character & Relationship Extractor merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.5 Authoring & Import Studio Phase 3.
- Summary: Fast-forward merged `feat/character-relationship-extractor` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 3 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 3 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 4 from clean local `main`; do not push unless explicitly requested.

## v0.5 World Bible & Lore Extractor plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.5 Authoring & Import Studio Phase 4.
- Summary: Added the v0.5.4 plan for deterministic proposal-only extraction of lore, location, organization, world-rule, secret, and knowledge-boundary candidates into reviewable Phase 1 authoring proposals. The plan explicitly avoids provider-backed extraction, migrations unless required, Web UI, direct `WorldBible` or global canon mutation, world events, and new `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.5.4-world-bible-lore-extractor-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, and change journal.
- Follow-up notes: Implementation should start on `feat/world-bible-lore-extractor` after this docs-only checkpoint is committed.

## v0.5 World Bible & Lore Extractor implementation entry

- Date: 2026-05-14
- Branch: feat/world-bible-lore-extractor
- Scope: Backend-only deterministic proposal-only lore extractor for v0.5 Authoring & Import Studio Phase 4.
- Summary: Added a deterministic authoring lore extractor that converts existing source fragment excerpts into traceable Phase 1 authoring proposals for lore, locations, organizations, world rules, secrets, and knowledge boundaries. Added `extract-lore` on the dedicated authoring router. The implementation does not call providers, does not add migrations, does not mutate `WorldBible` or global canon records, does not write world events, and does not add Web UI or `worlds.py` routes. Lore proposals remain blocked by the existing unsupported proposal-kind apply guardrail.
- Files changed: `/backend/packages/authoring/src/noveland/authoring/lore_extractor.py`, `/backend/packages/authoring/src/noveland/authoring/contracts.py`, `/backend/packages/authoring/src/noveland/authoring/service.py`, `/backend/services/api/src/noveland/services/api/authoring.py`, `/backend/tests/test_authoring_service.py`, `/backend/tests/test_api_authoring.py`, `/backend/tests/test_workspace_imports.py`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Authoring service lore extractor and blocked apply coverage, authoring API lore extractor endpoint coverage, and workspace import coverage.
- Docs updated: OpenSpec Phase 4 task status, project index, change journal, and task board.
- Verification: Targeted tests passed with `cd backend && uv run pytest tests/test_authoring_service.py tests/test_api_authoring.py tests/test_workspace_imports.py tests/test_alembic_config.py` (`14 passed`). Full local gate passed with backend ruff, backend mypy (`235 source files`), backend pytest (`304 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, `git diff --check`, and `openspec validate v0-5-authoring-import-studio --strict --json`.
- Follow-up notes: Fast-forward merge Phase 4 to local `main`, then update merge bookkeeping before starting Phase 5. Do not push unless explicitly requested.

## v0.5 World Bible & Lore Extractor merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.5 Authoring & Import Studio Phase 4.
- Summary: Fast-forward merged `feat/world-bible-lore-extractor` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 4 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 4 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 5 from clean local `main`; do not push unless explicitly requested.

## v0.5 Canon Conflict Review plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.5 Authoring & Import Studio Phase 5.
- Summary: Added the v0.5.5 plan for deterministic conflict review of existing import-run proposals, producing reviewable conflict report proposals for duplicates, relationship/identity/baseline contradictions, uncertain lore, and OOC risk. The plan explicitly avoids provider-backed review, migrations unless required, Web UI, automatic conflict resolution, direct canonical mutation, world events, and new `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.5.5-canon-conflict-review-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, and change journal.
- Follow-up notes: Implementation should start on `feat/canon-conflict-review` after this docs-only checkpoint is committed.

## v0.5 Canon Conflict Review implementation entry

- Date: 2026-05-14
- Branch: feat/canon-conflict-review
- Scope: Backend-only deterministic canon conflict review for v0.5 Authoring & Import Studio Phase 5.
- Summary: Added deterministic conflict review over existing import-run proposals, producing traceable `other` conflict report proposals for duplicate characters/lore/locations/organizations, relationship and identity/baseline contradictions, uncertain canon, and OOC risk. Added `review-conflicts` on the dedicated authoring router. The implementation does not call providers, does not add migrations, does not automatically resolve conflicts, does not mutate canonical records, does not write world events, and does not add Web UI or `worlds.py` routes.
- Files changed: `/backend/packages/authoring/src/noveland/authoring/conflict_review.py`, `/backend/packages/authoring/src/noveland/authoring/contracts.py`, `/backend/packages/authoring/src/noveland/authoring/service.py`, `/backend/services/api/src/noveland/services/api/authoring.py`, `/backend/tests/test_authoring_service.py`, `/backend/tests/test_api_authoring.py`, `/backend/tests/test_workspace_imports.py`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Authoring service conflict report coverage, authoring API conflict review endpoint coverage, and workspace import coverage.
- Docs updated: OpenSpec Phase 5 task status, project index, change journal, and task board.
- Verification: Targeted tests passed with `cd backend && uv run pytest tests/test_authoring_service.py tests/test_api_authoring.py tests/test_workspace_imports.py tests/test_alembic_config.py` (`16 passed`). Full local gate passed with backend ruff, backend mypy (`236 source files`), backend pytest (`306 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, `git diff --check`, and `openspec validate v0-5-authoring-import-studio --strict --json`.
- Follow-up notes: Fast-forward merge Phase 5 to local `main`, then update merge bookkeeping before starting Phase 6. Do not push unless explicitly requested.

## v0.5 Canon Conflict Review merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.5 Authoring & Import Studio Phase 5.
- Summary: Fast-forward merged `feat/canon-conflict-review` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 5 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 5 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 6 from clean local `main`; do not push unless explicitly requested.

## v0.5 Memory Migration Pipeline plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.5 Authoring & Import Studio Phase 6.
- Summary: Added the v0.5.6 plan for deterministic memory migration proposal generation from source fragments and existing import-run proposals. The plan explicitly avoids provider-backed extraction, migrations unless required, Web UI, direct memory writes, memory backend SDK access, direct canonical mutation, world events, and new `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.5.6-memory-migration-pipeline-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, and change journal.
- Follow-up notes: Implementation should start on `feat/memory-migration-pipeline` after this docs-only checkpoint is committed.

## v0.5 Memory Migration Pipeline implementation entry

- Date: 2026-05-14
- Branch: feat/memory-migration-pipeline
- Scope: Backend-only deterministic memory migration proposal generation for v0.5 Authoring & Import Studio Phase 6.
- Summary: Added a deterministic memory migration analyzer that converts source fragments and existing import-run proposals into reviewable fact, episodic, relationship, preference, and style memory proposals. The implementation reuses Phase 1 authoring runs/proposals, blocks direct memory proposal apply, avoids provider execution, avoids memory backend writes, and does not emit world events.
- Files changed: `/backend/packages/authoring/src/noveland/authoring/{__init__,contracts,memory_migration,service}.py`, `/backend/services/api/src/noveland/services/api/authoring.py`, `/backend/tests/test_authoring_service.py`, `/backend/tests/test_api_authoring.py`, `/backend/tests/test_workspace_imports.py`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Authoring service memory migration coverage, authoring API memory migration endpoint coverage, direct memory apply guardrail coverage, and workspace import coverage.
- Docs updated: OpenSpec tasks, project index, task board, active handoff, and change journal.
- Follow-up notes: Phase 6 full local gate passed; fast-forward merge to local `main`, record merge bookkeeping, then continue with Phase 7 Asset Import & Matching.

## v0.5 Memory Migration Pipeline merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.5 Authoring & Import Studio Phase 6.
- Summary: Fast-forward merged `feat/memory-migration-pipeline` into local `main`, marked Phase 6 complete in OpenSpec tasks, and moved harness handoff state to Phase 7 Asset Import & Matching.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: N/A.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 7 from clean local `main`; do not push unless explicitly requested.

## v0.5 Asset Import & Matching plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.5 Authoring & Import Studio Phase 7.
- Summary: Added the v0.5.7 plan for deterministic asset matching proposals that connect imported media-backed source assets to sprite, background, CG, and voice-reference candidates. The plan explicitly avoids provider-backed matching, migrations unless required, Web UI, new upload/media delivery paths, automatic visual/speech binding apply, direct canonical mutation, world events, and new `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.5.7-asset-import-matching-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Implementation should start on `feat/asset-import-matching` after this docs-only checkpoint is committed.

## v0.5 Asset Import & Matching implementation entry

- Date: 2026-05-14
- Branch: feat/asset-import-matching
- Scope: Backend-only deterministic asset matching proposal generation for v0.5 Authoring & Import Studio Phase 7.
- Summary: Added a deterministic asset matcher that turns imported media-backed source assets into reviewable sprite, background, CG, and voice-reference proposals. The implementation reuses Phase 1 authoring runs/proposals, validates same-worldline media assets, suppresses hidden/developer-only media, blocks unsupported canonical apply, avoids provider execution, avoids media job creation, and does not emit world events.
- Files changed: `/backend/packages/authoring/src/noveland/authoring/{__init__,asset_matching,contracts,service}.py`, `/backend/services/api/src/noveland/services/api/authoring.py`, `/backend/tests/test_authoring_service.py`, `/backend/tests/test_api_authoring.py`, `/backend/tests/test_workspace_imports.py`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Authoring service asset matching coverage, cross-worldline rejection coverage, hidden-media suppression coverage, authoring API asset matching endpoint coverage, and workspace import coverage.
- Docs updated: OpenSpec tasks, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Phase 7 full local gate passed; fast-forward merge to local `main`, record merge bookkeeping, then continue with Phase 8 Authoring Regression Fixture.

## v0.5 Asset Import & Matching merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.5 Authoring & Import Studio Phase 7.
- Summary: Fast-forward merged `feat/asset-import-matching` into local `main`, marked Phase 7 complete in OpenSpec tasks, and moved harness handoff state to Phase 8 Authoring Regression Fixture.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: N/A.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 8 from clean local `main`; do not push unless explicitly requested.

## v0.5 Authoring Regression Fixture plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.5 Authoring & Import Studio Phase 8.
- Summary: Added the v0.5.8 plan for a deterministic galgame import regression fixture covering source registry, script parsing, character extraction, lore proposal extraction, conflict review, memory migration, asset matching, review decisions, and guarded apply behavior. The plan explicitly avoids migrations, Web UI, production seed frameworks, provider-backed work, direct canonical mutation, media jobs, memory write jobs, world events, and new `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.5.8-authoring-regression-fixture-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Implementation should start on `feat/authoring-regression-fixture` after this docs-only checkpoint is committed.

## v0.5 Authoring Regression Fixture implementation entry

- Date: 2026-05-14
- Branch: feat/authoring-regression-fixture
- Scope: Backend-only deterministic authoring regression fixture for v0.5 Authoring & Import Studio Phase 8.
- Summary: Added an authoring sample import fixture and regression tests that exercise source registry, script parsing, character extraction, lore proposal extraction, conflict review, memory migration, asset matching, review decisions, and guarded apply behavior. The fixture validates deterministic signatures, strict worldline scope, no provider/media/memory/visual/speech side effects, no world events, and no storage/path/base64/raw prompt or output leaks.
- Files changed: `/backend/tests/fixtures/authoring_sample_import.py`, `/backend/tests/test_authoring_regression_fixture.py`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Authoring sample import deterministic signature, worldline scope, pipeline coverage, guarded apply, side-effect, and leak regression tests.
- Docs updated: OpenSpec tasks, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Phase 8 full local gate passed; fast-forward merge to local `main`, record merge bookkeeping, then provide v0.5 closeout status.

## v0.5 Authoring Regression Fixture merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping and closeout for v0.5 Authoring & Import Studio Phase 8.
- Summary: Fast-forward merged `feat/authoring-regression-fixture` into local `main`, marked Phase 8 and all v0.5 OpenSpec tasks complete, and updated harness state to v0.5 closeout.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: N/A.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: v0.5 is complete locally; OpenSpec archive and release notes remain optional docs-only follow-up if requested. Do not push unless explicitly requested.

## v0.6 Runtime Context Contract v2 implementation entry

- Date: 2026-05-15
- Branch: feat/runtime-context-contract-v2
- Scope: Backend-only v0.6 Runtime Narrative Quality Phase 1 runtime context contract preview.
- Summary: Added the dedicated `narrative_quality` package and app-level narrative quality router with an admin-only context preview endpoint for agent, conversation, GM, narrative, and eval context kinds. The implementation reuses existing living-world context, conversation, GM proposal, narrative artifact, and long-run eval records; validates worldline scope; redacts storage paths, media URIs, base64, raw prompt/output, and secret-like fields; and avoids provider calls, world event writes, migrations, Web dashboard work, and broad `worlds.py` routes.
- Files changed: `/backend/packages/narrative_quality/`, `/backend/services/api/src/noveland/services/api/narrative_quality.py`, `/backend/services/api/src/noveland/services/api/app.py`, `/backend/tests/test_narrative_quality_service.py`, `/backend/tests/test_api_narrative_quality.py`, `/backend/tests/test_workspace_imports.py`, `/backend/pyproject.toml`, `/backend/services/api/pyproject.toml`, `/backend/uv.lock`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Narrative quality service context preview coverage, narrative quality API ACL/redaction coverage, and workspace import coverage.
- Docs updated: OpenSpec Phase 1 task status, project index, file inventory, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff, backend mypy, targeted pytest (`10 passed`), OpenSpec strict changes/spec validation, and `git diff --check`. Full local gate passed with backend ruff, backend mypy (`246 source files`), backend pytest (`321 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: Commit Phase 1 implementation, fast-forward merge to local `main`, record merge bookkeeping, then start Phase 2 Provider-backed GM Proposal from clean local `main`. Do not push unless explicitly requested.

## v0.6 Runtime Context Contract v2 merge entry

- Date: 2026-05-15
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.6 Runtime Narrative Quality Phase 1.
- Summary: Fast-forward merged `feat/runtime-context-contract-v2` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 1 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: N/A.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 2 Provider-backed GM Proposal from clean local `main`; do not push unless explicitly requested.

## v0.6 Provider-backed GM Proposal plan entry

- Date: 2026-05-15
- Branch: main
- Scope: Final implementation plan for v0.6 Runtime Narrative Quality Phase 2.
- Summary: Added the Phase 2 plan for admin-only provider-backed GM proposal generation through the dedicated narrative quality boundary. The plan confirms current provider-kernel text generation is available through fake/local-stub execution with ledger evidence, forbids legacy provider profile fallback, keeps provider output behind proposal/review/apply boundaries, and avoids world event mutation, migrations unless proven necessary, broad `worlds.py` routes, Web UI, and new external provider adapters.
- Files changed: `/docs/agent/harness/feature-updates/v0.6.2-provider-backed-gm-proposal-plan.md`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Implementation should start on `feat/provider-backed-gm-proposal` after this docs-only checkpoint is committed.

## v0.6 Provider-backed GM Proposal implementation entry

- Date: 2026-05-15
- Branch: feat/provider-backed-gm-proposal
- Scope: Backend-only v0.6 Runtime Narrative Quality Phase 2 provider-backed GM proposal generation.
- Summary: Added admin-only provider-backed GM proposal generation under the dedicated narrative quality router. The implementation confirms provider-kernel text generation through fake/local-stub `ProviderExecutionService`, writes invocation and prompt snapshot evidence, creates proposed `gm_event_proposals` only after provider execution succeeds, supports dry-run without proposal persistence, stores safe traceability in `source_context`, rejects non-text providers, and avoids world event mutation, migrations, Web UI, broad `worlds.py` routes, and legacy provider profile fallback.
- Files changed: `/backend/packages/narrative_quality/src/noveland/narrative_quality/contracts.py`, `/backend/packages/narrative_quality/src/noveland/narrative_quality/service.py`, `/backend/services/api/src/noveland/services/api/narrative_quality.py`, `/backend/tests/test_narrative_quality_service.py`, `/backend/tests/test_api_narrative_quality.py`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Narrative quality service coverage for provider-backed proposal creation, dry-run behavior, non-text provider rejection, traceability redaction, plus API coverage for creation and ACL.
- Docs updated: OpenSpec Phase 2 task status, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff, backend mypy, targeted pytest (`21 passed`), OpenSpec strict changes/spec validation, and `git diff --check`. Full local gate passed with backend ruff, backend mypy (`246 source files`), backend pytest (`327 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: Commit Phase 2 implementation, fast-forward merge to local `main`, record merge bookkeeping, then start Phase 3 Dialogue Style & OOC Review from clean local `main`. Do not push unless explicitly requested.

## v0.6 Provider-backed GM Proposal merge entry

- Date: 2026-05-15
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.6 Runtime Narrative Quality Phase 2.
- Summary: Fast-forward merged `feat/provider-backed-gm-proposal` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 2 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: N/A.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 3 Dialogue Style & OOC Review from clean local `main`; do not push unless explicitly requested.

## v0.6 Dialogue Style & OOC Review plan entry

- Date: 2026-05-15
- Branch: main
- Scope: Final implementation plan for v0.6 Runtime Narrative Quality Phase 3.
- Summary: Added the Phase 3 plan for API-first deterministic dialogue style and out-of-character review through the narrative quality boundary. The plan reuses conversation turns, agent profiles, relationships, and context helpers; avoids provider-backed review, migrations unless required, Web UI, automatic dialogue blocking, turn mutation, memory writes, world events, and broad `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.6.3-dialogue-style-ooc-review-plan.md`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Implementation should start on `feat/dialogue-style-ooc-review` after this docs-only checkpoint is committed.

## v0.6 Dialogue Style & OOC Review implementation entry

- Date: 2026-05-15
- Branch: feat/dialogue-style-ooc-review
- Scope: Backend-only v0.6 Runtime Narrative Quality Phase 3 deterministic dialogue style and OOC review.
- Summary: Added admin-only dialogue review under the narrative quality router. The implementation reviews existing conversation turns or explicit text samples, validates conversation worldline scope, compares against speaker profile and relationship context, returns structured findings and scores, redacts unsafe operational content, avoids provider calls, avoids turn mutation, avoids memory writes, avoids world events, and keeps diagnostics out of reader/member routes.
- Files changed: `/backend/packages/narrative_quality/src/noveland/narrative_quality/contracts.py`, `/backend/packages/narrative_quality/src/noveland/narrative_quality/service.py`, `/backend/services/api/src/noveland/services/api/narrative_quality.py`, `/backend/tests/test_narrative_quality_service.py`, `/backend/tests/test_api_narrative_quality.py`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Narrative quality service coverage for turn review, unsafe text redaction, cross-worldline rejection, plus API coverage for dialogue review and ACL.
- Docs updated: OpenSpec Phase 3 task status, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff, backend mypy, targeted pytest (`21 passed`), OpenSpec strict changes/spec validation, and `git diff --check`. Full local gate passed with backend ruff, backend mypy (`246 source files`), backend pytest (`332 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed` after rerun), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Flaky notes: The first full Web test run had one isolated `agent-builder.test.tsx` mock-call failure; the individual test passed immediately afterward, and the full Web test/build/e2e sequence passed on rerun.
- Follow-up notes: Commit Phase 3 implementation, fast-forward merge to local `main`, record merge bookkeeping, then start Phase 4 Emotion/Sprite/Voice Alignment from clean local `main`. Do not push unless explicitly requested.

## v0.6 Dialogue Style & OOC Review merge entry

- Date: 2026-05-15
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.6 Runtime Narrative Quality Phase 3.
- Summary: Fast-forward merged `feat/dialogue-style-ooc-review` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 3 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: N/A.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 4 Emotion/Sprite/Voice Alignment from clean local `main`; do not push unless explicitly requested.

## v0.6 Emotion/Sprite/Voice Alignment plan entry

- Date: 2026-05-15
- Branch: main
- Scope: Final implementation plan for v0.6 Runtime Narrative Quality Phase 4.
- Summary: Added the Phase 4 plan for API-first deterministic alignment diagnostics over turn presentation emotion, sprite variant, voice profile, voice binding, and speech style mapping records. The plan requires reuse of presentation, visual, and speech systems and explicitly avoids provider calls, media generation, automatic binding changes, Web UI, migrations unless required, world events, and broad `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.6.4-emotion-sprite-voice-alignment-plan.md`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Implementation should start on `feat/emotion-sprite-voice-alignment` after this docs-only checkpoint is committed.

## v0.6 Emotion/Sprite/Voice Alignment implementation entry

- Date: 2026-05-15
- Branch: feat/emotion-sprite-voice-alignment
- Scope: Backend-only v0.6 Runtime Narrative Quality Phase 4 deterministic emotion/sprite/voice alignment diagnostics.
- Summary: Added admin-only turn presentation alignment diagnostics under the narrative quality router. The implementation validates conversation and presentation worldline scope, checks emotion keys against sprite variant expressions and mood tags, checks sprite set speaker binding, checks voice profile and agent voice binding availability, checks speech style mapping availability, returns structured findings and suggested fixes, and avoids provider calls, media jobs, automatic mutations, world events, Web UI, migrations, and broad `worlds.py` routes.
- Files changed: `/backend/packages/narrative_quality/src/noveland/narrative_quality/contracts.py`, `/backend/packages/narrative_quality/src/noveland/narrative_quality/service.py`, `/backend/services/api/src/noveland/services/api/narrative_quality.py`, `/backend/tests/test_narrative_quality_service.py`, `/backend/tests/test_api_narrative_quality.py`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Narrative quality service coverage for aligned presentations, missing voice bindings, sprite/emotion mismatch, cross-worldline rejection, no event writes, plus API coverage for alignment diagnostics and ACL.
- Docs updated: OpenSpec Phase 4 task status, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff, backend mypy, targeted pytest (`27 passed`), OpenSpec strict changes/spec validation, and `git diff --check`. Full local gate passed with backend ruff, backend mypy (`246 source files`), backend pytest (`338 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: Commit Phase 4 implementation, fast-forward merge to local `main`, record merge bookkeeping, then start Phase 5 Narrative Writer v2 from clean local `main`. Do not push unless explicitly requested.

## v0.6 Emotion/Sprite/Voice Alignment merge entry

- Date: 2026-05-15
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.6 Runtime Narrative Quality Phase 4.
- Summary: Fast-forward merged `feat/emotion-sprite-voice-alignment` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 4 tasks now mark the fast-forward merge complete, and the active handoff points to Phase 5 Narrative Writer v2 planning.
- Files changed: `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 4 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 5 Narrative Writer v2 from clean local `main`; do not push unless explicitly requested.
