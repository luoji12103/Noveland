# Beta Feedback System

## ADDED Requirements

### Requirement: Testers can submit contextual feedback
The system SHALL allow private beta testers to report scene, dialogue, character, voice, image, playback, and interaction issues.

#### Scenario: Player reports a turn issue
- **Given** a player is viewing a conversation turn
- **When** they submit feedback
- **Then** the system SHALL create a feedback record linked to safe refs for world, worldline, conversation, turn, presentation, and optional media
- **And** it SHALL NOT store raw prompts, raw outputs, storage paths, bytes, base64, or resolved secrets.

### Requirement: Admins can triage feedback
The system SHALL provide an admin triage lifecycle for beta feedback.

#### Scenario: Admin marks feedback triaged
- **Given** a feedback record exists
- **When** an admin updates its triage status
- **Then** the system SHALL persist status, safe notes, and related evidence refs
- **And** reporter private data SHALL remain protected.

### Requirement: Feedback can link to repair proposals
The system SHALL allow feedback to be associated with reviewable repair proposals without directly mutating world state.

#### Scenario: Feedback suggests wrong sprite
- **Given** feedback identifies a wrong expression or sprite
- **When** an admin creates a repair proposal
- **Then** the proposal SHALL be reviewable before apply
- **And** the feedback SHALL remain auditable.

## Non-goals

- Public forum.
- Automatic punishment or moderation action.
- Unreviewed repair apply.
