# World Packaging

## Capability

Define world bundle manifest, media bundle manifest, import, and export. This capability belongs to v0.8 Public Experience & Ecosystem and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: World Packaging provides the planned workflow
The system SHALL provide World Packaging capability for World export, World import, Media manifest while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using World Packaging
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse media assets/objects, world records, OpenSpec/current contracts rather than creating a parallel subsystem.

### Requirement: World Packaging preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for World Packaging, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** World Packaging reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: World Packaging has explicit acceptance evidence
The system SHALL provide focused validation for World Packaging and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for World Packaging is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Including secrets or internal storage URIs in bundles
