## ADDED Requirements

### Requirement: Living-world dashboard summarizes operational story state
The system SHALL provide an admin-oriented dashboard view of characters, locations, organizations, queued events, worldlines, hooks, pressure, diagnostics, and multimodal asset readiness.

#### Scenario: Admin reviews world state
- **GIVEN** a living world has active characters, events, branches, and diagnostics
- **WHEN** an admin opens the dashboard
- **THEN** the system SHALL summarize current story operation state
- **AND** it SHALL not expose hidden provider secrets, raw prompts, storage paths, or reader-restricted records.

### Requirement: Player story journal separates public narrative and player-private history
The system SHALL provide a player-facing journal for choices, relationship changes, recent events, invitations, and known hooks according to player knowledge.

#### Scenario: Player reads journal
- **GIVEN** a player has participated in a worldline
- **WHEN** they read their journal
- **THEN** the system SHALL show only entries visible to that player
- **AND** hidden admin evidence and unknown secrets SHALL be omitted.

### Requirement: In-world notifications and interventions create structured events
The system SHALL represent notifications, invitations, rumors, promises, travel, observation, replies, and player interventions as structured records linked to world events.

#### Scenario: Player intervention
- **GIVEN** a player chooses to intervene in an active event
- **WHEN** the intervention is saved
- **THEN** the system SHALL create a structured choice or event record
- **AND** consequence handling SHALL remain explicit and auditable.

### Requirement: GM safety and narrative continuity checks review drafts
The system SHALL check GM and narrative drafts for style drift, continuity conflicts, time contradictions, out-of-character behavior, knowledge leaks, and relationship jumps.

#### Scenario: Continuity blocker
- **GIVEN** a narrative draft contradicts current worldline state
- **WHEN** continuity review runs
- **THEN** the system SHALL report a blocker or warning with evidence references
- **AND** it SHALL not publish the draft automatically.

### Requirement: Route and ending planning models candidate outcomes
The system SHALL support character routes, hidden routes, normal endings, bad endings, epilogues, milestones, and ending candidates.

#### Scenario: Ending candidate review
- **GIVEN** a route has satisfied milestones
- **WHEN** ending candidates are requested
- **THEN** the system SHALL return eligible endings with unmet blockers and evidence references.

### Requirement: Long-run simulation evaluation measures living-world quality
The system SHALL run multi-day or multi-week simulations to measure activity, event density, consistency, branch isolation, narrative drift, and diagnostics blockers.

#### Scenario: Seven-day simulation eval
- **GIVEN** a sample living world is configured
- **WHEN** a seven-day eval run completes
- **THEN** the system SHALL report metrics, blockers, recommendations, and evidence using existing eval/release records.

### Requirement: Authoring toolchain imports structured templates
The system SHALL support authoring workflows for source-work notes, character templates, event templates, route templates, and sequel-ready world setup.

#### Scenario: Template validation
- **GIVEN** an author imports a structured world template
- **WHEN** validation runs
- **THEN** the system SHALL report valid records and blockers
- **AND** it SHALL not create partial world state unless explicitly applied.

### Requirement: Beta release profile reuses existing evidence framework
The system SHALL define a living-world beta release profile using existing checklist, eval, diagnostics, backup, permission, and regression evidence.

#### Scenario: Beta readiness review
- **GIVEN** a candidate beta world exists
- **WHEN** beta readiness is evaluated
- **THEN** the system SHALL aggregate evidence from existing release/eval frameworks
- **AND** it SHALL not create a duplicate release system.
