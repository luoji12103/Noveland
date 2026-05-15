# Authoring Regression Fixture Specification

## Purpose

This spec captures current v0.5 authoring regression fixture behavior: a deterministic sample import fixture covers source registry, parser, character/lore extraction, conflict review, memory migration, asset matching, guarded apply, and leak/side-effect checks.

## Requirements

### Requirement: Authoring fixture is deterministic
The system SHALL provide a repeatable authoring sample import fixture with stable world, worldline, user, media, proposal, and target-ref signatures.

#### Scenario: Fixture is created twice
- **GIVEN** the authoring sample fixture helper is called twice
- **WHEN** the fixture records are compared
- **THEN** stable identifiers and count summaries SHALL match
- **AND** the fixture SHALL be suitable for regression testing.

### Requirement: Authoring fixture covers the v0.5 pipeline
The fixture SHALL exercise source batches, source assets, fragments, import runs, proposals, source traceability, parser output, character/lore candidates, conflict reports, memory candidates, asset matches, review, and guarded apply.

#### Scenario: Fixture pipeline is inspected
- **GIVEN** the authoring sample fixture has been created
- **WHEN** tests inspect proposal and target-ref counts
- **THEN** dialogue, character, relationship, lore, memory, asset match, conflict report, and trace-only apply coverage SHALL be present.

### Requirement: Authoring fixture is worldline-scoped
The fixture SHALL create authoring records that all belong to the same world and primary worldline.

#### Scenario: Fixture records are queried
- **GIVEN** fixture authoring records exist
- **WHEN** tests read source batches, source assets, fragments, runs, proposals, and traceability
- **THEN** every record SHALL have the fixture world id
- **AND** every worldline-scoped record SHALL have the fixture worldline id.

### Requirement: Authoring fixture has no runtime or media side effects
The fixture SHALL NOT create world events, media jobs, memory write jobs, visual bindings, voice profiles, or voice bindings.

#### Scenario: Fixture side effects are inspected
- **GIVEN** the fixture has completed review and guarded apply
- **WHEN** tests inspect runtime, media, memory, visual, and speech side-effect tables
- **THEN** those side-effect tables SHALL remain empty for the fixture
- **AND** proposal payloads SHALL not contain storage URI, file path, base64, raw prompt, raw output, or full raw source leaks.

## Non-goals

- This spec does not define a production seed framework.
- This spec does not define a content quality benchmark.
- This spec does not define Web fixture controls.
