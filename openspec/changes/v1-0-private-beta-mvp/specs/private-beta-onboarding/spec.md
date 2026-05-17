# Private Beta Onboarding

## ADDED Requirements

### Requirement: Private beta access ownership is decided before implementation
The system SHALL complete a docs-only phase checkpoint before implementing private beta onboarding.
The checkpoint SHALL decide whether private beta access is represented by dedicated invite/access
records or by existing world memberships.

#### Scenario: Checkpoint selects dedicated access records
- **Given** existing world memberships cannot represent invite expiry, revocation, redemption, and audit safely
- **When** Phase 1 implementation begins
- **Then** the implementation SHALL use a dedicated private beta access boundary
- **And** it SHALL avoid broad route growth in `worlds.py`.

#### Scenario: Checkpoint selects membership-only access
- **Given** the checkpoint selects existing world memberships
- **When** implementation begins
- **Then** the checkpoint SHALL document how invite eligibility, revocation, redemption, audit, and least privilege are represented
- **And** implementation SHALL stop if those semantics cannot be preserved.

### Requirement: Private beta onboarding is invite-only
The system SHALL restrict private beta onboarding to invited or explicitly eligible testers.

#### Scenario: Uninvited user opens onboarding
- **Given** an authenticated user has no private beta eligibility
- **When** they request onboarding
- **Then** the system SHALL reject access
- **And** it SHALL NOT expose world setup details, admin diagnostics, provider configuration, or hidden media.

### Requirement: Onboarding creates player profile and identity
The system SHALL let eligible testers create or select a player profile, select an allowed world, and create or select a player identity.

#### Scenario: Eligible tester completes onboarding
- **Given** an eligible tester selects an allowed world
- **When** they complete profile and identity setup
- **Then** the system SHALL create player-scoped records using existing player boundaries
- **And** all records SHALL be scoped to the authorized world and player.

### Requirement: Onboarding preserves least privilege
The system SHALL grant private beta testers only the minimum permissions required for beta play.

#### Scenario: Tester completes onboarding
- **Given** an invited tester completes onboarding
- **When** their access is created
- **Then** the resulting access SHALL NOT grant platform-admin, world-admin, provider-admin, media-admin, invocation-ledger admin, or setup-wizard permissions
- **And** any world membership SHALL remain bounded to the selected private beta world.

### Requirement: First-run guidance is player-safe
The system SHALL provide first-run guidance without exposing admin-only diagnostics, raw prompts, raw outputs, storage paths, or secrets.

#### Scenario: Guidance displayed
- **Given** a tester reaches the first-run screen
- **When** guidance is shown
- **Then** the content SHALL describe allowed player actions and recovery paths
- **And** it SHALL NOT reveal provider internals or hidden route data.

## Non-goals

- Public registration.
- Marketplace onboarding.
- Social graph.
