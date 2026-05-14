# Admin UX Foundation

## Capability

Unify admin layout, route guards, shared states, API client conventions, and table/detail/action patterns. This capability belongs to v0.4 Operator/Admin UX and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Admin UX Foundation provides the planned workflow
The system SHALL provide Admin UX Foundation capability for Admin shell conventions, Shared loading, error, and empty states, Admin route guard pattern, Admin API client conventions, Shared table, detail, and action patterns while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Admin UX Foundation
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse Next.js app routes, existing auth proxy/client patterns, workspace shell components rather than creating a parallel subsystem.

### Requirement: Admin UX Foundation preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Admin UX Foundation, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Admin UX Foundation reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Admin UX Foundation has explicit acceptance evidence
The system SHALL provide focused validation for Admin UX Foundation and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Admin UX Foundation is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Concrete provider/media/speech/visual business UI
- Backend business logic changes
