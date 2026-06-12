## MODIFIED Requirements

### Requirement: Missing media has safe fallback
The system SHALL show safe fallback states when image, sprite, background, audio, or presentation data is missing, unavailable, or outside the player session worldline.

#### Scenario: Presentation references media outside the session worldline
- **Given** a player resume request references a presentation in the player session worldline
- **AND** that presentation points to image, background, composite, or audio media from another worldline or world
- **WHEN** the player session recovery state is calculated
- **THEN** the response SHALL use a safe missing-media recovery state instead of marking playback ready
- **AND** the response SHALL NOT expose storage paths, raw object metadata, bytes, base64, or provider internals.

#### Scenario: Presentation references private or admin-only media
- **Given** a player resume request references a presentation in the player session worldline
- **AND** that presentation points to private or admin-only image, background, composite, or audio media
- **WHEN** the player session recovery state is calculated
- **THEN** the response SHALL use a safe missing-media recovery state instead of marking playback ready
- **AND** the response SHALL NOT expose storage paths, raw object metadata, bytes, base64, or provider internals.
