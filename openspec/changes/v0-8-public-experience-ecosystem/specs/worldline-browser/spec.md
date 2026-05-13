# Worldline Browser

## Capability

Support branch viewing, rollback/switch review, and worldline comparison. This capability belongs to v0.8 Public Experience & Ecosystem and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Worldline Browser provides the planned workflow
The system SHALL provide Worldline Browser capability for Worldline tree/list, Branch compare, Switch/review UI while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Worldline Browser
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse worldline services, event snapshots, comparison APIs rather than creating a parallel subsystem.

### Requirement: Worldline Browser preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Worldline Browser, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Worldline Browser reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Worldline Browser has explicit acceptance evidence
The system SHALL provide focused validation for Worldline Browser and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Worldline Browser is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Unsafe destructive rollback without confirmation
