# Secret & Provider Governance Specification

## Purpose

This spec captures the current v0.7 secret and provider governance capability on `main`. It covers disabled-provider execution blocking, opaque `auth_ref` rotation, safe provider audit evidence, and provider boundary reuse.
## Requirements
### Requirement: Disabled providers cannot execute
The system SHALL enforce provider disabled/deleted status at every provider execution boundary.

#### Scenario: Disabled provider is selected
- **Given** a provider integration exists but is not active
- **When** an image, speech, provider smoke/test, narrative quality, or other provider-backed workflow tries to execute it
- **Then** the system SHALL block before the external provider call
- **And** it SHALL return an actionable safe error and safe audit evidence.

### Requirement: Secret rotation keeps auth_ref opaque
The system SHALL treat provider credentials as opaque `auth_ref` references resolved only at execution time.

#### Scenario: Admin rotates a provider auth_ref
- **Given** a world admin or platform admin updates provider authentication
- **When** the provider record is saved
- **Then** the persisted value SHALL be only an auth reference such as `env:...` or `secret:...`
- **And** no resolved API key, token, password, bearer token, client secret, access key, or private key SHALL be stored or returned.

### Requirement: Provider audit evidence is safe
The system SHALL record provider governance evidence without leaking resolved secrets, request headers, raw prompt snapshots, storage paths, bytes, or base64.

#### Scenario: Provider health or execution fails
- **Given** provider execution or health checking fails due to auth, network, timeout, rate limit, malformed response, or unsupported capability
- **When** health, diagnostics, invocation, or audit evidence is recorded
- **Then** evidence SHALL include safe status and reason codes
- **And** it SHALL NOT include resolved secrets, authorization headers, raw provider payloads, or filesystem paths.

### Requirement: Secret & Provider Governance preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for provider governance.

#### Scenario: Boundary enforcement
- **Given** provider governance reads or writes provider, media, invocation, speech, image, narrative quality, event, or diagnostic data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Secret & Provider Governance has explicit acceptance evidence
The system SHALL provide focused validation and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Secret & Provider Governance is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Provider marketplace.
- Resolved secret exposure.
- Full vault/KMS implementation.
- Client-side secret management UI.
