# Visual Asset Admin Console

## Capability

Manage character sprites, expression variants, backgrounds, and scene compose preview. This capability belongs to v0.4 Operator/Admin UX and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Visual Asset Admin Console provides the planned workflow
The system SHALL provide Visual Asset Admin Console capability for Sprite sets, Sprite variants, Scene backgrounds, Resolve sprite preview, Resolve background preview, Compose scene preview while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Visual Asset Admin Console
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse VisualAssetService, VisualResolver, VisualCompositionService, ImageService rather than creating a parallel subsystem.

### Requirement: Visual Asset Admin Console preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Visual Asset Admin Console, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Visual Asset Admin Console reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Visual Asset Admin Console has explicit acceptance evidence
The system SHALL provide focused validation for Visual Asset Admin Console and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Visual Asset Admin Console is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Automatic sprite generation
- Background generation orchestration
- Worldline-null visual defaults
