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
