# World Bible & Lore Extractor

## Capability

Extract locations, organizations, world rules, secrets, and knowledge boundaries. This capability belongs to v0.5 Authoring & Import Studio and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: World Bible & Lore Extractor provides the planned workflow
The system SHALL provide World Bible & Lore Extractor capability for World bible fragments, Lore candidates, Secret/knowledge boundary candidates, canon/inference/uncertain classification while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using World Bible & Lore Extractor
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse worlds/events docs, future world bible records, provider ledger if model-backed rather than creating a parallel subsystem.

### Requirement: World Bible & Lore Extractor preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for World Bible & Lore Extractor, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** World Bible & Lore Extractor reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: World Bible & Lore Extractor has explicit acceptance evidence
The system SHALL provide focused validation for World Bible & Lore Extractor and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for World Bible & Lore Extractor is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Runtime context injection of full raw source
