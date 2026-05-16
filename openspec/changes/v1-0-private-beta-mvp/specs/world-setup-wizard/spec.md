# World Setup Wizard

## ADDED Requirements

### Requirement: Setup wizard validates beta world completeness
The system SHALL aggregate setup evidence for provider readiness, media availability, voice bindings, persona/memory readiness, visual mappings, scene/playback readiness, and prior self-use evidence.

#### Scenario: World is incomplete
- **Given** a beta world lacks a required voice binding or persona memory
- **When** an admin runs the setup wizard
- **Then** the wizard SHALL report a blocker with actionable remediation
- **And** it SHALL NOT mark the world beta-ready.

### Requirement: Setup wizard reuses readiness evidence
The system SHALL reuse existing readiness, diagnostics, provider, media, visual, speech, memory, and self-use evidence rather than creating a duplicate readiness framework.

#### Scenario: Existing diagnostics are available
- **Given** multimodal diagnostics and provider health checks exist
- **When** the setup wizard runs
- **Then** it SHALL reference safe evidence summaries from those systems
- **And** it SHALL NOT copy raw prompt/output or storage path details into the report.

### Requirement: Setup wizard is admin-scoped
The system SHALL keep setup reports admin-scoped by default.

#### Scenario: Player requests setup report
- **Given** a private beta player requests setup wizard data
- **When** authorization is evaluated
- **Then** the system SHALL deny admin-only setup details
- **And** it MAY return only player-safe readiness status if explicitly supported.

## Non-goals

- Automatic setup repair.
- Public launch readiness replacement.
- Duplicate readiness framework.
