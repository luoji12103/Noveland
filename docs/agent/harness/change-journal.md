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
