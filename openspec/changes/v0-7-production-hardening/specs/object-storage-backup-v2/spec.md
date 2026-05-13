# Object Storage & Backup v2

## Capability

Define S3/GCS-compatible abstraction, backup/restore drill, checksum audit, and object lifecycle policy. This capability belongs to v0.7 Production Hardening and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Object Storage & Backup v2 provides the planned workflow
The system SHALL provide Object Storage & Backup v2 capability for Storage backend abstraction, Backup/restore procedure, Integrity checks while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Object Storage & Backup v2
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse MediaService, media_objects, storage local/backup modules rather than creating a parallel subsystem.

### Requirement: Object Storage & Backup v2 preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Object Storage & Backup v2, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Object Storage & Backup v2 reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Object Storage & Backup v2 has explicit acceptance evidence
The system SHALL provide focused validation for Object Storage & Backup v2 and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Object Storage & Backup v2 is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Public media CDN delivery
