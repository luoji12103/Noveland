# Beta Feedback System

## ADDED Requirements

### Requirement: Beta feedback ownership is decided before implementation
The system SHALL complete a docs-only checkpoint before implementing beta feedback.
The checkpoint SHALL decide whether beta feedback extends moderation reports/incidents or uses a
dedicated beta feedback package/router.

#### Scenario: Feedback checkpoint runs
- **Given** v1.0 Phase 6 is selected for implementation
- **When** the checkpoint is written
- **Then** it SHALL define feedback record ownership, issue taxonomy, safe evidence refs, reporter privacy, and repair linkage
- **And** it SHALL stop implementation if feedback requires public forum or social features.

### Requirement: Testers can submit contextual feedback
The system SHALL allow private beta testers to report scene, dialogue, character, voice, image, playback, and interaction issues.

#### Scenario: Player reports a turn issue
- **Given** a player is viewing a conversation turn
- **When** they submit feedback
- **Then** the system SHALL create a feedback record linked to safe refs for world, worldline, conversation, turn, presentation, and optional media
- **And** it SHALL NOT store raw prompts, raw outputs, storage paths, bytes, base64, or resolved secrets.

### Requirement: Feedback supports beta issue taxonomy
The system SHALL represent beta feedback issue types for dialogue, persona, memory, sprite,
background, voice, playback, provider, quota, session recovery, and UX issues.

#### Scenario: Player reports a persona issue
- **Given** a player reports an out-of-character response
- **When** the feedback is stored
- **Then** the record SHALL preserve safe refs to the turn, conversation, worldline, and related persona/memory evidence where authorized
- **And** it SHALL NOT expose the underlying prompt snapshot or raw provider output.

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
