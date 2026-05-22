# content-safety-moderation-hardening Specification

## Purpose
This spec captures the current v1.1 content safety and moderation hardening on `main`. It covers safe review of player-visible content, explicit beta feedback escalation to moderation, reporter privacy, admin-scoped evidence, and takedown/disable visibility behavior without exposing raw prompts or private incident data.
## Requirements
### Requirement: Player-visible content safety is reviewable
The system SHALL support review of player-visible content and character output safety with safe evidence refs.

#### Scenario: Unsafe output is flagged
- **Given** a character output violates an accepted safety policy
- **When** safety review runs
- **Then** the system SHALL create a safe finding or report reference
- **And** it SHALL NOT expose raw prompts or hidden admin evidence to players.

### Requirement: Safety workflows integrate feedback and privacy boundaries
The system SHALL keep moderation as the safety/action owner while allowing beta feedback to escalate to moderation when a report involves safety, abuse, or player-visible harm. Player privacy records SHALL remain the owner for player data export or deletion requests.

#### Scenario: Feedback escalates to moderation
- **Given** a tester submits beta feedback that identifies a safety issue
- **When** an admin escalates it
- **Then** the system SHALL preserve reporter privacy, safe feedback refs, and moderation audit refs
- **And** it SHALL NOT expose reporter private data to other testers.

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
