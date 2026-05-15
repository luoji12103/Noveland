# Script Parser & Dialogue Extractor Specification

## Purpose

This spec captures current v0.5 deterministic script parsing behavior: source fragment parsing into reviewable dialogue, scene, choice, route, and event proposals without provider calls or canonical mutation.

## Requirements

### Requirement: Script parsing reads source fragments in one worldline
The system SHALL parse only source fragments that belong to the import run worldline.

#### Scenario: Parser receives a cross-worldline fragment
- **GIVEN** an import run belongs to one worldline
- **WHEN** a parse request includes a source fragment from another worldline
- **THEN** the request SHALL be rejected
- **AND** no parse proposals SHALL be created.

### Requirement: Parser creates reviewable proposals
The system SHALL create import proposals for detected dialogue, unresolved quoted dialogue, scene markers, choices, route markers, and event markers.

#### Scenario: Script fragment contains multiple candidate forms
- **GIVEN** a source fragment contains speaker dialogue, quoted unresolved dialogue, scene markers, choice lines, route markers, and event markers
- **WHEN** the deterministic parser runs
- **THEN** it SHALL create traceable proposals for each detected candidate
- **AND** each proposal SHALL link back to the source fragment.

### Requirement: Parser summary records deterministic execution
The system SHALL update the import run summary with parser mode, candidate counts, unresolved speaker count, and provider execution status.

#### Scenario: Parser completes
- **GIVEN** a parse request succeeds
- **WHEN** the result is returned
- **THEN** the response SHALL include created proposal, dialogue, scene, choice, route, event, and unresolved speaker counts
- **AND** `provider_execution` SHALL be `false`.

### Requirement: Parser does not mutate world events
The system SHALL NOT write parser output into `world_events.payload`.

#### Scenario: Parser creates event proposals
- **GIVEN** a source fragment contains an event marker
- **WHEN** the parser creates an event candidate proposal
- **THEN** the candidate SHALL remain an authoring proposal
- **AND** no world event SHALL be appended.

## Non-goals

- This spec does not define full script engine compatibility.
- This spec does not define provider-backed parsing.
- This spec does not define direct conversation, scene, route, or world event creation.
