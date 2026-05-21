# Memory & Persona QA

## ADDED Requirements

### Requirement: Memory and persona QA ownership is decided before implementation
The system SHALL complete a docs-only checkpoint before implementing memory/persona QA.
The checkpoint SHALL decide whether QA uses existing narrative quality diagnostics/eval records,
authoring proposal evidence, or dedicated QA run records.

#### Scenario: QA checkpoint runs
- **Given** v1.0 Phase 5 is selected for implementation
- **When** the checkpoint is written
- **Then** it SHALL define where QA findings, safe evidence refs, and repair suggestions are represented
- **And** it SHALL stop implementation if the path would expose raw prompts or outputs to non-admin users.

### Requirement: QA detects memory and persona drift
The system SHALL provide admin diagnostics for memory contamination, persona drift, dialogue style drift, and worldline contamination.

#### Scenario: Persona drift is detected
- **Given** recent turns diverge from a character persona baseline
- **When** an admin runs memory/persona QA
- **Then** the system SHALL return a safe finding with evidence refs and suggested repair proposal types
- **And** it SHALL NOT mutate persona or memory directly.

### Requirement: QA evidence is worldline-aware
The system SHALL validate world and worldline scope for memory, persona, turn, invocation, and source evidence.

#### Scenario: Cross-worldline evidence is supplied
- **Given** a QA request references evidence from a different worldline
- **When** the diagnostic runs
- **Then** the system SHALL reject the request with a safe actionable error.

### Requirement: QA output is admin-scoped and redacted
The system SHALL keep detailed QA findings admin-scoped and redacted.

#### Scenario: Non-admin requests QA details
- **Given** a player or reader requests QA details
- **When** authorization is checked
- **Then** the system SHALL reject or redact the response
- **And** it SHALL NOT expose raw prompts, raw outputs, storage paths, or secrets.

## Non-goals

- Automatic destructive memory repair.
- Reader/player diagnostic access.
- Replacement memory framework.
