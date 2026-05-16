# Operational Runbooks

## ADDED Requirements

### Requirement: Runbooks cover normal-use incidents
The system SHALL provide operator runbooks for provider failure, stuck media/jobs, worldline rollback review, backup/restore, and secret rotation.

#### Scenario: Provider outage runbook
- **Given** a provider is degraded or unavailable
- **When** an operator opens the provider failure runbook
- **Then** the runbook SHALL describe safe diagnosis, degraded mode, retry, fallback, and escalation steps
- **And** it SHALL NOT instruct operators to expose resolved secrets or raw prompts.

### Requirement: Runbooks reference existing controls
The system SHALL reference existing routes, commands, diagnostics, and reports where possible rather than inventing unsupported procedures.

#### Scenario: Media job is stuck
- **Given** a media job is stuck
- **When** an operator follows the media/job recovery runbook
- **Then** the runbook SHALL point to existing media job inspection, cancel, reprioritize, or retry controls as applicable.

### Requirement: Runbooks are validation-friendly
The system SHALL keep runbooks structured enough for lightweight documentation consistency checks.

#### Scenario: Docs consistency test runs
- **Given** runbooks are updated
- **When** docs consistency checks run
- **Then** referenced critical files, commands, or route docs SHALL be validated where feasible.

## Non-goals

- External SRE platform.
- Secret disclosure examples.
- Runtime behavior changes by documentation alone.
