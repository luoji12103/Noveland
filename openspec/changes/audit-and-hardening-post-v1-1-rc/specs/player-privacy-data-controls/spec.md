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
