# Multimodal Diagnostics Dashboard Specification

## Purpose

This spec captures the current v0.4 world-scoped multimodal diagnostics dashboard on `main`. The dashboard lets authorized admins review Phase 12 multimodal diagnostics, safe evidence references, eval runs, findings, metrics, and an explicit multimodal smoke eval action through existing diagnostic APIs.

## Requirements

### Requirement: Dashboard displays current multimodal diagnostics
The system SHALL provide a world-scoped Web admin dashboard for multimodal diagnostic status using existing multimodal eval and diagnostics APIs.

#### Scenario: Admin opens diagnostics
- **GIVEN** an authorized world admin opens `/worlds/{worldId}/diagnostics`
- **WHEN** current diagnostics load
- **THEN** the dashboard SHALL show summary status, blockers, warnings, recommendations, and component metrics
- **AND** evidence SHALL be rendered from safe references rather than raw prompt, secret, storage, or binary content.

### Requirement: Dashboard summarizes provider, media, invocation, visual, speech, and event checks
The system SHALL present existing diagnostic summaries for provider health, media integrity, invocation coverage, visual defaults, speech bindings, event payload leak checks, and cost/latency metrics.

#### Scenario: Admin reviews component findings
- **GIVEN** diagnostics include provider, media, invocation, visual, speech, and event findings
- **WHEN** the dashboard renders component sections
- **THEN** each finding SHALL show severity, code, message, and safe evidence references
- **AND** the dashboard SHALL not introduce backend diagnostic rules.

### Requirement: Dashboard lists recent multimodal eval runs
The system SHALL show recent multimodal eval runs backed by existing eval records.

#### Scenario: Admin reviews eval history
- **GIVEN** multimodal smoke eval runs exist
- **WHEN** the dashboard loads eval history
- **THEN** it SHALL display run status, timestamps, summary metrics, and blockers
- **AND** it SHALL not create a duplicate release or eval framework.

### Requirement: Dashboard can trigger explicit multimodal smoke eval
The system SHALL allow an authorized admin to start an explicit multimodal smoke eval through the existing multimodal eval API.

#### Scenario: Admin starts smoke eval
- **GIVEN** an authorized admin requests a multimodal smoke eval
- **WHEN** the Web action posts to the eval route
- **THEN** the backend SHALL create the eval run through existing services
- **AND** no provider execution, daemon behavior, or public launch gate change SHALL be added by the dashboard.

## Non-goals

- This spec does not define backend diagnostic rule changes.
- This spec does not define public launch gate changes.
- This spec does not define duplicate eval/release frameworks.
- This spec does not define provider execution, daemon execution, streaming, or public reader delivery.
