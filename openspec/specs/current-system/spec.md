# Current System Specification

## Purpose

This spec captures the current Noveland system behavior on `main` after Phase 3-13 and archived v0.4, v0.5, and v0.8 work. It summarizes the implemented backend/Web surface and points to narrower specs for architecture, providers, media, multimodal flows, authoring, admin UX, and public experience capabilities.

## Requirements

### Requirement: Repository separates product surfaces and backend packages
The system SHALL keep backend domain logic in backend packages, API routing in `backend/services/api`, Web UI/client logic in `web`, deployment wiring in `infra`, and engineering documentation in `docs/agent` and `openspec`.

#### Scenario: Package boundary review
- **GIVEN** a maintainer is locating provider, media, speech, visual, conversation, or eval code
- **WHEN** they inspect the repository layout
- **THEN** the owning backend package SHALL contain the domain service and contracts for that capability
- **AND** API routers SHALL delegate to those services instead of owning domain logic.

### Requirement: Backend API composes world, runtime, conversation, provider, media, and multimodal routers
The system SHALL expose backend routers for auth, runtime, worlds, media, images, speech, visual assets, asset generation, multimodal evals, model invocations, providers, conversations, conversation presentations, and realtime streams from the API app.

#### Scenario: API app router inventory
- **GIVEN** the API application is created
- **WHEN** router registration is inspected
- **THEN** each current route module SHALL be included from `backend/services/api/src/noveland/services/api/app.py`
- **AND** multimodal routes SHALL be separate modules instead of being folded into `worlds.py`.

### Requirement: Web app exposes existing product and admin surfaces
The system SHALL provide Web routes for world lists, world detail, agents, conversations, narrative workspace, narrative reader, login, runtime admin, provider admin, presets, memory backends, public reader/player playback surfaces, player privacy controls, worldline browsing, and API proxy routes.

#### Scenario: Web route inventory
- **GIVEN** a user navigates the current Next.js app
- **WHEN** they use existing pages under `web/app`
- **THEN** the app SHALL serve current world, agent, conversation, narrative, reader/player, auth, runtime, provider, preset, memory admin, playback, scene, privacy, and worldline surfaces
- **AND** it SHALL not imply direct storage delivery, public unauthenticated media access, or admin-only diagnostics in reader/player routes.

### Requirement: Full local gate is the acceptance authority
The system SHALL rely on the local backend, Web, infra, and diff checks as the primary acceptance gate because the project currently has no GitHub CI requirement.

#### Scenario: Release readiness check
- **GIVEN** a phase implementation claims completion
- **WHEN** the full local gate is run
- **THEN** backend lint, typecheck, and tests SHALL pass
- **AND** Web lint, typecheck, tests, build, Next env check, and e2e tests SHALL pass
- **AND** compose config plus `git diff --check` SHALL pass.

### Requirement: Architecture freeze fixture exists for multimodal regression
The system SHALL include a deterministic backend sample-world fixture and regression test proving that provider, invocation, media, visual, speech, conversation presentation, asset generation, and diagnostics records compose safely.

#### Scenario: Sample fixture regression
- **GIVEN** the sample-world regression test runs
- **WHEN** it creates fixture data
- **THEN** all created worldline-scoped records SHALL use the same primary worldline
- **AND** visual resolvers, background resolvers, presentation references, media object checksums, provider secret redaction, and diagnostics SHALL pass.

## Non-goals

- This spec does not define proposed behavior that has not been archived into current specs.
- This spec does not add implementation tasks.
- This spec does not replace detailed package specs or ADRs.
- This spec does not require Web support for visual/audio preview beyond existing surfaces.
