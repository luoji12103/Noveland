# Media System Specification

## Purpose

This spec captures current media kernel behavior, image generation/edit/composition, media object storage metadata, cataloging, lineage, and safe attachment rules.

## Requirements

### Requirement: Media assets and objects are the canonical binary media records
The system SHALL represent uploaded and generated image, audio, video, and document media through `media_assets` and `media_objects`.

#### Scenario: Media object creation
- **GIVEN** a service stores generated or uploaded media
- **WHEN** the media is persisted
- **THEN** it SHALL create a media asset and object metadata record
- **AND** it SHALL NOT store raw bytes or base64 in arbitrary JSON payloads.

### Requirement: Media jobs track planned and completed media work
The system SHALL use `media_jobs` to represent media generation, upload, composition, transcription, speech synthesis, and asset generation proposal outputs.

#### Scenario: Media job status update
- **GIVEN** a media job exists for image, audio, or orchestration work
- **WHEN** its status changes
- **THEN** the job record SHALL capture safe status metadata
- **AND** it SHALL NOT store provider secrets, raw prompts, raw outputs, bytes, or base64.

### Requirement: Media references attach assets to domain records
The system SHALL use `media_references` and related catalog records to attach media assets to turns, agents, scenes, events, narrative artifacts, and other domain targets.

#### Scenario: Conversation turn media attachment
- **GIVEN** a TTS audio asset, sprite, background, or composite image is associated with a conversation turn
- **WHEN** the attachment is persisted
- **THEN** the system SHALL write a media reference
- **AND** it SHALL preserve same-world and same-worldline validation.

### Requirement: Image provider flows use media and invocation records
The system SHALL route provider-backed image generation and editing through provider execution and SHALL store resulting files in media records.

#### Scenario: Provider-backed image generation
- **GIVEN** an admin requests image generation through the image API
- **WHEN** a configured provider succeeds
- **THEN** the system SHALL create invocation and prompt snapshot evidence
- **AND** it SHALL create output media job, asset, object, lineage, and safe response records.

### Requirement: Deterministic image composition reuses the image service
The system SHALL compose local deterministic image outputs through the existing image/composer service and SHALL not create a second composer for visual scene composition.

#### Scenario: Visual scene composition
- **GIVEN** a visual service composes multiple sprite/background inputs
- **WHEN** composition is requested
- **THEN** it SHALL reuse the Phase 6 deterministic composer through image/media services
- **AND** it SHALL create media job, asset, object, and input lineage records without a provider invocation unless provider execution is used.

### Requirement: Narrative artifacts are not media storage
The system SHALL NOT use `narrative_artifacts` as storage for binary media files.

#### Scenario: Publication references media
- **GIVEN** narrative content needs to refer to an image or audio asset
- **WHEN** the relationship is persisted
- **THEN** it SHALL use media reference or catalog metadata
- **AND** the narrative artifact SHALL NOT carry bytes, base64, or internal storage URIs as media storage.

## Non-goals

- This spec does not define public reader media delivery.
- This spec does not define Web image/audio preview UI.
- This spec does not define a second media framework.
- This spec does not define streaming media generation.
