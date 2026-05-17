# Private Beta Gate

## ADDED Requirements

### Requirement: Private beta gate ownership is decided before implementation
The system SHALL complete a docs-only checkpoint before implementing the private beta gate.
The checkpoint SHALL confirm that the gate extends existing observability/readiness aggregation
unless a specific signoff record is approved.

#### Scenario: Gate checkpoint runs
- **Given** v1.0 Phase 8 is selected for implementation
- **When** the checkpoint is written
- **Then** it SHALL define private beta gate ownership, evidence sources, and report redaction
- **And** it SHALL reject duplicate readiness frameworks.

### Requirement: Private beta gate aggregates required evidence
The system SHALL aggregate evidence from onboarding, setup wizard, session stability, memory/persona QA, feedback, quota enforcement, and content iteration before marking a world private-beta-ready.

#### Scenario: Complete beta evidence
- **Given** all required private beta evidence is present
- **When** an admin runs the private beta gate
- **Then** the gate SHALL report pass status for 1-3 invited testers and 1-2 hour test sessions
- **And** it SHALL include safe blocker and warning summaries.

### Requirement: Private beta gate validates tester-session evidence
The system SHALL require evidence that 1-3 invited testers can complete 1-2 hour sessions without
developer intervention, hidden spend, unrecoverable state, or critical persona/memory blockers.

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

## Non-goals

- Public launch gate.
- Normal-use release candidate gate.
- Duplicate release framework.
