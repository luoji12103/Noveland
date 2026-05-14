# Authoring Source Registry

## Capability

Manage script, lore, character sheet, location sheet, image, and audio source assets through the dedicated v0.5 authoring package/router. This capability belongs to v0.5 Authoring & Import Studio and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Authoring Source Registry provides the planned workflow
The system SHALL provide Authoring Source Registry capability for source batches, source assets, source fragments, source metadata, target worldline, ownership, and visibility while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Authoring Source Registry
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL use `backend/packages/authoring/` and `authoring.py`
- **And** the workflow SHALL reuse MediaService, worldline records, auth/ACL services rather than creating a parallel subsystem.

### Requirement: Authoring Source Registry owns v0.5 source boundaries
The system SHALL treat existing `authoring_templates`, `authoring_import_jobs`, and world composition import as legacy-compatible inputs or references, not as the primary v0.5 foundation.

#### Scenario: Legacy source is referenced
- **Given** a v0.5 import references an existing authoring template or composition import artifact
- **When** the source registry records the reference
- **Then** it SHALL store safe source metadata and traceability
- **And** it SHALL NOT move new v0.5 source registry logic into `worlds.py`.

### Requirement: Authoring Source Registry preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Authoring Source Registry, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Authoring Source Registry reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Authoring Source Registry has explicit acceptance evidence
The system SHALL provide focused validation for Authoring Source Registry and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Authoring Source Registry is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Parsing or applying source content
- Provider-backed extraction
- Direct canonical state mutation
