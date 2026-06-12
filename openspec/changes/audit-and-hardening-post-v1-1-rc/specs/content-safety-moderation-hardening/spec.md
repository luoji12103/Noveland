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

#### Scenario: Moderation target refs resolve within their owning scope
- **Given** a report, safety review, or action targets a scene, narrative publication, or player profile
- **When** the moderation API validates the mutation
- **Then** the API SHALL reject missing, cross-world, and cross-worldline target refs
- **And** worldline-scoped targets SHALL only be accepted when the target belongs to the supplied worldline
- **And** moderation records SHALL NOT be persisted for arbitrary UUIDs that do not resolve to the requested world scope.
