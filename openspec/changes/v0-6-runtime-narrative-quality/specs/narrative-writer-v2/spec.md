# Narrative Writer v2

## Capability

Generate chapters from world events and conversation turns with worldline, visibility, and reader-safe filtering. This capability belongs to v0.6 Runtime Narrative Quality and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Narrative Writer v2 provides the planned workflow
The system SHALL provide Narrative Writer v2 capability for Narrative generation v2, Visibility filter, Reader-safe output while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Narrative Writer v2
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse narrative services, events, invocation ledger, media references rather than creating a parallel subsystem.

### Requirement: Narrative Writer v2 preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Narrative Writer v2, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Narrative Writer v2 reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Narrative Writer v2 has explicit acceptance evidence
The system SHALL provide focused validation for Narrative Writer v2 and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Narrative Writer v2 is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Narrative artifacts as media storage
- Raw prompt/output in world_events.payload
