# Release Candidate Gate

## ADDED Requirements

### Requirement: RC gate aggregates normal-use evidence
The system SHALL aggregate operational runbook, backup/restore, stress, safety/moderation, import/export, provider reliability, user-facing polish, and prior readiness evidence into a release-candidate report.

#### Scenario: RC evidence complete
- **Given** all required normal-use evidence is present
- **When** an admin runs the RC gate
- **Then** the report SHALL show release-candidate pass status with safe evidence summaries and any warnings.

### Requirement: RC gate blocks critical missing evidence
The system SHALL fail RC readiness when critical operational, backup, safety, stress, import/export, provider, UX, or leak evidence is missing.

#### Scenario: Backup restore missing
- **Given** no successful backup/restore drill evidence exists
- **When** the RC gate runs
- **Then** the gate SHALL fail with an actionable blocker.

### Requirement: RC gate does not auto-launch
The system SHALL distinguish release-candidate readiness from automatic public launch.

#### Scenario: RC gate passes
- **Given** the RC gate passes
- **When** public release is considered
- **Then** the system SHALL NOT automatically publicize worlds or enable unauthenticated access.

### Requirement: RC gate distinguishes readiness tiers
The system SHALL distinguish self-use MVP, private beta, normal use, release candidate, and public launch readiness.

#### Scenario: Private beta gate passed but RC evidence is missing
- **Given** private beta readiness has passed
- **When** the RC gate evaluates a world without backup/restore, stress, provider reliability, import/export, and polish evidence
- **Then** the RC gate SHALL fail with actionable blockers
- **And** it SHALL NOT treat private beta readiness as release-candidate readiness.

## Non-goals

- Automatic public launch.
- Duplicate readiness framework.
- Marketplace readiness.
