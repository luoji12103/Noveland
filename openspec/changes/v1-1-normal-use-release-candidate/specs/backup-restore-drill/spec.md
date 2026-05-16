# Backup / Restore Drill

## ADDED Requirements

### Requirement: Backup restore drill verifies database and media state
The system SHALL support a real backup/restore drill that verifies database records, media payloads, media checksums, worldlines, conversations, presentations, and memory state.

#### Scenario: Restore completes
- **Given** a backup archive and media payload archive exist
- **When** they are restored to the accepted target environment
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

## Non-goals

- Cloud-specific backup product.
- Restoring resolved secrets.
- Public restore report.
