# Script Parser & Dialogue Extractor

## Capability

Parse dialogue, speaker, scene, choice, route, and event candidates. This capability belongs to v0.5 Authoring & Import Studio and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Script Parser & Dialogue Extractor provides the planned workflow
The system SHALL provide Script Parser & Dialogue Extractor capability for Script parse jobs, Dialogue extraction, Speaker resolution, Scene/choice candidate extraction, Preview records while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Script Parser & Dialogue Extractor
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse Phase 1 authoring source fragments/proposals, provider execution for optional parsing, and invocation ledger rather than creating a parallel subsystem.

### Requirement: Script Parser & Dialogue Extractor preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Script Parser & Dialogue Extractor, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Script Parser & Dialogue Extractor reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Script Parser & Dialogue Extractor has explicit acceptance evidence
The system SHALL provide focused validation for Script Parser & Dialogue Extractor and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Script Parser & Dialogue Extractor is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Direct apply to world state
