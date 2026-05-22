# operational-runbooks Specification

## Purpose
This spec captures the current v1.1 operational runbook capability on `main`. It covers normal-use incident runbooks for provider outage, quota exhaustion, stuck media jobs, migration failure, backup/restore, rollback, worldline restore, secret rotation, private beta incidents, import/export recovery, and provider fallback/degraded mode with safe redaction rules.
## Requirements
### Requirement: Runbooks cover normal-use incidents
The system SHALL provide operator runbooks for provider outage, quota exhaustion, stuck media/jobs, migration failure, backup/restore, rollback, worldline restore, secret rotation, invite/session/feedback incidents, and import/export recovery.

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

#### Scenario: Import/export recovery is needed
- **Given** a world package import or export fails validation
- **When** an operator follows the import/export recovery runbook
- **Then** the runbook SHALL point to existing package preview/apply, media manifest, provider config, and source traceability checks
- **And** it SHALL NOT instruct operators to bypass preview/review/apply.

### Requirement: Runbooks are validation-friendly
The system SHALL keep runbooks structured enough for lightweight documentation consistency checks.

#### Scenario: Docs consistency test runs
- **Given** runbooks are updated
- **When** docs consistency checks run
- **Then** referenced critical files, commands, or route docs SHALL be validated where feasible.
