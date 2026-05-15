# Authoring Source Registry Specification

## Purpose

This spec captures current v0.5 authoring source registry behavior on `main`: strict-worldline source batches, source assets, source fragments, safe metadata, media reference validation, and the dedicated authoring package/router boundary.

## Requirements

### Requirement: Authoring sources are worldline-scoped
The system SHALL store authoring source batches, source assets, and source fragments with non-null `world_id` and `worldline_id`.

#### Scenario: Source batch is created
- **GIVEN** a world admin creates an authoring source batch
- **WHEN** the request includes a valid worldline
- **THEN** the batch SHALL be persisted under that world and worldline
- **AND** list operations SHALL filter by the requested worldline.

### Requirement: Source assets may reference media assets safely
The system SHALL allow source assets to reference existing `media_assets` only when the media asset belongs to the same world and worldline.

#### Scenario: Cross-worldline media is referenced
- **GIVEN** a source asset request includes a `media_asset_id`
- **WHEN** the media asset belongs to another worldline
- **THEN** the request SHALL be rejected
- **AND** no authoring source asset SHALL be created.

### Requirement: Source fragments preserve traceable excerpts
The system SHALL store source fragments with a stable fragment key, kind, sequence, excerpt text, locator JSON, and metadata JSON.

#### Scenario: Fragment is added to a source asset
- **GIVEN** a source asset exists in the target worldline
- **WHEN** a world admin adds a fragment
- **THEN** the fragment SHALL be persisted under the same world and worldline
- **AND** the fragment SHALL be available for parser, extractor, matching, and migration workflows.

### Requirement: Authoring JSON rejects leaked implementation data
The system SHALL reject source metadata, locator JSON, and excerpt values that contain disallowed storage, path, bytes, base64, raw prompt, raw output, or raw source keys/values.

#### Scenario: Leaky metadata is submitted
- **GIVEN** an authoring create request contains `storage_uri`, `file://`, `local://`, `base64`, `raw_prompt`, `raw_output`, or `full_raw_source`
- **WHEN** the request is validated
- **THEN** the request SHALL fail validation
- **AND** the unsafe value SHALL NOT be persisted.

### Requirement: Authoring uses a dedicated backend boundary
The system SHALL expose authoring registry behavior through `backend/packages/authoring/` and `backend/services/api/src/noveland/services/api/authoring.py`.

#### Scenario: Authoring source API is called
- **GIVEN** a world admin calls `/worlds/{world_id}/authoring/source-batches`
- **WHEN** the backend handles the request
- **THEN** it SHALL use the authoring package service
- **AND** it SHALL NOT add broad v0.5 authoring/import logic to `worlds.py`.

## Non-goals

- This spec does not define provider-backed extraction.
- This spec does not define Web authoring UI.
- This spec does not define direct canonical world-state mutation.
- This spec does not define public reader access to authoring sources.
