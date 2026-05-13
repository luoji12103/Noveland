# Conversation Playback UI

## Capability

Render image, sprite, background, voice, subtitles, and turn presentation playback. This capability belongs to v0.8 Public Experience & Ecosystem and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Conversation Playback UI provides the planned workflow
The system SHALL provide Conversation Playback UI capability for Playback UI, Turn presentation rendering, Audio playback while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Conversation Playback UI
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse conversation presentations, media delivery, speech assets rather than creating a parallel subsystem.

### Requirement: Conversation Playback UI preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Conversation Playback UI, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Conversation Playback UI reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Conversation Playback UI has explicit acceptance evidence
The system SHALL provide focused validation for Conversation Playback UI and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Conversation Playback UI is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Editing presentation state in reader UI
