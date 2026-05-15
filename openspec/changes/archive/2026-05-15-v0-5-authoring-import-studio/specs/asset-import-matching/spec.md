# Asset Import & Matching

## Capability

Import sprites, variants, backgrounds, CGs, and voice references and match them to characters or scenes. This capability belongs to v0.5 Authoring & Import Studio and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Asset Import & Matching provides the planned workflow
The system SHALL provide Asset Import & Matching capability for Asset matching candidates, Character/scene binding proposals, Manual confirmation while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Asset Import & Matching
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse MediaService, VisualAssetService, Speech voice references, and the Phase 1 import proposal workflow rather than creating a parallel subsystem.

### Requirement: Asset Import & Matching preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Asset Import & Matching, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Asset Import & Matching reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Asset Import & Matching has explicit acceptance evidence
The system SHALL provide focused validation for Asset Import & Matching and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Asset Import & Matching is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Public media delivery
- Automatic visual binding apply without review
