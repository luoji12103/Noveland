# backup-restore-drill Specification

## Purpose
This spec captures the current v1.1 backup/restore drill capability on `main`. It covers fresh local/single-host restore verification for database state, media payloads, checksums, worldlines, conversations, presentations, memory, provider config metadata without secrets, OpenSpec/docs provenance, and safe admin restore reports.
## Requirements
### Requirement: Backup restore drill verifies database and media state
The system SHALL support a real backup/restore drill against a fresh local/single-host target that verifies database records, media payloads, media checksums, worldlines, conversations, presentations, memory state, and OpenSpec/docs provenance.

#### Scenario: Restore completes
- **Given** a backup archive and media payload archive exist
- **When** they are restored to a fresh target with empty database and object storage root
- **Then** worldline, conversation, presentation, memory, media object, and checksum verification SHALL pass.

### Requirement: Provider config restore excludes secrets
The system SHALL restore provider configuration metadata without resolved secrets.

#### Scenario: Provider config restored
- **Given** a backup includes provider integration metadata
- **When** restore verification runs
- **Then** provider records SHALL preserve safe config and `auth_ref` references only
- **And** resolved API keys SHALL NOT be present in the backup archive or restore report.

### Requirement: Restore reports are safe
The system SHALL produce safe restore reports for admin review.

#### Scenario: Restore verification fails
- **Given** a media checksum mismatch occurs
- **When** the restore report is generated
- **Then** it SHALL identify the safe media object reference and failure type
- **And** it SHALL NOT expose storage paths, bytes, base64, raw prompts, raw outputs, or secrets.
