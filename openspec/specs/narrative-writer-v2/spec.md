# Narrative Writer v2 Specification

## Purpose

This spec captures the current v0.6 admin-only Narrative Writer v2 capability on `main`. It covers strict-worldline draft artifact generation, provider-kernel text execution, reader-safe output boundaries, and narrative artifact/publication worldline strategy.

## Requirements
### Requirement: Narrative Writer v2 provides the current workflow
The system SHALL provide Narrative Writer v2 capability for Narrative generation v2, narrative artifact worldline strategy, Visibility filter, Reader-safe output while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Narrative Writer v2
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the implemented Narrative Writer v2 scope
- **And** the workflow SHALL reuse narrative services, events, provider execution, invocation ledger, media references rather than creating a parallel subsystem.
- **And** provider-backed narrative generation SHALL NOT start until provider-kernel text generation execution is available.

### Requirement: Narrative Writer v2 resolves narrative artifact worldline strategy first
The system SHALL stop implementation before Narrative Writer v2 if strict worldline behavior for narrative artifacts and publications is unresolved.

#### Scenario: Narrative artifact worldline strategy is unresolved
- **Given** Narrative Writer v2 implementation is about to persist generated narrative drafts
- **When** `narrative_artifacts` worldline behavior has not been decided
- **Then** implementation SHALL stop for architecture review
- **And** generated drafts SHALL NOT rely only on ad hoc metadata for required worldline isolation.

### Requirement: Narrative Writer v2 uses the narrative quality API boundary
The system SHALL expose new v0.6 narrative writer quality APIs through `narrative_quality.py` rather than adding broad routes to `worlds.py`.

#### Scenario: New narrative writer API is added
- **Given** a v0.6 implementation adds Narrative Writer v2 endpoints
- **When** those endpoints are registered
- **Then** they SHALL be registered through the narrative quality router
- **And** they SHALL be admin-scoped and worldline-aware.

### Requirement: Narrative Writer v2 preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Narrative Writer v2, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Narrative Writer v2 reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Narrative Writer v2 has explicit acceptance evidence
The system SHALL provide focused validation for Narrative Writer v2 and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Narrative Writer v2 is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Narrative artifacts as media storage.
- Raw prompt/output in `world_events.payload`.
- Broad new `worlds.py` routes.
- Automatic publication.
