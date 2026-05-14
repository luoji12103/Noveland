# Admin UX Foundation Specification

## Purpose

This spec captures the current v0.4 admin UX foundation on `main`: shared admin layout primitives, route guard conventions, API request helpers, loading/error/empty states, metric/table/detail patterns, and workspace navigation integration.

## Requirements

### Requirement: Admin surfaces reuse shared foundation components
The system SHALL provide shared admin UI primitives for notices, summaries, metrics, tables, detail panels, action groups, and stable loading, error, and empty states.

#### Scenario: Admin page uses foundation primitives
- **GIVEN** a v0.4 admin page renders provider, media, visual, speech, invocation, or diagnostics data
- **WHEN** the page presents state, tables, details, or actions
- **THEN** it SHALL use the shared admin foundation patterns
- **AND** it SHALL avoid page-local replacements for common admin states.

### Requirement: Admin routes use established authorization patterns
The system SHALL use the existing platform/world admin route guard and same-origin auth proxy conventions for admin routes.

#### Scenario: Unauthorized actor reaches an admin route
- **GIVEN** an actor without the required admin role opens an admin surface
- **WHEN** the server-side route guard evaluates the request
- **THEN** the request SHALL be denied or redirected through the existing auth flow
- **AND** protected admin data SHALL NOT be rendered.

### Requirement: Admin API calls use existing same-origin client conventions
The system SHALL use existing CSRF-aware same-origin API helpers and world-scoped client modules for admin actions.

#### Scenario: Admin action posts to the backend
- **GIVEN** an admin submits a provider, media, visual, speech, invocation, or diagnostics action
- **WHEN** the Web app sends the request
- **THEN** it SHALL use the established proxy/client helper path
- **AND** it SHALL not bypass backend ACLs, validation, or redaction.

### Requirement: Workspace navigation exposes v0.4 admin surfaces
The system SHALL include world-scoped navigation entries for provider integrations, media, visual assets, speech, invocation ledger, and diagnostics.

#### Scenario: Admin navigates a world workspace
- **GIVEN** an authorized world admin is in a world workspace
- **WHEN** they inspect workspace navigation
- **THEN** the v0.4 admin destinations SHALL be discoverable
- **AND** legacy platform-admin provider profile pages SHALL remain separate from world-scoped provider integrations.

## Non-goals

- This spec does not define backend business logic changes.
- This spec does not define new provider, media, visual, speech, invocation, or eval APIs.
- This spec does not define public reader delivery, streaming, or daemon execution.
- This spec does not define a marketing or consumer-facing design system.
