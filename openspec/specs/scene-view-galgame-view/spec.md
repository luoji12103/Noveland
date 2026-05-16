# Scene View / Galgame View Specification

## Purpose

This spec captures the current v0.8 reader/player scene view on `main`. It covers a basic galgame-style reading surface composed from conversation turn presentations and reader-safe media descriptors, with deterministic missing-asset fallback and accessibility constraints.

## Requirements
### Requirement: Scene view renders safe presentation records
The system SHALL render scene backgrounds, sprites, dialogue, and audio from conversation turn presentations and reader-safe media descriptors.

#### Scenario: Scene with two characters
- **Given** a turn presentation references visible sprite, background, composite, and TTS media
- **When** a reader opens the scene view
- **Then** the UI SHALL render the scene from safe DTOs
- **And** it SHALL NOT fetch admin visual/media records directly.

### Requirement: Scene view handles missing assets deterministically
The system SHALL show deterministic fallback states for missing background, sprite, or audio assets.

#### Scenario: Missing sprite asset
- **Given** a presentation references no usable sprite variant
- **When** the scene view renders
- **Then** it SHALL show a safe missing-sprite state
- **And** it SHALL NOT choose a random asset.

### Requirement: Scene view remains accessible and bounded
The UI SHALL be responsive, keyboard-usable, reduced-motion friendly, and avoid a custom game engine in the first implementation.

#### Scenario: Reduced motion user
- **Given** reduced motion is enabled
- **When** a scene transition occurs
- **Then** the UI SHALL avoid motion-heavy transitions.

### Requirement: Scene view has explicit acceptance evidence
The implementation SHALL include component, responsive, accessibility, and e2e tests.

#### Scenario: Phase acceptance
- **Given** Scene View implementation is complete
- **When** targeted tests and the full local gate run
- **Then** all checks SHALL pass before fast-forward merge.

## Non-goals

- Full game engine.
- Streaming rendering.
- Editing visual bindings from the reader scene.
