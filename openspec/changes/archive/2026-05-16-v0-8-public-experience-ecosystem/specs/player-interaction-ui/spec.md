# Player Interaction UI

## Capability

Expose choices, interventions, journal, notifications, and route feedback to players using existing player records. This capability belongs to v0.8 Public Experience & Ecosystem and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Player UI reuses existing player records
The system SHALL use existing `PlayerChoiceRecord`, `PlayerJournalEntry`, `InWorldNotification`, and `PlayerInterventionRecord` semantics for player-facing interactions.

#### Scenario: Player submits a choice
- **Given** a player is authorized for a worldline
- **When** they submit a supported choice
- **Then** the system SHALL create or update the existing player choice record type
- **And** it SHALL NOT create a parallel player interaction framework.

### Requirement: Player feedback hides spoilers
The system SHALL filter route feedback, journal entries, and notifications by player knowledge and visibility.

#### Scenario: Route feedback contains hidden future state
- **Given** route diagnostics include future route milestones
- **When** a player views route feedback
- **Then** hidden milestone details SHALL be omitted or summarized safely
- **And** admin diagnostics SHALL remain unavailable.

### Requirement: Player UI preserves event payload boundaries
Player interactions SHALL NOT write storage paths, raw prompts, raw outputs, bytes, base64, or resolved secrets into `world_events.payload`.

#### Scenario: Intervention creates an event
- **Given** a player intervention is recorded
- **When** related world events are appended
- **Then** the event payload SHALL contain only safe references and summaries.

### Requirement: Player UI has explicit acceptance evidence
The implementation SHALL include UI, API, ACL, and leak tests.

#### Scenario: Phase acceptance
- **Given** Player Interaction UI implementation is complete
- **When** targeted tests and the full local gate run
- **Then** all checks SHALL pass before fast-forward merge.

## Non-goals

- New player record framework.
- Admin diagnostics in player UI.
- Direct provider-backed player action execution.
