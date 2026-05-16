# Continuity Review v2 Specification

## Purpose

This spec captures the current v0.6 admin-only Continuity Review v2 capability on `main`. It covers continuity diagnostics, conflict reports, safe repair suggestions, worldline-aware review, and reuse of existing guardrail, event, route, relationship, and multimodal diagnostic records.

## Requirements
### Requirement: Continuity Review v2 provides the current workflow
The system SHALL provide Continuity Review v2 capability for Continuity diagnostics, Conflict reports, Repair suggestions while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Continuity Review v2
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the implemented continuity review scope
- **And** the workflow SHALL reuse world events, relationship/route records, multimodal diagnostics rather than creating a parallel subsystem.

### Requirement: Continuity Review v2 preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Continuity Review v2, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Continuity Review v2 reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Continuity Review v2 has explicit acceptance evidence
The system SHALL provide focused validation for Continuity Review v2 and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Continuity Review v2 is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Automatic repair apply.
- Provider execution during continuity review.
- Reader/member exposure of admin-only continuity evidence.
