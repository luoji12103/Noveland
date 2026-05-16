# Content Safety & Moderation Hardening

## ADDED Requirements

### Requirement: Player-visible content safety is reviewable
The system SHALL support review of player-visible content and character output safety with safe evidence refs.

#### Scenario: Unsafe output is flagged
- **Given** a character output violates an accepted safety policy
- **When** safety review runs
- **Then** the system SHALL create a safe finding or report reference
- **And** it SHALL NOT expose raw prompts or hidden admin evidence to players.

### Requirement: Takedown hides content and media
The system SHALL ensure applied takedown or disable actions hide affected reader/player-visible content and media.

#### Scenario: Content is taken down
- **Given** a moderator applies a takedown action
- **When** a player requests the affected content
- **Then** the content and associated media SHALL be hidden or blocked
- **And** moderation evidence SHALL remain admin-scoped.

### Requirement: Reporter privacy is protected
The system SHALL protect reporter identity and private data in moderation and safety workflows.

#### Scenario: Reader views moderated content state
- **Given** a report exists
- **When** a reader/player requests content status
- **Then** they SHALL NOT receive reporter private data or admin-only incident details.

## Non-goals

- Automatic punitive action without policy.
- Public moderator UI.
- Duplicate moderation framework.
