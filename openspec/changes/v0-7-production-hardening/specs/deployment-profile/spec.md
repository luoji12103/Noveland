# Deployment Profile

## Capability

Define production compose/profile, health endpoints, migration procedure, and operator docs. This capability belongs to v0.7 Production Hardening and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Deployment Profile provides the planned workflow
The system SHALL provide Deployment Profile capability for Production deployment docs, Compose profile, Health checks while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Deployment Profile
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse infra compose, health API, migration config rather than creating a parallel subsystem.

### Requirement: Deployment Profile preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Deployment Profile, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Deployment Profile reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Deployment Profile has explicit acceptance evidence
The system SHALL provide focused validation for Deployment Profile and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Deployment Profile is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Managed cloud platform lock-in
