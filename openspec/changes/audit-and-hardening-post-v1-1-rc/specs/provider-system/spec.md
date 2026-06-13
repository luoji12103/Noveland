## MODIFIED Requirements

### Requirement: Provider execution writes invocation evidence
The system SHALL create model_invocations and prompt_snapshots for provider-backed calls, including failed calls.

#### Scenario: Failed provider call
- **GIVEN** a provider request fails because of missing auth, unsupported capability, timeout, malformed response, or upstream error
- **WHEN** the provider execution service handles the failure
- **THEN** a failed invocation record SHALL exist
- **AND** prompt snapshot evidence SHALL be safe and redacted.

#### Scenario: Legacy provider profile execution is controlled
- **GIVEN** a legacy provider profile path can trigger model-provider plugins or upstream HTTP providers
- **WHEN** an operator, runtime loop, agent run, conversation advance, or narrative generation uses that path
- **THEN** the call SHALL route through ProviderExecutionService or be explicitly disabled/degraded until it is migrated
- **AND** it SHALL NOT bypass invocation ledger, prompt snapshot, safe auth metadata, or provider execution error handling.

#### Scenario: World admin provider execution respects provider visibility
- **GIVEN** a world admin can run provider smoke tests or explicit provider test invocations for their world
- **WHEN** the target primary provider or fallback provider is global, hidden, developer-only, cross-world, or otherwise not visible to that world admin through provider registry routes
- **THEN** the execution route SHALL reject the request before adapter execution, health-check writes, media-job writes, or invocation/prompt-snapshot writes
- **AND** platform admins MAY continue to execute platform-visible provider integrations for controlled diagnostics.
