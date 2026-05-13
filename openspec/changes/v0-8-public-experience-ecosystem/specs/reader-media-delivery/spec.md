# Reader Media Delivery

## Capability

Provide reader-visible media delivery without leaking storage_uri or filesystem paths. This capability belongs to v0.8 Public Experience & Ecosystem and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Reader Media Delivery provides the planned workflow
The system SHALL provide Reader Media Delivery capability for Reader media endpoint, Image/audio delivery, Visibility enforcement while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Reader Media Delivery
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse MediaService, media references, authorization rather than creating a parallel subsystem.

### Requirement: Reader Media Delivery preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Reader Media Delivery, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Reader Media Delivery reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Reader Media Delivery has explicit acceptance evidence
The system SHALL provide focused validation for Reader Media Delivery and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Reader Media Delivery is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Admin-only media exposure
- Raw storage path delivery
