# World Bible & Lore Extractor Specification

## Purpose

This spec captures current v0.5 deterministic world-bible and lore extraction behavior: lore, location, organization, world-rule, secret, and knowledge-boundary candidates remain reviewable proposals only.

## Requirements

### Requirement: Lore extraction remains proposal-only
The system SHALL represent extracted lore and world-bible candidates as authoring proposals and SHALL NOT directly apply them to global canon tables.

#### Scenario: Lore candidate is extracted
- **GIVEN** a source fragment describes a location, organization, world rule, secret, or knowledge boundary
- **WHEN** the deterministic lore extractor runs
- **THEN** it SHALL create proposal records
- **AND** no global `WorldBible` or canonical state mutation SHALL occur.

### Requirement: Lore extraction is worldline-scoped
The system SHALL reject lore extraction requests whose source fragments do not belong to the import run worldline.

#### Scenario: Cross-worldline lore fragment is supplied
- **GIVEN** an import run belongs to one worldline
- **WHEN** the request includes a lore fragment from another worldline
- **THEN** the request SHALL fail
- **AND** no proposals SHALL be created from that fragment.

### Requirement: Lore extraction records classification evidence safely
The system SHALL store lore classification, confidence, evidence, and proposal payload in safe authoring JSON fields.

#### Scenario: Secret or uncertain lore is detected
- **GIVEN** a source fragment contains secret or uncertain knowledge
- **WHEN** extraction creates a proposal
- **THEN** the proposal payload and evidence SHALL describe the candidate safely
- **AND** disallowed raw source, storage, path, bytes, base64, prompt, and output values SHALL NOT be persisted.

### Requirement: Lore extraction summarizes candidate counts
The system SHALL update import run summary JSON with lore extractor mode, provider execution status, and candidate counts.

#### Scenario: Lore extraction completes
- **GIVEN** a lore extraction request succeeds
- **WHEN** the result is returned
- **THEN** it SHALL include lore, location, organization, world-rule, secret, knowledge-boundary, and uncertain counts
- **AND** `provider_execution` SHALL be `false`.

## Non-goals

- This spec does not define direct apply to global `WorldBible`.
- This spec does not define runtime context injection of raw source.
- This spec does not define reader/member exposure of secret or developer-only lore candidates.
- This spec does not define provider-backed lore extraction.
