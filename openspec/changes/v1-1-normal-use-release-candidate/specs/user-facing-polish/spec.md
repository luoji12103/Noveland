# User-facing Polish

## ADDED Requirements

### Requirement: Key player flows have polished loading and error states
The system SHALL provide clear loading, empty, error, and fallback states for onboarding, playback, scene view, feedback, and session resume.

#### Scenario: Scene media is unavailable
- **Given** a scene view cannot load expected media
- **When** the player opens the scene
- **Then** the UI SHALL show dialogue and a safe visual fallback
- **And** it SHALL NOT expose storage paths, raw object metadata, or admin diagnostics.

### Requirement: Player surfaces support mobile basics and accessibility
The system SHALL maintain basic responsive behavior and accessibility expectations for key player surfaces.

#### Scenario: Player opens playback on mobile viewport
- **Given** a player uses a narrow viewport
- **When** playback renders
- **Then** dialogue, controls, media, loading, and error states SHALL remain readable and operable.

### Requirement: UI implementation follows product design context
The system SHALL use the Noveland product UI context and `impeccable` workflow before implementing v1.1 user-facing UI polish.

#### Scenario: UI polish phase begins
- **Given** Phase 7 implementation is requested
- **When** frontend files will be edited
- **Then** the implementer SHALL load and follow `impeccable` guidance before mutation.

## Non-goals

- Marketing redesign.
- Full game engine.
- Decorative hero pages.
