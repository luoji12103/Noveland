## ADDED Requirements

### Requirement: World bible captures sequel-world constraints
The system SHALL provide structured world bible records for source context, canon timeline, sequel boundaries, forbidden changes, location rules, and character rules.

#### Scenario: Admin records canon constraints
- **GIVEN** a world admin creates or updates world bible information
- **WHEN** the world bible is saved
- **THEN** the system SHALL persist structured constraints under the world
- **AND** future runtime or narrative flows SHALL be able to read those constraints without parsing free-form event payloads.

### Requirement: Continuity state distinguishes canon and expansion content
The system SHALL classify relevant world content as canon, post-canon, alternate, or original expansion.

#### Scenario: Continuity metadata on world change
- **GIVEN** a world state change records new story information
- **WHEN** the change is persisted
- **THEN** it SHALL carry continuity metadata
- **AND** the metadata SHALL be queryable for later narrative review.

### Requirement: Character profiles separate roster role from persona text
The system SHALL support structured character role, importance, canon status, speech style, goals, secrets, daily preferences, story function, and emotional baseline alongside existing agent persona text.

#### Scenario: Character profile lookup
- **GIVEN** an agent participates in a scene
- **WHEN** profile context is requested
- **THEN** the system SHALL return structured profile fields
- **AND** it SHALL preserve existing agent persona behavior.

### Requirement: Relationship graph records durable character relationships
The system SHALL store worldline-scoped relationship edges for affection, trust, hostility, intimacy, obligation, rivalry, debt, and related notes.

#### Scenario: Relationship update
- **GIVEN** two characters share a worldline
- **WHEN** a relationship edge is created or updated
- **THEN** the edge SHALL validate same world and worldline
- **AND** the change SHALL be auditable through typed state or event evidence.

### Requirement: Organization and membership records model factions
The system SHALL model organizations or factions and SHALL track character memberships with role, loyalty, influence, and visibility.

#### Scenario: Hidden membership
- **GIVEN** a character has a hidden organization membership
- **WHEN** a non-admin reads character context
- **THEN** the hidden membership SHALL NOT be exposed
- **AND** admin diagnostics SHALL still be able to inspect it.

### Requirement: Location graph extends scene semantics
The system SHALL support location hierarchy, adjacency, availability, opening rules, and narrative tags without replacing existing scenes.

#### Scenario: Adjacent location query
- **GIVEN** a scene is linked into the location graph
- **WHEN** available adjacent locations are requested
- **THEN** the system SHALL return only locations valid for the same worldline and current availability rules.
