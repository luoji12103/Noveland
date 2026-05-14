# Provider Admin Console Specification

## Purpose

This spec captures the current v0.4 world-scoped provider integration admin console on `main`. The console lets authorized admins inspect provider integrations, capabilities, health checks, and smoke-test status through existing provider APIs without exposing resolved secrets or changing provider execution behavior.

## Requirements

### Requirement: Provider integration list and detail are admin-only
The system SHALL expose a world-scoped Web admin page for provider integrations using the existing `/worlds/{worldId}/providers` backend surface and Web proxy/client helpers.

#### Scenario: Admin inspects providers
- **GIVEN** an authorized world admin opens `/worlds/{worldId}/providers`
- **WHEN** provider data is loaded
- **THEN** the page SHALL show provider list/detail information, adapter kind, provider kind, status, and safe config summaries
- **AND** it SHALL not expose resolved secret values.

### Requirement: Provider capabilities and health checks are visible safely
The system SHALL show declared capabilities and health-check history using existing provider capability and health routes.

#### Scenario: Admin reviews provider health
- **GIVEN** a provider integration has capability and health records
- **WHEN** the admin selects that provider
- **THEN** the page SHALL display safe capability and health metadata
- **AND** secret-like or raw request material SHALL be omitted or redacted.

### Requirement: Smoke-test actions reuse existing provider routes
The system SHALL allow an authorized admin to trigger provider smoke/test actions through existing provider APIs.

#### Scenario: Admin runs a smoke test
- **GIVEN** an authorized admin selects a provider integration
- **WHEN** they submit the smoke-test action
- **THEN** the Web client SHALL call the existing provider endpoint
- **AND** the result SHALL be rendered from safe response fields only.

### Requirement: Provider admin preserves legacy provider profile separation
The system SHALL keep `/admin/providers` for legacy platform provider profiles and `/worlds/{worldId}/providers` for Phase 5+ provider integrations.

#### Scenario: Operator switches provider pages
- **GIVEN** an operator needs platform provider profiles and world provider integrations
- **WHEN** they use navigation
- **THEN** each page SHALL point to the correct backend contract
- **AND** the world-scoped console SHALL not mutate legacy provider profile records.

## Non-goals

- This spec does not define new provider adapters.
- This spec does not define resolved secret display or user-managed secret UI.
- This spec does not define provider fallback, load balancing, marketplace, or streaming.
- This spec does not change provider execution, registry, health, or smoke-test backend semantics.
