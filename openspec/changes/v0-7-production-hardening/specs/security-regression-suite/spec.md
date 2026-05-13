# Security Regression Suite

## Capability

Add regression coverage for secret leak, prompt leak, storage_uri/path leak, ACL leak, and worldline isolation. This capability belongs to v0.7 Production Hardening and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Security Regression Suite provides the planned workflow
The system SHALL provide Security Regression Suite capability for Security regression tests, Leak fixtures, ACL test matrix while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Security Regression Suite
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse Phase 13 fixture, authorization tests, multimodal diagnostics rather than creating a parallel subsystem.

### Requirement: Security Regression Suite preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Security Regression Suite, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Security Regression Suite reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Security Regression Suite has explicit acceptance evidence
The system SHALL provide focused validation for Security Regression Suite and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Security Regression Suite is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Full external penetration test program
