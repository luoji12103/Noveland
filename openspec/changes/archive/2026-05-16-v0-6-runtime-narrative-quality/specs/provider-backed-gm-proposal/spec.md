# Provider-backed GM Proposal

## Capability

Use provider-kernel text generation to generate GM proposals without directly mutating world state. This capability belongs to v0.6 Runtime Narrative Quality and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Provider-backed GM Proposal provides the planned workflow
The system SHALL provide Provider-backed GM Proposal capability for provider-kernel text generation alignment, GM proposal generation, Review/apply boundary, Impact classification while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Provider-backed GM Proposal
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse ProviderExecutionService, ProviderSecretResolver, InvocationLedgerService, prompt snapshots, world events rather than creating a parallel subsystem.
- **And** real provider-backed GM generation SHALL NOT use the legacy provider profile path for new v0.6 execution.

### Requirement: Provider-backed GM Proposal uses the narrative quality API boundary
The system SHALL expose new v0.6 GM quality APIs through `narrative_quality.py` rather than adding broad routes to `worlds.py`.

#### Scenario: New GM proposal API is added
- **Given** a v0.6 implementation adds provider-backed GM proposal endpoints
- **When** those endpoints are registered
- **Then** they SHALL be registered through the narrative quality router
- **And** they SHALL be admin-scoped and worldline-aware.

### Requirement: Provider-backed GM Proposal preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Provider-backed GM Proposal, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Provider-backed GM Proposal reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Provider-backed GM Proposal has explicit acceptance evidence
The system SHALL provide focused validation for Provider-backed GM Proposal and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Provider-backed GM Proposal is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Automatic high-impact event apply
- Broad new `worlds.py` routes
