# Private Beta Onboarding Specification

## Purpose
This spec captures the current v1.0 private beta onboarding and access model on `main`. It covers invite-only access, hashed token handling, lifecycle audit, least-privilege world membership bootstrap, guided player profile setup, and safe first-run onboarding for selected beta testers.

## Requirements
### Requirement: Private beta invitations preserve lifecycle and audit
The system SHALL represent private beta invitation lifecycle separately from world membership.

#### Scenario: Admin creates an invite
- **Given** an authorized world admin creates a private beta invite
- **When** the invite is stored
- **Then** the invite SHALL preserve world, optional worldline, inviter actor, invited email or user reference, intended beta role, expiration, status, and safe metadata
- **And** the invite SHALL NOT store the raw token.

#### Scenario: Invite is no longer redeemable
- **Given** an invite is expired, revoked, or waitlisted
- **When** a tester attempts redemption
- **Then** the system SHALL reject redemption
- **And** it SHALL NOT create or upgrade world membership.

#### Scenario: Invite is redeemed
- **Given** an invite is pending or accepted, unexpired, and valid for the requested world
- **When** an authenticated tester redeems it
- **Then** the system SHALL record redemption actor and timestamp
- **And** it MAY create or update a least-privilege world membership
- **And** repeated redemption SHALL be idempotent only when the same user and same invite make it safe.

### Requirement: Invite tokens are protected
The system SHALL handle private beta invite tokens as secrets.

#### Scenario: Invite token is issued
- **Given** an authorized admin creates an invite
- **When** the token is generated
- **Then** the token SHALL be non-guessable
- **And** the system SHALL store only a hash or equivalent non-redeemable verifier.

#### Scenario: Invite data is returned
- **Given** invite records are listed, inspected, redeemed, or used for onboarding
- **When** an API response is produced
- **Then** it SHALL NOT include the raw token
- **And** the token SHALL NOT appear in logs, prompt snapshots, model invocations, `world_events.payload`, reader APIs, player APIs, or member APIs.

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
- **And** all records SHALL be scoped to the authorized world, worldline, and player.

#### Scenario: Invite is redeemed before profile setup
- **Given** an authenticated tester has redeemed a valid invite
- **When** they have not completed guided player identity setup
- **Then** the system SHALL grant only safe onboarding access
- **And** it SHALL require a worldline-scoped player profile before player session use.

### Requirement: Onboarding preserves least privilege
The system SHALL grant private beta testers only the minimum permissions required for beta play.

#### Scenario: Tester completes onboarding
- **Given** an invited tester completes onboarding
- **When** their access is created
- **Then** the resulting access SHALL NOT grant platform-admin, world-admin, provider-admin, media-admin, invocation-ledger admin, or setup-wizard permissions
- **And** any world membership SHALL remain bounded to the selected private beta world.

#### Scenario: Tester calls admin routes
- **Given** an invited tester has redeemed access as a beta tester
- **When** they request admin, provider, invocation-ledger admin, or media-admin routes
- **Then** the system SHALL reject the request
- **And** it SHALL NOT expose provider configuration, resolved secrets, prompt snapshot internals, hidden assets, developer-only assets, storage paths, raw prompts, or raw outputs.

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
