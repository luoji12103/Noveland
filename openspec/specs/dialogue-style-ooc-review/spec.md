# Dialogue Style & OOC Review Specification

## Purpose

This spec captures the current v0.6 admin-only dialogue style and out-of-character review capability on `main`. It covers style consistency checks, OOC signals, safe findings, and reuse of conversation turns, agent profiles, and invocation ledger evidence.

## Requirements
### Requirement: Dialogue Style & OOC Review provides the current workflow
The system SHALL provide Dialogue Style & OOC Review capability for Dialogue review service, OOC signal, Style consistency score while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Dialogue Style & OOC Review
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the implemented dialogue review scope
- **And** the workflow SHALL reuse conversation turns, agent profiles, invocation ledger rather than creating a parallel subsystem.

### Requirement: Dialogue Style & OOC Review preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Dialogue Style & OOC Review, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Dialogue Style & OOC Review reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Dialogue Style & OOC Review has explicit acceptance evidence
The system SHALL provide focused validation for Dialogue Style & OOC Review and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Dialogue Style & OOC Review is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Blocking all dialogue generation by default.
- Automatic rewrite or repair apply.
- Reader/member exposure of admin-only style evidence.
