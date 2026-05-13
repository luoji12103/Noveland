# Multimodal Pipeline Specification

## Purpose

This spec captures current Phase 7-13 multimodal behavior: speech and voice profiles, strict-worldline visual bindings, conversation turn presentation, admin-only asset generation proposals, multimodal diagnostics, and the sample-world regression fixture.

## Requirements

### Requirement: Speech and voice profile flows use media and provider boundaries
The system SHALL manage voice profiles, agent voice bindings, speech transcripts, style mappings, TTS, and STT through speech services and provider execution.

#### Scenario: TTS output attachment
- **GIVEN** a TTS request is made for a conversation turn
- **WHEN** speech synthesis completes
- **THEN** the system SHALL create invocation evidence, media job, audio media asset/object, and an optional turn media reference
- **AND** it SHALL NOT mutate turn text.

### Requirement: STT creates transcripts without automatic memory writes
The system SHALL create speech transcript records for STT output and SHALL NOT automatically write STT transcripts into long-term memory or mutate turn input/output text.

#### Scenario: Audio transcription
- **GIVEN** an admin transcribes a source audio asset for a conversation turn
- **WHEN** STT succeeds
- **THEN** a speech transcript SHALL be created and optionally linked to turn presentation
- **AND** no memory write job SHALL be automatically enqueued.

### Requirement: Visual bindings are strict-worldline records
The system SHALL store character sprite sets, sprite variants, and scene background profiles with non-null worldline identifiers and references to existing media assets.

#### Scenario: Sprite variant creation
- **GIVEN** an admin creates a sprite variant
- **WHEN** the referenced media asset belongs to another world or worldline
- **THEN** the visual service SHALL reject the variant.

### Requirement: Sprite and background resolution is deterministic
The system SHALL resolve sprites by exact expression/pose/outfit and mood tags, then neutral fallback, then default fallback, and SHALL resolve backgrounds by scene/location/time/weather with default fallback.

#### Scenario: Sprite fallback
- **GIVEN** no exact sprite variant matches the requested expression
- **WHEN** neutral and default variants exist
- **THEN** the resolver SHALL return the deterministic fallback
- **AND** it SHALL return an actionable error if no usable fallback exists.

### Requirement: Conversation turn presentation stores structured multimodal references
The system SHALL use `conversation_turn_presentations` as the canonical backend record for turn emotion, sprite, voice, background, composite scene, TTS audio, transcript, render state, and safe presentation metadata.

#### Scenario: Render visual for a turn
- **GIVEN** a presentation render request has resolvable sprite and background assets
- **WHEN** visual rendering completes
- **THEN** the system SHALL update the turn presentation with sprite/background/composite references
- **AND** it SHALL attach resulting media through media references.

### Requirement: Asset generation is preview plus admin apply
The system SHALL keep asset generation as proposal and admin apply only: preview persists proposals without provider calls, and apply creates queued media jobs without executing providers.

#### Scenario: Apply selected proposals
- **GIVEN** an admin has reviewed asset generation proposals
- **WHEN** they apply selected proposals
- **THEN** selected proposals SHALL create media jobs
- **AND** unselected or dismissed proposals SHALL remain unapplied.

### Requirement: Multimodal diagnostics reuse existing eval records
The system SHALL run multimodal diagnostics through a focused eval service and persist eval evidence using existing `long_run_eval_runs` records.

#### Scenario: Diagnostics pass sample world
- **GIVEN** the multimodal sample-world fixture exists
- **WHEN** diagnostics are run
- **THEN** provider secret checks, invocation coverage, media object integrity, sprite defaults, voice bindings, presentation references, transcript memory isolation, event payload leak checks, and cost/job aggregation SHALL pass.

## Non-goals

- This spec does not define Web visual or audio playback UI.
- This spec does not define daemon-driven asset generation.
- This spec does not define public reader media delivery.
- This spec does not define streaming voice, image, or conversation flows.
- This spec does not define cross-worldline visual inheritance.
