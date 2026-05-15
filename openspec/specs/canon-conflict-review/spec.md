# Canon Conflict Review Specification

## Purpose

This spec captures current v0.5 deterministic canon conflict review behavior: import-run proposals are analyzed for duplicate, contradiction, uncertain-canon, and OOC-risk reports represented as traceable proposals.

## Requirements

### Requirement: Conflict review analyzes current import proposals
The system SHALL inspect proposals in a selected import run and included statuses to generate conflict report proposals.

#### Scenario: Duplicate candidates exist
- **GIVEN** an import run contains proposals with duplicate or overlapping candidate payloads
- **WHEN** conflict review runs
- **THEN** it SHALL create `canon_conflict_report` proposals
- **AND** original proposals SHALL remain unchanged unless separately reviewed.

### Requirement: Conflict review detects deterministic report categories
The system SHALL report duplicate, contradiction, uncertain, and OOC-risk candidates using deterministic review logic.

#### Scenario: Contradictory relationship payloads exist
- **GIVEN** two relationship proposals assert conflicting relationship values
- **WHEN** conflict review runs
- **THEN** it SHALL create a contradiction report proposal with safe evidence
- **AND** the report SHALL remain reviewable authoring data.

### Requirement: Conflict review has no automatic resolution
The system SHALL NOT automatically resolve, merge, reject, or apply conflicted proposals.

#### Scenario: Conflict report is created
- **GIVEN** conflict review creates a report proposal
- **WHEN** the result is returned
- **THEN** the report SHALL be a proposal for admin review
- **AND** no canonical state mutation SHALL occur.

### Requirement: Conflict review records summary counts
The system SHALL update import run summary JSON with review mode, provider execution status, and conflict category counts.

#### Scenario: Conflict review completes
- **GIVEN** a conflict review request succeeds
- **WHEN** the result is returned
- **THEN** it SHALL include created proposal, duplicate, contradiction, uncertain, and OOC-risk counts
- **AND** `provider_execution` SHALL be `false`.

## Non-goals

- This spec does not define automatic conflict resolution.
- This spec does not define semantic LLM-based canon judgment.
- This spec does not define direct mutation of agents, relationships, world events, or lore records.
