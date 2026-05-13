# Public Launch Gate

## Capability

Define public launch readiness checklist separate from internal production readiness. This capability belongs to v0.8 Public Experience & Ecosystem and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Public Launch Gate provides the planned workflow
The system SHALL provide Public Launch Gate capability for Public launch checklist, Security/privacy signoff, Moderation signoff while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Public Launch Gate
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse production readiness gate, BetaChecklistRun, LongRunEvalRun, diagnostics rather than creating a parallel subsystem.

### Requirement: Public Launch Gate preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Public Launch Gate, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Public Launch Gate reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Public Launch Gate has explicit acceptance evidence
The system SHALL provide focused validation for Public Launch Gate and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Public Launch Gate is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Skipping v0.7 production readiness
- Automatic launch on passing tests
