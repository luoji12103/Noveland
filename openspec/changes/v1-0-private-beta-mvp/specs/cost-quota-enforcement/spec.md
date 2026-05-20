# Cost & Quota Real Enforcement

## ADDED Requirements

### Requirement: Quota ownership is decided before implementation
The system SHALL complete a docs-only checkpoint before implementing private beta quota enforcement.
The checkpoint SHALL decide whether player/capability quotas extend provider budget policy JSON or
require dedicated quota policy records.

#### Scenario: Quota checkpoint runs
- **Given** v1.0 Phase 3 is selected for implementation
- **When** the checkpoint is written
- **Then** it SHALL map all runtime/provider/media/speech/image spend paths that must be guarded
- **And** it SHALL define how world, player, provider, and capability scopes are evaluated before provider execution.

#### Scenario: Checkpoint selects provider-owned JSON policy extension
- **Given** existing provider budget policies already guard provider execution before external calls
- **When** Phase 3 implementation begins
- **Then** the implementation SHALL keep enforcement in `ProviderExecutionService`
- **And** it SHALL extend provider budget policy JSON with player and capability scopes before adding new quota tables.

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
