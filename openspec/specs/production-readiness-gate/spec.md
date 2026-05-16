# Production Readiness Gate Specification

## Purpose

This spec captures the current v0.7 internal production readiness gate on `main`. It covers aggregation of existing beta, release, eval, diagnostic, provider, media, storage, cost, ACL, and security regression evidence without duplicating the release framework.
## Requirements
### Requirement: Readiness gate reuses existing evidence
The system SHALL aggregate existing beta, release, eval, diagnostics, provider, media, storage, cost, ACL, and security regression evidence rather than creating a duplicate release framework.

#### Scenario: Admin runs readiness gate
- **Given** v0.7 hardening evidence exists for a world or deployment profile
- **When** an authorized admin runs the readiness gate
- **Then** the gate SHALL aggregate provider governance, budget status, storage integrity, deployment profile, diagnostics, security regression, beta checklist, long-run eval, multimodal eval, and narrative quality evidence where available
- **And** it SHALL return actionable blockers and recommendations.

### Requirement: Readiness gate is internal-only
The system SHALL keep production readiness distinct from public launch readiness and SHALL not expose readiness internals to reader/member/player routes.

#### Scenario: Reader requests readiness report
- **Given** a readiness report exists
- **When** a reader, member, or player-visible route attempts to access it
- **Then** the system SHALL reject the request or return only a safe public projection accepted by a future change
- **And** it SHALL NOT leak admin-only evidence.

### Requirement: Operator signoff is safe
The system SHALL record operator signoff only if the accepted implementation scope defines a safe write path and storage model.

#### Scenario: Operator records signoff
- **Given** a readiness report has blockers and recommendations
- **When** an authorized operator records signoff
- **Then** the signoff SHALL store actor reference, timestamp, and safe notes only
- **And** it SHALL NOT store raw prompts, raw outputs, resolved secrets, storage paths, bytes, or base64.

### Requirement: Production Readiness Gate preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for readiness gate work.

#### Scenario: Boundary enforcement
- **Given** the readiness gate reads or writes provider, media, invocation, visual, speech, event, presentation, authoring, eval, diagnostics, or narrative quality data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Production Readiness Gate has explicit acceptance evidence
The system SHALL provide focused validation and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Production Readiness Gate is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Public launch gate.
- Marketing/release workflow.
- External compliance certification.
- Blocking every runtime path.
