# World Setup Wizard Specification

## Purpose
This spec captures the current v1.0 private beta world setup readiness behavior on `main`. It covers admin-only setup aggregation over existing observability/readiness evidence for access, sessions, quota, providers, media, visual, voice, persona, memory, source traceability, and self-use MVP evidence.

## Requirements
### Requirement: Setup wizard extends readiness rather than duplicating it
The system SHALL implement the setup wizard as an aggregation over existing readiness, diagnostics, provider, media, visual, speech, memory, authoring, private beta access, session, quota, and self-use evidence unless a checkpoint explicitly approves a persistent signoff record.

#### Scenario: Setup wizard report is requested
- **Given** a platform admin requests private beta setup readiness for a world
- **When** the report is generated
- **Then** it SHALL return `readiness_kind=private_beta_world_setup`
- **And** it SHALL reuse existing readiness section/evidence DTOs
- **And** it SHALL NOT create setup wizard run/report tables.

### Requirement: Setup wizard validates beta world completeness
The system SHALL aggregate setup evidence for provider readiness, media availability, voice bindings, persona/memory readiness, visual mappings, scene/playback readiness, beta access, player session restore, quota enforcement, and prior self-use evidence.

#### Scenario: World is incomplete
- **Given** a beta world lacks a required voice binding or persona memory
- **When** an admin runs the setup wizard
- **Then** the wizard SHALL report a blocker with actionable remediation
- **And** it SHALL NOT mark the world beta-ready.

#### Scenario: Session or quota evidence is missing
- **Given** a beta world has provider and content evidence but lacks session restore or quota evidence
- **When** an admin runs the setup wizard
- **Then** the wizard SHALL report a blocker
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

### Requirement: Setup wizard evidence is redacted
The system SHALL expose only safe setup evidence references and summaries.

#### Scenario: Setup evidence contains internal fields
- **Given** setup evidence is linked to invites, providers, media, prompt snapshots, source fragments, or world events
- **When** the setup report is returned
- **Then** it SHALL suppress invite tokens, token hashes, resolved secrets, storage paths, object paths, bytes, base64, raw prompts, raw outputs, prompt snapshot internals, raw source fragments, local model paths, and raw workflow JSON.

## Non-goals

- Automatic setup repair.
- Public launch readiness replacement.
- Duplicate readiness framework.
