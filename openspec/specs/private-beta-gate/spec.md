# Private Beta Gate Specification

## Purpose
This spec captures the current v1.0 private beta readiness gate on `main`. It covers admin-only readiness aggregation for invite-only beta use, setup, session restore, quota, memory/persona QA, feedback, repair-loop evidence, manual 1-2 hour tester-session evidence, no-leak checks, and the boundary that private beta readiness is not public launch readiness.

## Requirements
### Requirement: Private beta gate aggregates required evidence
The system SHALL aggregate evidence from onboarding, setup wizard, session stability, memory/persona QA, feedback, quota enforcement, and content iteration before marking a world private-beta-ready.

#### Scenario: Complete beta evidence
- **Given** all required private beta evidence is present
- **When** an admin runs the private beta gate
- **Then** the gate SHALL report pass status for 1-3 invited testers and 1-2 hour test sessions
- **And** it SHALL include safe blocker and warning summaries.

### Requirement: Private beta gate validates tester-session evidence
The system SHALL require evidence that 1-3 invited testers can complete 1-2 hour sessions without developer intervention, hidden spend, unrecoverable state, or critical persona/memory blockers.

#### Scenario: Tester-session evidence missing
- **Given** onboarding, provider, and content checks pass but no tester-session evidence exists
- **When** an admin runs the private beta gate
- **Then** the gate SHALL fail with an actionable blocker
- **And** it SHALL NOT authorize broad tester rollout.

### Requirement: Private beta gate blocks unsafe readiness
The system SHALL fail private beta readiness when required privacy, quota, feedback, session, provider, memory, or leak checks are missing.

#### Scenario: Quota evidence missing
- **Given** a world lacks quota enforcement evidence
- **When** the private beta gate runs
- **Then** it SHALL fail with an actionable blocker
- **And** it SHALL NOT authorize broad tester rollout.

### Requirement: Private beta gate is not public launch
The system SHALL distinguish private beta readiness from public launch readiness.

#### Scenario: Private beta passes
- **Given** the private beta gate passes
- **When** public launch readiness is requested
- **Then** the system SHALL still require later public or release-candidate checks.

### Requirement: Private beta gate reuses observability readiness
The system SHALL implement private beta readiness as an observability/readiness report rather than as a duplicate gate framework.

#### Scenario: Private beta gate report is requested
- **Given** a platform admin requests private beta readiness
- **When** the report is generated
- **Then** it SHALL return `readiness_kind=private_beta_gate`
- **And** it SHALL reuse existing readiness section/evidence DTOs
- **And** it SHALL NOT create private beta gate run/report tables.

## Non-goals

- Public launch gate.
- Normal-use release candidate gate.
- Duplicate release framework.
