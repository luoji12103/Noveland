# user-facing-polish Specification

## Purpose
This spec captures the current v1.1 user-facing polish on `main`. It covers loading, empty, error, degraded, quota, feedback, onboarding, resume, playback, scene, provider status, responsive, and accessibility improvements on existing surfaces, shaped by the Noveland product UI context and `impeccable`.
## Requirements
### Requirement: Key player flows have polished loading and error states
The system SHALL provide clear loading, empty, error, degraded, quota-exceeded, and fallback states for onboarding, playback, scene view, feedback, and session resume.

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

### Requirement: Admin normal-use surfaces communicate readiness clearly
The system SHALL improve setup/readiness, import/export, provider status, and feedback affordances only within the accepted polish scope.

#### Scenario: Provider is degraded
- **Given** an admin views provider status during normal-use polish
- **When** a provider is degraded or quota blocked
- **Then** the UI SHALL explain the state with safe status, action, and evidence refs
- **And** it SHALL NOT expose resolved secrets, raw prompts, raw outputs, or prompt snapshot internals.

### Requirement: UI implementation follows product design context
The system SHALL use the Noveland product UI context and `impeccable` workflow before implementing v1.1 user-facing UI polish.

#### Scenario: UI polish phase begins
- **Given** Phase 7 implementation is requested
- **When** frontend files will be edited
- **Then** the implementer SHALL load and follow `impeccable` guidance before mutation.
