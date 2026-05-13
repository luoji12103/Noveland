## ADDED Requirements

### Requirement: Promise and foreshadowing tracker records unresolved hooks
The system SHALL track promises, foreshadowing, unresolved mysteries, agreements, and flags with participants, status, evidence, and reveal or resolution conditions.

#### Scenario: Query unresolved hooks
- **GIVEN** a worldline has unresolved hooks
- **WHEN** GM, narrative, or admin diagnostics request hook context
- **THEN** the system SHALL return active hooks with evidence references
- **AND** it SHALL filter hidden hooks by ACL.

### Requirement: Plot threads model story lines
The system SHALL model personal, organization, daily, main, and hidden plot threads with status, participants, stakes, next beats, and related events.

#### Scenario: Plot thread update
- **GIVEN** a plot thread advances
- **WHEN** the update is persisted
- **THEN** the system SHALL record status and evidence
- **AND** it SHALL validate same worldline participants and related records.

### Requirement: Route affinity is distinct from simple relationship values
The system SHALL track route progression, route flags, milestones, eligibility, and ending candidates separately from general relationship edges.

#### Scenario: Route milestone check
- **GIVEN** a player has made choices and relationship state has changed
- **WHEN** route eligibility is evaluated
- **THEN** the system SHALL return satisfied and unsatisfied route conditions
- **AND** it SHALL not infer route state solely from affection.

### Requirement: Event conditions explain trigger readiness
The system SHALL express event trigger conditions for time, place, relationship, faction state, hooks, secrets, player choices, and worldline flags.

#### Scenario: Trigger dry run
- **GIVEN** an event condition set exists
- **WHEN** a dry run is requested
- **THEN** the system SHALL explain which conditions pass or fail
- **AND** it SHALL not mutate world state.

### Requirement: Scene beat composer structures narrative input
The system SHALL convert eligible events into structured scene beats with setup, participants, dialogue goals, choices, aftermath, and presentation hints.

#### Scenario: Compose scene beat draft input
- **GIVEN** an event is eligible for narrative drafting
- **WHEN** scene beat composition runs
- **THEN** it SHALL produce structured beat data
- **AND** provider-backed narrative generation, if used later, SHALL still go through invocation ledger boundaries.

### Requirement: Knowledge and secret systems prevent omniscient context
The system SHALL track character facts, secrets, guesses, mistaken beliefs, holders, reveal conditions, and information-flow evidence.

#### Scenario: Agent observation filtering
- **GIVEN** a character does not know a secret
- **WHEN** runtime builds that character's observation context
- **THEN** the secret SHALL NOT be included
- **AND** diagnostics SHALL be able to report the reason.

### Requirement: Emotional state and relationship decay are explicit
The system SHALL track short-term emotional state and relationship decay/repair rules with event evidence.

#### Scenario: Relationship repair
- **GIVEN** a character apologizes or keeps a promise
- **WHEN** repair rules apply
- **THEN** relationship and emotion state SHALL update explicitly
- **AND** the change SHALL be auditable.
