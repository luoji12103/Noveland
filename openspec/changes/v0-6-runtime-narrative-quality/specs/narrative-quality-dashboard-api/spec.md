# Narrative Quality Dashboard/API

## Capability

Expose API-first quality metrics, blockers, and repair recommendations to admins. Web dashboard implementation is deferred until backend API contracts are stable. This capability belongs to v0.6 Runtime Narrative Quality and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Narrative Quality Dashboard/API provides API-first diagnostics
The system SHALL provide Narrative Quality Dashboard/API capability for Quality API, dashboard-ready DTOs, and diagnostic summaries while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Narrative Quality Dashboard/API
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support API-first diagnostics
- **And** the workflow SHALL reuse multimodal evals, runtime diagnostics, admin API patterns rather than creating a parallel subsystem.

### Requirement: Narrative Quality Dashboard/API uses the narrative quality boundary
The system SHALL expose new v0.6 narrative quality APIs through `backend/services/api/src/noveland/services/api/narrative_quality.py` and service code under `backend/packages/narrative_quality/`.

#### Scenario: New narrative quality endpoint is added
- **Given** a v0.6 implementation adds quality metrics, blockers, or repair recommendation endpoints
- **When** the route is registered
- **Then** it SHALL be registered through the narrative quality router at app-level
- **And** it SHALL NOT be added as a broad new route to `worlds.py`.

### Requirement: Web dashboard is deferred
The system SHALL NOT require Web dashboard routes, components, or e2e scenarios for initial v0.6 backend diagnostic phases.

#### Scenario: Backend diagnostic phase needs UI work
- **Given** a v0.6 backend diagnostic phase is in progress
- **When** completing the phase would require Web dashboard implementation
- **Then** implementation SHALL stop for review
- **And** the backend phase SHALL remain API-first until a later approved Web phase starts.

### Requirement: Narrative Quality Dashboard/API preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Narrative Quality Dashboard/API, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Narrative Quality Dashboard/API reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Narrative Quality Dashboard/API has explicit acceptance evidence
The system SHALL provide focused validation for Narrative Quality Dashboard/API and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Narrative Quality Dashboard/API is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Public quality dashboard
- Initial Web dashboard routes, components, or e2e scenarios
- Broad new `worlds.py` routes
- Changing diagnostics semantics without tests
