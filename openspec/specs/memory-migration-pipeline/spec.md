# Memory Migration Pipeline Specification

## Purpose

This spec captures current v0.5 deterministic memory migration behavior: source fragments and eligible proposals are converted into reviewable fact, episodic, relationship, preference, and style memory proposals without memory writes.

## Requirements

### Requirement: Memory migration creates proposals, not memory writes
The system SHALL represent migrated memory candidates as authoring proposals and SHALL NOT write directly to the memory backend.

#### Scenario: Source fragment contains memory-like facts
- **GIVEN** a source fragment contains fact, episodic, relationship, preference, or style information
- **WHEN** memory migration runs
- **THEN** it SHALL create memory proposals
- **AND** no `MemoryWriteJob` SHALL be enqueued.

### Requirement: Memory migration can include import proposals
The system SHALL optionally analyze existing import proposals in the same run to produce memory candidates.

#### Scenario: Proposal inclusion is enabled
- **GIVEN** an import run contains character, relationship, lore, or dialogue proposals
- **WHEN** memory migration runs with proposal inclusion enabled
- **THEN** eligible proposal payloads SHALL be converted into memory proposal candidates
- **AND** candidates SHALL be deduplicated before persistence.

### Requirement: Memory migration is worldline-scoped
The system SHALL reject memory migration requests whose source fragments do not belong to the import run worldline.

#### Scenario: Cross-worldline fragment is supplied
- **GIVEN** an import run belongs to one worldline
- **WHEN** memory migration receives a source fragment from another worldline
- **THEN** the request SHALL fail
- **AND** no memory proposals SHALL be created from that fragment.

### Requirement: Memory migration records safe summary counts
The system SHALL update import run summary JSON with migration mode, proposal inclusion flag, provider execution status, and memory category counts.

#### Scenario: Memory migration completes
- **GIVEN** a memory migration request succeeds
- **WHEN** the result is returned
- **THEN** it SHALL include fact, episodic, relationship, preference, and style counts
- **AND** `provider_execution` SHALL be `false`.

## Non-goals

- This spec does not define direct memory backend SDK access.
- This spec does not define automatic memory writes outside explicit future apply semantics.
- This spec does not define provider-backed memory extraction.
