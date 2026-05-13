# Speech Admin Console

## Capability

Manage voice profiles, agent bindings, style mappings, transcripts, and TTS/STT test actions. This capability belongs to v0.4 Operator/Admin UX and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Speech Admin Console provides the planned workflow
The system SHALL provide Speech Admin Console capability for Voice profile list/detail, Agent voice binding editor, Style mapping editor, Transcript browser, TTS/STT test action while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Speech Admin Console
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse SpeechService, VoiceProfileService, SpeechTranscriptService, SpeechStyleMappingService rather than creating a parallel subsystem.

### Requirement: Speech Admin Console preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Speech Admin Console, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Speech Admin Console reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Speech Admin Console has explicit acceptance evidence
The system SHALL provide focused validation for Speech Admin Console and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Speech Admin Console is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Realtime voice
- Streaming
- Local voice server deployment
