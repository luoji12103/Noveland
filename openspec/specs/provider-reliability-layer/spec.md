# provider-reliability-layer Specification

## Purpose
This spec captures the current v1.1 provider reliability layer on `main`. It covers provider health trends, degraded-mode status, explicit audited retry/requeue controls, and manual-first opt-in fallback or model switching with capability, quota, auth, and audit checks.
## Requirements
### Requirement: Provider health trends inform degraded mode
The system SHALL track provider health trends and expose degraded-mode status for provider-dependent workflows.

#### Scenario: Provider repeatedly fails
- **Given** a provider fails repeated health checks or executions
- **When** reliability evaluation runs
- **Then** the provider SHALL be marked degraded or at risk
- **And** admins SHALL receive safe evidence refs without secrets or raw prompts.

### Requirement: Retry and requeue are explicit and audited
The system SHALL provide manual-first retry and requeue controls for eligible provider or media jobs.

#### Scenario: Admin retries failed job
- **Given** a failed provider-backed media job is eligible for retry
- **When** an admin retries it
- **Then** the retry SHALL be audited and linked to safe invocation/job evidence
- **And** duplicate hidden spend SHALL NOT occur.

### Requirement: Fallback and model switch are controlled
The system SHALL allow fallback or model switching only through configured opt-in policies with capability, quota, and audit checks. Automatic fallback SHALL remain disabled unless a checkpoint explicitly approves the policy and evidence model.

#### Scenario: Fallback selected
- **Given** a primary provider is degraded and a compatible fallback is configured
- **When** execution uses the fallback
- **Then** the system SHALL record safe evidence of the model/provider switch
- **And** world state SHALL NOT be corrupted or cross-worldline mutated.
