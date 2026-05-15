# Asset Import & Matching Specification

## Purpose

This spec captures current v0.5 deterministic asset import matching behavior: imported source assets and fragments can produce reviewable sprite, background, CG, and voice-reference match proposals without media jobs or binding writes.

## Requirements

### Requirement: Asset matching reads same-worldline source inputs
The system SHALL match source assets and source fragments only when they belong to the import run worldline.

#### Scenario: Cross-worldline source asset is supplied
- **GIVEN** an import run belongs to one worldline
- **WHEN** an asset matching request includes a source asset from another worldline
- **THEN** the source SHALL be rejected or counted as blocked
- **AND** no match proposal SHALL be created from that source.

### Requirement: Asset matching validates referenced media assets
The system SHALL validate source media asset references against the same world and worldline before using them for asset matching.

#### Scenario: Source asset references media from another worldline
- **GIVEN** a source asset create request includes a media asset from another worldline
- **WHEN** validation runs
- **THEN** the request SHALL fail
- **AND** the unsafe source asset SHALL NOT be persisted.

### Requirement: Asset matching creates reviewable media binding candidates
The system SHALL create authoring proposals for sprite, background, CG, and voice-reference matches based on deterministic source hints.

#### Scenario: Imported assets contain role hints
- **GIVEN** source assets or fragments include sprite, background, CG, or voice-like hints
- **WHEN** deterministic asset matching runs
- **THEN** it SHALL create `asset_match` proposals with safe payload and evidence
- **AND** it SHALL NOT create media jobs, visual bindings, speech bindings, or provider invocations.

### Requirement: Asset matching records match summary counts
The system SHALL update import run summary JSON with matching mode, included match categories, provider execution status, match counts, and blocked count.

#### Scenario: Asset matching completes
- **GIVEN** an asset matching request succeeds
- **WHEN** the result is returned
- **THEN** it SHALL include sprite, background, CG, voice, and blocked counts
- **AND** `provider_execution` SHALL be `false`.

## Non-goals

- This spec does not define public media delivery.
- This spec does not define automatic visual or speech binding apply.
- This spec does not define media upload storage behavior beyond referencing existing media assets.
- This spec does not define provider-backed asset classification.
