# Player Session Stability Specification

## Purpose
This spec captures the current v1.0 player session stability contract on `main`. It covers server-owned player resume state, worldline and player isolation, safe restoration of current conversation and presentation pointers, and player-safe recovery states for missing media or provider failures.

## Requirements
### Requirement: Player sessions resume safely
The system SHALL restore current player conversation, worldline, scene, presentation, and playback state after interruption.

#### Scenario: Player returns after closing browser
- **Given** a player has an active conversation in an allowed worldline
- **When** they return after closing the browser
- **Then** the system SHALL restore the current conversation and scene state
- **And** it SHALL validate world, worldline, player, and membership scope.

### Requirement: Player sessions are isolated per tester
The system SHALL prevent one tester from reading or mutating another tester's private beta session state.

#### Scenario: Tester requests another tester's resume state
- **Given** a private beta player has a session in a worldline
- **When** another tester requests that session
- **Then** the system SHALL reject the request
- **And** it SHALL NOT reveal conversation, scene, presentation, media, or provider failure details for the other tester.

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
