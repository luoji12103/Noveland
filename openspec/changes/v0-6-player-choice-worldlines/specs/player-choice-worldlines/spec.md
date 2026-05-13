## ADDED Requirements

### Requirement: Player actor model represents player identity in world state
The system SHALL represent a player as an in-world actor with identity, relationships, location, history, and visibility under a world.

#### Scenario: Player actor binding
- **GIVEN** a world member participates as a player
- **WHEN** the player actor profile is resolved
- **THEN** the system SHALL return the actor profile scoped to the world and worldline
- **AND** it SHALL enforce member visibility rules.

### Requirement: Player choices are structured event-backed records
The system SHALL persist player choices with choice key, prompt/context, selected option, affected actors, worldline, and event evidence.

#### Scenario: Choice persistence
- **GIVEN** a player selects a choice in a worldline
- **WHEN** the choice is saved
- **THEN** the system SHALL create a structured choice record
- **AND** it SHALL append or reference a typed world event without raw prompt or media payload leakage.

### Requirement: Consequence engine previews and applies explicit effects
The system SHALL preview and apply choice consequences for relationships, events, organization state, route eligibility, future flags, and memory summaries through explicit records.

#### Scenario: Consequence preview
- **GIVEN** a pending player choice
- **WHEN** consequence preview is requested
- **THEN** the system SHALL explain potential affected records
- **AND** it SHALL NOT mutate state until apply is requested by an authorized actor.

### Requirement: Worldlines can fork from snapshots or event positions
The system SHALL create branch worldlines from a snapshot or event sequence position while preserving parent lineage and fork metadata.

#### Scenario: Fork worldline
- **GIVEN** an authorized actor requests a fork from a valid snapshot
- **WHEN** the fork is created
- **THEN** the new worldline SHALL record parent worldline and fork position
- **AND** branch-specific state SHALL use the new worldline identifier.

### Requirement: Branch memory and multimodal state remain isolated
The system SHALL keep memory, relationship, event, visual, speech, media, presentation, and asset generation state isolated by worldline after a fork.

#### Scenario: Branch memory search
- **GIVEN** two branches diverge after a fork
- **WHEN** memory or multimodal context is queried for one branch
- **THEN** records from the other branch SHALL NOT be returned unless an explicit cross-branch comparison path is used.

### Requirement: Timeline comparison reads divergent state
The system SHALL provide admin comparison of fork point, divergent events, choices, relationships, faction state, and presentation-relevant records without mutating either branch.

#### Scenario: Compare branches
- **GIVEN** two related worldlines exist
- **WHEN** an admin requests timeline comparison
- **THEN** the system SHALL return fork metadata and state deltas
- **AND** it SHALL not create provider calls, media jobs, or memory writes.
