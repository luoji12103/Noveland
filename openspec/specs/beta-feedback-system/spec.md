# Beta Feedback System Specification

## Purpose
This spec captures the current v1.0 private beta feedback system on `main`. It covers dedicated reporter-private feedback records, contextual safe evidence refs, beta issue taxonomy, admin triage, and repair proposal linkage without turning feedback into a public forum or automatic mutation path.

## Requirements
### Requirement: Beta feedback has dedicated records
The system SHALL store private beta issue reports in dedicated beta feedback records rather than using moderation reports as the primary beta issue table.

#### Scenario: Feedback ownership is dedicated
- **Given** a private beta tester submits feedback
- **When** the report is persisted
- **Then** it SHALL be stored in `beta_feedback_reports`
- **And** moderation records SHALL only be used for later safety or abuse escalation when needed.

### Requirement: Testers can submit contextual feedback
The system SHALL allow private beta testers to report scene, dialogue, character, voice, image, playback, and interaction issues.

#### Scenario: Player reports a turn issue
- **Given** a player is viewing a conversation turn
- **When** they submit feedback
- **Then** the system SHALL create a feedback record linked to safe refs for world, worldline, conversation, turn, presentation, and optional media
- **And** it SHALL NOT store raw prompts, raw outputs, storage paths, bytes, base64, or resolved secrets.

### Requirement: Feedback supports beta issue taxonomy
The system SHALL represent beta feedback issue types for dialogue, persona, memory, sprite, background, voice, playback, provider, quota, session recovery, and UX issues.

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
