# Visual Asset Admin Console Specification

## Purpose

This spec captures the current v0.4 world-scoped visual asset admin console on `main`. The console lets authorized admins manage strict-worldline sprite sets, variants, scene backgrounds, resolver previews, and compose-scene previews through existing visual and image APIs.

## Requirements

### Requirement: Visual admin manages strict-worldline sprite sets
The system SHALL provide a world-scoped Web admin page for character sprite sets and variants using existing visual APIs.

#### Scenario: Admin manages sprite variants
- **GIVEN** an authorized world admin opens `/worlds/{worldId}/visual`
- **WHEN** they create or inspect sprite sets and variants
- **THEN** records SHALL be sent to existing visual endpoints
- **AND** every visual binding SHALL retain a non-null worldline scope enforced by the backend.

### Requirement: Visual admin manages scene backgrounds
The system SHALL allow admins to create and inspect scene background profiles through existing visual background APIs.

#### Scenario: Admin configures a background
- **GIVEN** a background media asset exists in the same worldline
- **WHEN** the admin creates a scene background profile
- **THEN** the request SHALL reference the media asset by ID
- **AND** it SHALL not copy storage URIs or file paths into visual records.

### Requirement: Resolver previews use existing deterministic resolver APIs
The system SHALL let admins preview sprite and background resolution by calling existing resolver endpoints.

#### Scenario: Admin previews sprite fallback
- **GIVEN** sprite variants include exact, neutral, and default candidates
- **WHEN** the admin submits a resolve-sprite preview
- **THEN** the response SHALL show the backend-selected asset and fallback reason
- **AND** no random asset selection SHALL be introduced by the Web layer.

### Requirement: Compose-scene preview reuses existing image composition
The system SHALL submit compose-scene preview requests through existing visual/image service routes.

#### Scenario: Admin composes a scene
- **GIVEN** sprite and background assets are valid for the same worldline
- **WHEN** the admin submits a compose-scene preview
- **THEN** the backend deterministic composer SHALL own composition
- **AND** the Web layer SHALL not implement a second image composer.

## Non-goals

- This spec does not define automatic sprite or background generation.
- This spec does not define nullable worldline visual defaults.
- This spec does not define public reader visual delivery.
- This spec does not change backend visual resolver or image composition semantics.
