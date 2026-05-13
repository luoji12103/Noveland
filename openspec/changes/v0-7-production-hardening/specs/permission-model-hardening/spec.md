# Permission Model Hardening

## Capability

Establish owner/admin/member/reader/player permission matrix. This capability belongs to v0.7 Production Hardening and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Permission Model Hardening provides the planned workflow
The system SHALL provide Permission Model Hardening capability for ACL matrix, Route-level permissions, Admin vs reader/player separation while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Permission Model Hardening
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse auth services, API authorization dependencies, current route tests rather than creating a parallel subsystem.

### Requirement: Permission Model Hardening preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Permission Model Hardening, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Permission Model Hardening reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Permission Model Hardening has explicit acceptance evidence
The system SHALL provide focused validation for Permission Model Hardening and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Permission Model Hardening is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- New public launch routes
