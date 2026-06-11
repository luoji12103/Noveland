## MODIFIED Requirements

### Requirement: TTS and STT test actions are explicit
The system SHALL expose explicit TTS and STT admin actions using existing speech orchestration APIs.

#### Scenario: Admin speech test responses omit internal media and invocation payloads
- **GIVEN** an authorized world admin runs a TTS or STT test action
- **WHEN** the speech API returns media, job, transcript, and invocation references
- **THEN** the response SHALL omit raw audio bytes, storage URIs, filesystem/object paths, resolved secrets, provider request bodies, raw prompt text, and raw provider output text
- **AND** it SHALL preserve safe IDs, world/worldline scope, status, MIME/checksum metadata, transcript text, and invocation IDs needed for operator follow-up.
