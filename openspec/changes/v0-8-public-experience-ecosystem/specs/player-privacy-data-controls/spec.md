# Player Privacy & Data Controls

## Capability

Support export/delete requests, player profile visibility, and conversation data controls. This capability belongs to v0.8 Public Experience & Ecosystem and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Player Privacy & Data Controls provides the planned workflow
The system SHALL provide Player Privacy & Data Controls capability for Data export, Data deletion request, Privacy controls while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Player Privacy & Data Controls
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse auth/member records, conversation records, world events rather than creating a parallel subsystem.

### Requirement: Player Privacy & Data Controls preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Player Privacy & Data Controls, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Player Privacy & Data Controls reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Player Privacy & Data Controls has explicit acceptance evidence
The system SHALL provide focused validation for Player Privacy & Data Controls and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Player Privacy & Data Controls is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Deleting shared world history without governance
