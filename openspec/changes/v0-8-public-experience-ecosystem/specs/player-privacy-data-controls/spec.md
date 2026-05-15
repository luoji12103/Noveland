# Player Privacy & Data Controls

## Capability

Support player data export and delete-request workflows while protecting shared world history. This capability belongs to v0.8 Public Experience & Ecosystem and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Player exports include only allowed player data
The system SHALL export player-owned or player-visible data according to ACL and knowledge visibility.

#### Scenario: Player requests export
- **Given** a player requests their data export
- **When** the export is generated
- **Then** it SHALL include allowed profile, choice, journal, notification, intervention, and conversation references
- **And** it SHALL exclude secrets, storage paths, raw prompts, raw outputs, and hidden admin evidence.

### Requirement: Delete requests protect shared world state
The system SHALL represent deletion as a reviewable request when records participate in shared world history.

#### Scenario: Shared conversation data
- **Given** a player asks to delete data from a shared conversation
- **When** the system evaluates the request
- **Then** it SHALL create a reviewable request or redaction plan
- **And** it SHALL NOT automatically corrupt shared canonical history.

### Requirement: Privacy controls are auditable
The system SHALL record safe status and evidence references for privacy requests without exposing sensitive contents.

#### Scenario: Admin reviews delete request
- **Given** an admin reviews a player delete request
- **When** the request status changes
- **Then** the audit trail SHALL contain safe summaries and actor refs only.

### Requirement: Privacy controls have explicit acceptance evidence
The implementation SHALL include privacy, ACL, export-redaction, and review workflow tests.

#### Scenario: Phase acceptance
- **Given** Privacy/Data Controls implementation is complete
- **When** targeted tests and the full local gate run
- **Then** all checks SHALL pass before fast-forward merge.

## Non-goals

- Automatic deletion of shared canonical world history.
- Legal compliance automation beyond local product controls.
- Exporting raw internal diagnostics or prompt snapshots.
