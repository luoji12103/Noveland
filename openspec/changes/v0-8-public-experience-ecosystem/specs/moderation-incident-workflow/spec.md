# Moderation & Incident Workflow

## Capability

Support reports, rollback, disable world/provider, and incident records. This capability belongs to v0.8 Public Experience & Ecosystem and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Moderation & Incident Workflow provides the planned workflow
The system SHALL provide Moderation & Incident Workflow capability for Reports, Incident records, Admin moderation flow while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Moderation & Incident Workflow
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse incident diagnostics, provider disable, worldline snapshots rather than creating a parallel subsystem.

### Requirement: Moderation & Incident Workflow preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Moderation & Incident Workflow, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Moderation & Incident Workflow reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Moderation & Incident Workflow has explicit acceptance evidence
The system SHALL provide focused validation for Moderation & Incident Workflow and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Moderation & Incident Workflow is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Automated public moderation without review
