# Reader Media Delivery

## Capability

Provide reader-safe media descriptors and delivery for visible media without leaking storage internals. This capability belongs to v0.8 Public Experience & Ecosystem and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Reader media uses safe descriptors
The system SHALL expose reader media through DTOs that contain stable asset/object references, content type, size hints, visibility state, and a safe delivery URL or token, but not storage internals.

#### Scenario: Reader-safe media descriptor
- **Given** a visible media asset is attached to a published reader surface
- **When** an authorized reader requests its descriptor
- **Then** the response SHALL include a safe delivery reference
- **And** the response SHALL NOT include `storage_uri`, filesystem paths, bytes, base64, raw prompts, raw outputs, or resolved secrets.

### Requirement: Reader delivery enforces visibility
The system SHALL enforce media, object, reference, presentation, and narrative publication visibility before serving reader media.

#### Scenario: Hidden media is blocked
- **Given** a media asset is hidden or developer-only
- **When** a reader requests the descriptor or delivery endpoint
- **Then** the request SHALL be denied or omitted from reader results
- **And** the denial SHALL NOT reveal storage internals.

### Requirement: Reader media reuses the media kernel
The system SHALL reuse `MediaService`, `media_assets`, `media_objects`, and `media_references` rather than creating a second media storage framework.

#### Scenario: Existing media object delivery
- **Given** a visible media object exists in media storage
- **When** the reader delivery route serves it
- **Then** bytes SHALL be read through the existing media storage service
- **And** no new media storage path or narrative-artifact storage path SHALL be introduced.

### Requirement: Reader media implementation has explicit acceptance evidence
The implementation SHALL include ACL, visibility, leak, and delivery tests before it can be merged.

#### Scenario: Phase acceptance
- **Given** Reader Media Delivery implementation is complete
- **When** targeted tests and the full local gate run
- **Then** all checks SHALL pass
- **And** the phase SHALL be fast-forward merged only from a clean local branch.

## Non-goals

- Public CDN integration without an accepted phase decision.
- Admin media asset management.
- Provider calls or media generation.
- Exposing raw storage paths or admin media DTOs to readers.
