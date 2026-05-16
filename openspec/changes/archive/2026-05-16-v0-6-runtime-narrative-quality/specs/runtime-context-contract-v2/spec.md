# Runtime Context Contract v2

## Capability

Distinguish agent, conversation, GM, narrative, and eval context contracts. This capability belongs to v0.6 Runtime Narrative Quality and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Runtime Context Contract v2 provides the planned workflow
The system SHALL provide Runtime Context Contract v2 capability for Context schemas, Visibility boundaries, Worldline scope, Prompt snapshot traceability while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Runtime Context Contract v2
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse Invocation ledger, observations, conversation services, memory services rather than creating a parallel subsystem.

### Requirement: Runtime Context Contract v2 preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Runtime Context Contract v2, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Runtime Context Contract v2 reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Runtime Context Contract v2 has explicit acceptance evidence
The system SHALL provide focused validation for Runtime Context Contract v2 and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Runtime Context Contract v2 is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- One generic prompt context for all call sites
