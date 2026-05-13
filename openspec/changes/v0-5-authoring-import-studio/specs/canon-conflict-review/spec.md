# Canon Conflict Review

## Capability

Identify conflicting facts, duplicate characters, relationship contradictions, timeline conflicts, and OOC risk. This capability belongs to v0.5 Authoring & Import Studio and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Canon Conflict Review provides the planned workflow
The system SHALL provide Canon Conflict Review capability for Conflict reports, Duplicate detection, Admin resolution, Apply decisions while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Canon Conflict Review
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse import candidates, world events, agent/profile records, diagnostics patterns rather than creating a parallel subsystem.

### Requirement: Canon Conflict Review preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Canon Conflict Review, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Canon Conflict Review reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Canon Conflict Review has explicit acceptance evidence
The system SHALL provide focused validation for Canon Conflict Review and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Canon Conflict Review is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Automatic conflict resolution
