## ADDED Requirements

### Requirement: Character presence tracks visible and offscreen location
The system SHALL track character current location, visibility, offscreen state, and encounter eligibility in a worldline-scoped form.

#### Scenario: Presence query
- **GIVEN** a character has presence state
- **WHEN** runtime context is requested for a scene
- **THEN** the system SHALL return only same-worldline eligible characters
- **AND** hidden/offscreen state SHALL be filtered according to ACL.

### Requirement: Daily life scheduler proposes routine activity
The system SHALL resolve character routines into candidate daily-life activity using calendar and schedule state.

#### Scenario: Routine event candidate
- **GIVEN** a character has a schedule for the current world time
- **WHEN** the scheduler evaluates daily activity
- **THEN** it SHALL produce a candidate activity or a diagnostic reason for no action
- **AND** it SHALL NOT directly call providers.

### Requirement: Offscreen event queue stores proposed activity before commitment
The system SHALL store offscreen event candidates with participants, location, reason, priority, and current status before appending committed world events.

#### Scenario: Review pending offscreen event
- **GIVEN** runtime creates an offscreen event candidate
- **WHEN** an admin reviews the queue
- **THEN** the candidate SHALL include evidence and affected records
- **AND** it SHALL not have polluted `world_events.payload` with prompts, outputs, storage paths, or secrets.

### Requirement: Event importance ranks narrative weight
The system SHALL classify event candidates and committed events by daily, relationship, organization, route, and main-plot importance.

#### Scenario: Importance filter
- **GIVEN** event candidates have importance labels
- **WHEN** runtime or narrative services request high-impact events
- **THEN** the system SHALL filter by importance without parsing free-form text.

### Requirement: GM agenda plans near-term world pressure
The system SHALL persist GM agenda state for near-term story goals, character hooks, organization plans, and world pressure.

#### Scenario: Agenda inspection
- **GIVEN** a GM agenda exists for a worldline
- **WHEN** an admin requests agenda state
- **THEN** the system SHALL return active goals and blockers
- **AND** member/reader routes SHALL NOT expose hidden agenda details.

### Requirement: Event resolution is deterministic and replay-compatible
The system SHALL resolve approved offscreen events using deterministic inputs including character state, relationships, faction progress, player history, and explicit random seed where needed.

#### Scenario: Replay event resolution
- **GIVEN** the same worldline state and event proposal inputs
- **WHEN** resolution runs twice
- **THEN** it SHALL produce the same outcome and event evidence.
