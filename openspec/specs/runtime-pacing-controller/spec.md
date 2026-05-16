# Runtime Pacing Controller Specification

## Purpose

This spec captures the current v0.6 admin-only runtime pacing diagnostic capability on `main`. It covers media-job pressure, asset generation budget pressure, lookahead coverage, current-turn gaps, offscreen compression opportunities, and safe recommendations without mutations.

## Requirements
### Requirement: Runtime Pacing Controller provides the current workflow
The system SHALL provide Runtime Pacing Controller capability for Pacing policy, Lookahead limits, Offscreen compression while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Runtime Pacing Controller
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the implemented pacing diagnostic scope
- **And** the workflow SHALL reuse runtime services, asset generation policies, media jobs rather than creating a parallel subsystem.

### Requirement: Runtime Pacing Controller preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Runtime Pacing Controller, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Runtime Pacing Controller reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Runtime Pacing Controller has explicit acceptance evidence
The system SHALL provide focused validation for Runtime Pacing Controller and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Runtime Pacing Controller is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Unbounded pre-generation.
- Daemon auto-generation without accepted spec.
- Media job mutation or provider execution from pacing review.
