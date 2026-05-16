# Conversation Playback UI Specification

## Purpose

This spec captures the current v0.8 reader/player conversation playback UI on `main`. It covers read-only playback over safe turn presentation data, subtitles, reader-safe visual media, and optional audio through Reader Media Delivery.

## Requirements
### Requirement: Playback consumes safe presentation data
The system SHALL render playback from reader/member-safe conversation turn presentation DTOs and SHALL NOT fetch admin-only media, invocation, or prompt snapshot data.

#### Scenario: Playback renders a visible turn
- **Given** a conversation turn has a reader-visible presentation, sprite, background, and TTS media
- **When** a reader opens playback
- **Then** the UI SHALL render the turn using safe presentation and media descriptors
- **And** no admin evidence or storage internals SHALL appear in the page data.

### Requirement: Playback depends on Reader Media Delivery
The system SHALL use the Reader Media Delivery capability for audio and image access.

#### Scenario: Audio respects media visibility
- **Given** a TTS media asset is no longer reader-visible
- **When** playback tries to render the turn
- **Then** the UI SHALL show a safe missing-audio state
- **And** the media delivery endpoint SHALL not serve the hidden object.

### Requirement: Playback is read-only for presentation state
The reader playback UI SHALL NOT edit conversation turn presentation records.

#### Scenario: Reader cannot edit presentation
- **Given** a reader is viewing playback
- **When** they interact with playback controls
- **Then** the system SHALL only change local playback state
- **And** it SHALL NOT mutate canonical presentation records.

### Requirement: Playback has explicit acceptance evidence
The implementation SHALL include component, safe-data, and e2e smoke tests.

#### Scenario: Phase acceptance
- **Given** Conversation Playback UI implementation is complete
- **When** targeted tests and the full local gate run
- **Then** all checks SHALL pass before fast-forward merge.

## Non-goals

- Editing presentation state in reader UI.
- Exposing prompt snapshots or model invocation details.
- Streaming playback.
