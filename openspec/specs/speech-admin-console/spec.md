# Speech Admin Console Specification

## Purpose

This spec captures the current v0.4 world-scoped speech admin console on `main`. The console lets authorized admins inspect and manage voice profiles, agent voice bindings, style mappings, transcripts, and explicit TTS/STT test actions through existing speech APIs.

## Requirements

### Requirement: Speech admin manages voice profiles and bindings
The system SHALL provide a world-scoped Web admin page for voice profiles and agent voice bindings using existing speech service APIs.

#### Scenario: Admin binds an agent voice
- **GIVEN** an authorized world admin opens `/worlds/{worldId}/speech`
- **WHEN** they create or update an agent voice binding
- **THEN** the Web client SHALL call existing speech binding endpoints
- **AND** same-worldline validation SHALL remain a backend responsibility.

### Requirement: Speech admin manages style mappings
The system SHALL expose speech style mappings for provider/emotion selection through existing speech style mapping routes.

#### Scenario: Admin updates a style mapping
- **GIVEN** a provider and voice profile are configured
- **WHEN** the admin creates or updates an emotion style mapping
- **THEN** the system SHALL persist the mapping through the existing speech API
- **AND** it SHALL not add new provider adapter behavior.

### Requirement: Speech admin exposes transcript inspection
The system SHALL let admins inspect speech transcript records and safe transcript metadata.

#### Scenario: Admin reviews a transcript
- **GIVEN** STT has produced a transcript record
- **WHEN** the transcript browser displays it
- **THEN** transcript text and metadata SHALL come from existing transcript APIs
- **AND** the UI SHALL not imply automatic memory writes.

### Requirement: TTS and STT test actions are explicit
The system SHALL expose explicit TTS and STT admin actions using existing speech orchestration APIs.

#### Scenario: Admin runs a TTS test
- **GIVEN** a voice profile and provider path are available
- **WHEN** the admin submits a TTS test
- **THEN** speech synthesis SHALL run through existing backend speech/provider services
- **AND** response rendering SHALL not include raw audio bytes, storage paths, or resolved secrets.

## Non-goals

- This spec does not define realtime voice or streaming.
- This spec does not define local voice server deployment.
- This spec does not define automatic STT-to-memory writes.
- This spec does not change backend speech service semantics.
