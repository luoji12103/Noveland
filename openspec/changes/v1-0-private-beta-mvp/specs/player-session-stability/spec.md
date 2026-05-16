# Player Session Stability

## ADDED Requirements

### Requirement: Player sessions resume safely
The system SHALL restore current player conversation, worldline, scene, presentation, and playback state after interruption.

#### Scenario: Player returns after closing browser
- **Given** a player has an active conversation in an allowed worldline
- **When** they return after closing the browser
- **Then** the system SHALL restore the current conversation and scene state
- **And** it SHALL validate world, worldline, player, and membership scope.

### Requirement: Missing media has safe fallback
The system SHALL show safe fallback states when image, sprite, background, audio, or presentation data is missing or unavailable.

#### Scenario: Audio asset unavailable
- **Given** a conversation turn references unavailable audio
- **When** playback resumes
- **Then** the player SHALL see dialogue text and a safe unavailable-audio state
- **And** the response SHALL NOT expose storage paths, raw object metadata, bytes, or base64.

### Requirement: Player errors are actionable without internals
The system SHALL return player-safe error states for provider, media, memory, or playback failures.

#### Scenario: Provider generation fails
- **Given** a provider call fails during player interaction
- **When** the player UI reports the issue
- **Then** it SHALL show a safe recovery message
- **And** admin-only ledger or provider evidence SHALL remain hidden from the player.

## Non-goals

- Offline mode.
- Multiplayer synchronization.
- Raw event payload display.
