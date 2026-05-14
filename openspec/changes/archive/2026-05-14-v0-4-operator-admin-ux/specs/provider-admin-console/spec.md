# Provider Admin Console

## Capability

Manage provider integrations, adapter_kind, capabilities, health checks, and smoke tests. This capability belongs to v0.4 Operator/Admin UX and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Provider Admin Console provides the planned workflow
The system SHALL provide Provider Admin Console capability for Provider list/detail, Capability view, Health-check history, Smoke-test action, auth_ref status display, Restricted visibility handling while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Provider Admin Console
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse ProviderRegistryService, ProviderHealthService, ProviderExecutionService, providers API rather than creating a parallel subsystem.

### Requirement: Provider Admin Console preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Provider Admin Console, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Provider Admin Console reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Provider Admin Console has explicit acceptance evidence
The system SHALL provide focused validation for Provider Admin Console and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Provider Admin Console is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Resolved secret display
- New provider adapters
- Provider execution kernel changes
