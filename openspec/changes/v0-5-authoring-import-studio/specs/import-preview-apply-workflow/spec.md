# Import Preview/Apply Workflow

## Capability

Unify import run lifecycle, proposal review, selective apply, rollback hints, source traceability, and audit records as the shared Phase 1 foundation. This capability belongs to v0.5 Authoring & Import Studio and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Import Preview/Apply Workflow provides the planned workflow
The system SHALL provide Import Preview/Apply Workflow capability for import run lifecycle, proposal creation, proposal review, review decisions, selective apply, rollback hints, source traceability, and audit trail while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Import Preview/Apply Workflow
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL use the dedicated authoring package/router
- **And** the workflow SHALL reuse asset generation preview/apply patterns, world events, diagnostics rather than creating a parallel subsystem.

### Requirement: Import Preview/Apply Workflow is the Phase 1 shared foundation
The system SHALL implement import runs, proposals, review decisions, source traceability, preview, and selective apply before extractor, matching, memory migration, or regression fixture phases depend on it.

#### Scenario: Later phase creates candidates
- **Given** a later v0.5 extractor or matching phase identifies a candidate
- **When** the candidate is persisted
- **Then** it SHALL be represented as an authoring proposal linked to an import run and source fragment
- **And** it SHALL use the shared review/apply state model.

### Requirement: Import Preview/Apply Workflow preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Import Preview/Apply Workflow, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Import Preview/Apply Workflow reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Import Preview/Apply Workflow has explicit acceptance evidence
The system SHALL provide focused validation for Import Preview/Apply Workflow and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Import Preview/Apply Workflow is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Unbounded batch mutation
- Provider outputs directly applying state
- Direct apply for unsupported proposal kinds
