# Public Launch Gate

## Capability

Define public launch readiness that depends on v0.7 internal production readiness and adds public, privacy, moderation, media, and sample-world evidence. This capability belongs to v0.8 Public Experience & Ecosystem and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Public launch gate reuses internal production readiness
The system SHALL aggregate v0.7 internal production readiness instead of replacing it with a duplicate release framework.

#### Scenario: Internal readiness has blockers
- **Given** the v0.7 production readiness report has blockers
- **When** public launch readiness is evaluated
- **Then** the public launch gate SHALL fail
- **And** it SHALL reference internal readiness blockers safely.

### Requirement: Public launch gate adds public-surface evidence
The system SHALL include reader media delivery, playback/scene UI, privacy controls, moderation workflow, sample package, and packaging evidence in public readiness.

#### Scenario: Missing moderation signoff
- **Given** production readiness passes
- **When** moderation signoff is missing
- **Then** the public launch gate SHALL report a public launch blocker.

### Requirement: Public launch requires explicit signoff
The system SHALL NOT automatically launch a world or public surface solely because tests pass.

#### Scenario: Checks pass but signoff missing
- **Given** automated readiness checks pass
- **When** public launch status is requested
- **Then** the status SHALL remain blocked or pending until explicit signoff is recorded.

### Requirement: Public launch gate has explicit acceptance evidence
The implementation SHALL include readiness, blocker, ACL, signoff, and evidence-redaction tests.

#### Scenario: Phase acceptance
- **Given** Public Launch Gate implementation is complete
- **When** targeted tests and the full local gate run
- **Then** all checks SHALL pass before fast-forward merge.

## Non-goals

- Skipping v0.7 production readiness.
- Automatic public launch.
- Duplicate release/readiness framework.
