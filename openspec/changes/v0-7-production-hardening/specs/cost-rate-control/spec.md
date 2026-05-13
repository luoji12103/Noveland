# Cost & Rate Control

## Capability

Add per-world budgets, per-provider budgets, media generation budgets, emergency stop, and quota status. This capability belongs to v0.7 Production Hardening and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Cost & Rate Control provides the planned workflow
The system SHALL provide Cost & Rate Control capability for Budget model, Rate limits, Emergency disable switches while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Cost & Rate Control
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse model_invocations, media_jobs, provider integrations, asset generation policies rather than creating a parallel subsystem.

### Requirement: Cost & Rate Control preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Cost & Rate Control, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Cost & Rate Control reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Cost & Rate Control has explicit acceptance evidence
The system SHALL provide focused validation for Cost & Rate Control and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Cost & Rate Control is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Complex billing marketplace
