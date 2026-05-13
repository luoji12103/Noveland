# Narrative Quality Dashboard/API

## Capability

Expose quality metrics, blockers, and repair recommendations to admins. This capability belongs to v0.6 Runtime Narrative Quality and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Narrative Quality Dashboard/API provides the planned workflow
The system SHALL provide Narrative Quality Dashboard/API capability for Quality API, Dashboard-ready DTOs, Diagnostic summaries while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Narrative Quality Dashboard/API
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse multimodal evals, runtime diagnostics, admin API patterns rather than creating a parallel subsystem.

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
- Changing diagnostics semantics without tests
