# Character & Relationship Extractor Specification

## Purpose

This spec captures current v0.5 deterministic character and relationship extraction behavior: character, alias, faction, identity, relationship, and emotional-baseline candidates represented as traceable proposals.

## Requirements

### Requirement: Character extraction is proposal-first
The system SHALL convert source fragments and optionally existing dialogue proposals into character and relationship proposals.

#### Scenario: Character sheet is extracted
- **GIVEN** a character source fragment contains names, aliases, faction, identity, relationship, and emotion lines
- **WHEN** the deterministic extractor runs
- **THEN** it SHALL create reviewable proposals for detected candidates
- **AND** it SHALL NOT create or mutate canonical agent records directly.

### Requirement: Dialogue speaker proposals can seed characters
The system SHALL optionally inspect dialogue proposals in the same import run to create speaker candidate proposals.

#### Scenario: Dialogue speaker extraction is enabled
- **GIVEN** an import run contains dialogue proposals with speaker metadata
- **WHEN** character extraction runs with dialogue proposal inclusion enabled
- **THEN** speaker candidates SHALL be deduplicated into character proposals
- **AND** every candidate SHALL remain scoped to the run worldline.

### Requirement: Character extraction records summary counts
The system SHALL update import run summary JSON with extractor mode, inclusion mode, provider execution status, and candidate counts.

#### Scenario: Character extraction completes
- **GIVEN** a character extraction request succeeds
- **WHEN** the result is returned
- **THEN** it SHALL include character, relationship, alias, faction, identity, and emotional baseline counts
- **AND** `provider_execution` SHALL be `false`.

### Requirement: Character extraction preserves source traceability
The system SHALL create source traceability for fragment-backed proposals.

#### Scenario: Proposal is created from a fragment
- **GIVEN** a candidate was extracted from a source fragment
- **WHEN** the proposal is persisted
- **THEN** source traceability SHALL link the source fragment to the proposal.

## Non-goals

- This spec does not define automatic relationship graph mutation.
- This spec does not define provider-backed character extraction.
- This spec does not define public reader exposure of candidate identities.
