# Character & Relationship Extractor

## Capability

Extract characters, relationships, names, factions, identities, and emotional baselines. This capability belongs to v0.5 Authoring & Import Studio and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Character & Relationship Extractor provides the planned workflow
The system SHALL provide Character & Relationship Extractor capability for Character candidates, Relationship candidates, Faction/identity tags, Review records while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Character & Relationship Extractor
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse agents package, existing relationship records for explicit apply, and the Phase 1 import preview/apply workflow rather than creating a parallel subsystem.

### Requirement: Character & Relationship Extractor preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Character & Relationship Extractor, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Character & Relationship Extractor reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Character & Relationship Extractor has explicit acceptance evidence
The system SHALL provide focused validation for Character & Relationship Extractor and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Character & Relationship Extractor is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Automatic relationship graph mutation
