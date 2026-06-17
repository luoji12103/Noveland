## MODIFIED Requirements

### Requirement: Quotas limit provider spend by scope
The system SHALL enforce quotas for provider calls by world, player, provider, and capability where configured.

#### Scenario: Player exceeds image quota
- **Given** a player has reached the configured image generation quota
- **When** another image generation would be requested
- **Then** the system SHALL block or degrade the request with a safe explanation
- **And** it SHALL NOT execute hidden provider spend.

#### Scenario: Legacy provider profile spend is not hidden
- **Given** a legacy provider profile test call, runtime agent run, conversation turn, or narrative generation would call an external provider
- **When** quota enforcement cannot be proven for that call path
- **Then** the system SHALL block, degrade, or migrate the path before external provider execution
- **And** it SHALL NOT execute hidden provider spend outside ProviderExecutionService.
