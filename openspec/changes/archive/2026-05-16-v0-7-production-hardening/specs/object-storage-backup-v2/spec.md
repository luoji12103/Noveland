# Object Storage & Backup v2

## Capability

Define storage integrity, backup/restore drills, checksum audit, lifecycle policy, and an optional S3/GCS-compatible abstraction without public media delivery. This capability belongs to v0.7 Production Hardening and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Storage integrity is auditable
The system SHALL verify media object and snapshot storage existence, size, and checksum using storage abstractions rather than ad hoc filesystem paths.

#### Scenario: Admin runs storage audit
- **Given** media objects and snapshot payload references exist
- **When** an authorized audit runs
- **Then** the system SHALL report missing objects, checksum mismatches, and size mismatches
- **And** the report SHALL avoid exposing raw filesystem paths to reader/member/player routes.

### Requirement: Backup/restore drill is repeatable
The system SHALL document and validate a local backup/restore drill for database and object payloads.

#### Scenario: Operator follows backup procedure
- **Given** a local/single-host deployment has database and object storage data
- **When** the operator follows the v0.7 backup/restore drill
- **Then** the procedure SHALL include backup readiness, database dump, object archive, restore order, migration guidance, and verification
- **And** destructive restore actions SHALL NOT be exposed through public or reader/member APIs.

### Requirement: Storage abstraction avoids cloud lock-in
The system SHALL keep remote object storage provider choice behind a storage interface and SHALL NOT require one managed cloud provider for v0.7 acceptance.

#### Scenario: Remote storage is configured later
- **Given** a future S3/GCS-compatible backend is introduced
- **When** media or snapshot code writes objects
- **Then** callers SHALL use the storage interface
- **And** media/kernel records SHALL continue storing safe object references and checksums, not raw bytes or public URLs.

### Requirement: Object Storage & Backup v2 preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for storage and backup work.

#### Scenario: Boundary enforcement
- **Given** storage/backup reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Object Storage & Backup v2 has explicit acceptance evidence
The system SHALL provide focused validation and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Object Storage & Backup v2 is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Public media CDN delivery
- Destructive restore Web UI
- Managed cloud lock-in
- Bulk historical backfill unless explicitly accepted
