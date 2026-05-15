# Memory Migration Pipeline

## Capability

Convert source content into fact, episodic, relationship, preference, and style memory proposals. This capability belongs to v0.5 Authoring & Import Studio and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Memory Migration Pipeline provides the planned workflow
The system SHALL provide Memory Migration Pipeline capability for Memory migration proposals, Preview/apply, Source traceability, Worldline scoping while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Memory Migration Pipeline
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse MemoryService, memory write jobs, and the Phase 1 import proposal workflow rather than creating a parallel subsystem.

### Requirement: Memory Migration Pipeline preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Memory Migration Pipeline, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Memory Migration Pipeline reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Memory Migration Pipeline has explicit acceptance evidence
The system SHALL provide focused validation for Memory Migration Pipeline and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Memory Migration Pipeline is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Direct memory backend SDK access
- Automatic memory writes outside apply
