# Galgame Visual Asset Mapping

## ADDED Requirements

### Requirement: Imported art maps into existing visual bindings
The system SHALL map imported character sprites, expression variants, backgrounds, and CG assets into existing media and visual records through preview/review/apply.

#### Scenario: Character expressions are mapped
- **Given** imported sprite assets exist for a character
- **When** visual mapping runs
- **Then** the system SHALL propose sprite set and neutral, happy, and sad variant bindings
- **And** it SHALL NOT overwrite existing visual bindings unless explicitly selected by an authorized operator.

### Requirement: Visual mapping preserves worldline isolation
The system SHALL validate world and worldline scope for every mapped media asset, sprite variant, background profile, and scene reference.

#### Scenario: Cross-worldline asset is selected
- **Given** a proposed visual binding references a media asset from another worldline
- **When** apply is requested
- **Then** the system SHALL reject the apply action
- **And** it SHALL return an actionable safe error.

### Requirement: Mapped assets are reader-safe only through approved delivery
The system SHALL expose mapped visual assets to reader/player surfaces only through reader-safe media descriptors and visibility policy checks.

#### Scenario: Hidden asset is mapped
- **Given** a hidden or developer-only asset exists in the source import
- **When** reader/player playback resolves scene media
- **Then** the hidden or developer-only asset SHALL be suppressed unless an internal/platform-admin path explicitly allows it.

## Non-goals

- New media storage system.
- New visual resolver.
- Automatic destructive remapping.
