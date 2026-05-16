# Cost & Rate Control Specification

## Purpose

This spec captures the current v0.7 cost and rate control capability on `main`. It covers provider-owned budget policy, quota status, emergency stop, and pre-call execution guards reused by provider-backed workflows.
## Requirements
### Requirement: Budget checks run before external calls
The system SHALL enforce accepted budget/rate policies before external provider calls or automatic media/narrative generation spend.

#### Scenario: Provider execution exceeds budget
- **Given** a world or provider budget has been reached
- **When** a provider-backed image, speech, provider smoke/test, asset generation, or narrative quality workflow is requested
- **Then** the system SHALL block before the external provider call
- **And** it SHALL return safe quota status and a safe blocked-execution reason.

### Requirement: Quota status is admin-visible
The system SHALL expose quota and budget status to authorized admins using existing invocation, media job, provider, and asset generation evidence where possible.

#### Scenario: Admin reviews quota status
- **Given** model invocations, media jobs, provider integrations, and asset generation proposals exist for a world
- **When** an authorized admin requests quota status
- **Then** the response SHALL include safe aggregate counts/cost estimates
- **And** it SHALL NOT expose raw prompts, raw outputs, resolved secrets, storage paths, bytes, or base64.

### Requirement: Emergency stop is auditable
The system SHALL provide an emergency stop mechanism for provider-backed spend that is reversible by authorized admins and visible through safe audit evidence.

#### Scenario: Emergency stop is active
- **Given** an emergency stop is active for a world or provider
- **When** a provider-backed workflow is requested
- **Then** the workflow SHALL be blocked before execution
- **And** the block SHALL be visible in safe admin evidence without mutating canonical world state.

### Requirement: Cost & Rate Control preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for cost/rate controls.

#### Scenario: Boundary enforcement
- **Given** cost/rate control reads or writes provider, media, invocation, visual, speech, event, presentation, asset generation, or narrative quality data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Cost & Rate Control has explicit acceptance evidence
The system SHALL provide focused validation and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Cost & Rate Control is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Complex billing marketplace.
- Subscription management.
- Provider fallback/load balancing.
- Public user quota UX.
