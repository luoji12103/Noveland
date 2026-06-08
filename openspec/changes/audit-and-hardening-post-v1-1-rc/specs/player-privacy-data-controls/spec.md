## MODIFIED Requirements

### Requirement: Privacy controls are auditable
The system SHALL record safe status and evidence references for privacy requests without exposing sensitive contents.

#### Scenario: Admin reviews delete request
- **Given** an admin reviews a player delete request
- **When** the request status changes
- **Then** the audit trail SHALL contain safe summaries and actor refs only.

#### Scenario: Privacy mutations require CSRF
- **Given** an authenticated browser session creates an export request, creates a delete request, or reviews a privacy request
- **When** the request would persist or update privacy control state
- **Then** the API SHALL require a matching CSRF cookie and X-CSRF-Token header before mutating privacy state.

### Requirement: Player exports omit operator-only evidence
The system SHALL keep player privacy exports limited to safe player-owned or player-visible fields.

#### Scenario: Player export includes interaction records
- **GIVEN** a player requests their data export
- **WHEN** journal, notification, or intervention records contain source refs, source event refs, choice/event linkage, prompt text, metadata, storage paths, raw prompts, raw outputs, bytes, base64, secrets, or hidden admin evidence
- **THEN** the export SHALL omit those operator-only internals while preserving safe player-owned titles, bodies, selected options, statuses, target identity fields, and timing fields.
