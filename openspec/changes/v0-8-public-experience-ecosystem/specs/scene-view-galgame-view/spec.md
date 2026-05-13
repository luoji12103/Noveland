# Scene View / Galgame View

## Capability

Provide a basic galgame reading surface with scene background, sprites, dialogue, audio, and basic transitions. This capability belongs to v0.8 Public Experience & Ecosystem and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Scene View / Galgame View provides the planned workflow
The system SHALL provide Scene View / Galgame View capability for Scene background, Sprites, Dialogue, Audio, Basic transitions while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Scene View / Galgame View
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse visual resolver outputs, conversation presentations, reader media delivery rather than creating a parallel subsystem.

### Requirement: Scene View / Galgame View preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Scene View / Galgame View, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Scene View / Galgame View reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Scene View / Galgame View has explicit acceptance evidence
The system SHALL provide focused validation for Scene View / Galgame View and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Scene View / Galgame View is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Full game engine
- Streaming rendering
