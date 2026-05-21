# Cost & Quota Real Enforcement Specification

## Purpose
This spec captures the current v1.0 private beta cost and quota enforcement behavior on `main`. It covers provider-owned pre-spend checks, world/provider/capability/player budget scopes, explicit admin overrides, safe quota evidence, and no-hidden-spend failure behavior.

## Requirements
### Requirement: Quotas limit provider spend by scope
The system SHALL enforce quotas for provider calls by world, player, provider, and capability where configured.

#### Scenario: Player exceeds image quota
- **Given** a player has reached the configured image generation quota
- **When** another image generation would be requested
- **Then** the system SHALL block or degrade the request with a safe explanation
- **And** it SHALL NOT execute hidden provider spend.

### Requirement: Per-player quota isolation is enforced
The system SHALL isolate quota usage between private beta testers when player-scoped quota is configured.

#### Scenario: One tester exhausts quota
- **Given** tester A has reached a configured player image quota
- **When** tester B requests image generation within their own quota
- **Then** tester B's request SHALL be evaluated independently
- **And** tester A's exhausted quota SHALL NOT block tester B unless a world/provider/capability limit is also exhausted.

### Requirement: Quota failures produce safe audit evidence
The system SHALL record safe quota-block evidence suitable for admin inspection.

#### Scenario: Quota block recorded
- **Given** a provider call is blocked by quota
- **When** an admin reviews cost controls
- **Then** the report SHALL include world, player, provider, capability, limit, and remaining budget summary
- **And** it SHALL NOT include resolved secrets, raw prompts, raw outputs, or storage paths.

### Requirement: Admin overrides are explicit
The system SHALL require explicit admin action for quota overrides.

#### Scenario: Admin raises player quota
- **Given** a player needs additional quota
- **When** an admin adjusts the limit
- **Then** the change SHALL be audited
- **And** future provider calls SHALL use the updated limit.

## Non-goals

- Billing system.
- Marketplace pricing.
- Silent quota bypass.
