# Invocation Ledger Browser Specification

## Purpose

This spec captures the current v0.4 world-scoped invocation ledger browser on `main`. The browser lets authorized admins inspect model invocations, prompt snapshots, tags, redaction actions, visibility, and retention state through existing invocation APIs.

## Requirements

### Requirement: Invocation ledger browser lists and filters invocations
The system SHALL provide a world-scoped Web admin page for model invocation ledger records using existing invocation search APIs.

#### Scenario: Admin searches invocations
- **GIVEN** an authorized world admin opens `/worlds/{worldId}/invocations`
- **WHEN** they filter by provider, capability, status, visibility, retention, or tags
- **THEN** the page SHALL display matching invocation summaries
- **AND** it SHALL preserve backend ACL and worldline filtering.

### Requirement: Invocation detail shows safe prompt snapshot evidence
The system SHALL allow admins to inspect invocation detail and prompt snapshot evidence through existing backend routes.

#### Scenario: Admin inspects prompt snapshots
- **GIVEN** an invocation has prompt snapshot records
- **WHEN** the admin selects the invocation
- **THEN** the UI SHALL render snapshot checksums, visibility, redaction, and safe evidence fields
- **AND** resolved secrets, storage URIs, filesystem paths, bytes, base64 payloads, raw prompts, and raw outputs SHALL be redacted where required by backend/API contracts.

### Requirement: Tag and redaction actions use existing invocation APIs
The system SHALL let admins create/delete invocation tags and request redaction through existing invocation endpoints.

#### Scenario: Admin redacts an invocation
- **GIVEN** an invocation is eligible for redaction
- **WHEN** the admin submits a redaction action
- **THEN** the existing backend redaction endpoint SHALL process the request
- **AND** the Web layer SHALL not perform ledger mutation outside approved APIs.

### Requirement: Ledger browser preserves member and reader boundaries
The system SHALL keep raw prompt/output inspection restricted to authorized admin contexts and SHALL not add reader/member exposure paths.

#### Scenario: Non-admin actor attempts ledger access
- **GIVEN** an actor lacks invocation ledger authority
- **WHEN** they attempt to access the ledger browser or same-origin proxy
- **THEN** the request SHALL be denied by existing guard/proxy/API checks
- **AND** prompt snapshot evidence SHALL not be disclosed.

## Non-goals

- This spec does not define reader/member raw prompt exposure.
- This spec does not define an external tracing exporter.
- This spec does not change invocation ledger persistence or redaction semantics.
- This spec does not introduce provider execution changes.
