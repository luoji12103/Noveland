## MODIFIED Requirements

### Requirement: Safety workflows integrate feedback and privacy boundaries
The system SHALL keep moderation as the safety/action owner while allowing beta feedback to escalate to moderation when a report involves safety, abuse, or player-visible harm. Player privacy records SHALL remain the owner for player data export or deletion requests.

#### Scenario: Feedback escalates to moderation
- **Given** a tester submits beta feedback that identifies a safety issue
- **When** an admin escalates it
- **Then** the system SHALL preserve reporter privacy, safe feedback refs, and moderation audit refs
- **And** it SHALL NOT expose reporter private data to other testers.

#### Scenario: Moderation mutations require CSRF
- **Given** an authenticated browser session has access to moderation write routes
- **When** the session submits, reviews, escalates, creates an action, or creates/reviews an incident
- **Then** the API SHALL require a matching CSRF cookie and X-CSRF-Token header before mutating moderation state.
