# Security Regression Suite

## Capability

Add consolidated regression coverage for secret leaks, prompt/output leaks, storage/path leaks, ACL leaks, and worldline isolation after the earlier v0.7 hardening phases. This capability belongs to v0.7 Production Hardening and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Forbidden payload fixtures are covered
The system SHALL include regression fixtures that fail if secrets, raw prompts/outputs, storage paths, storage_uri, bytes, base64, or unsafe world event payloads leak through protected surfaces.

#### Scenario: Leak fixture is introduced
- **Given** a fixture contains forbidden secret-like, prompt-like, or storage-like content
- **When** security regression tests exercise admin-safe and lower-privilege routes
- **Then** lower-privilege routes SHALL reject or sanitize the content
- **And** admin-safe routes SHALL expose only safe evidence refs or redacted summaries.

### Requirement: ACL matrix is regression-tested
The system SHALL test the expected route matrix for platform-admin, world-admin, world-member, reader, and player-facing actors.

#### Scenario: Actor calls a route outside their role
- **Given** an authenticated actor has insufficient role for an admin-only route
- **When** they call provider, invocation, media admin, authoring, narrative quality, observability, or readiness APIs
- **Then** the API SHALL return forbidden or a safe projection
- **And** it SHALL NOT leak hidden evidence existence.

### Requirement: Worldline isolation is regression-tested
The system SHALL detect cross-worldline access or binding mistakes in multimodal, authoring, narrative quality, and readiness flows.

#### Scenario: Cross-worldline reference is used
- **Given** a record from one worldline is used in a request for another worldline
- **When** the request touches media, visual, conversation presentation, authoring proposal, narrative quality, or eval records
- **Then** the system SHALL reject the request or report a blocker
- **And** no canonical state SHALL be mutated.

### Requirement: Security Regression Suite preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for security regression work.

#### Scenario: Boundary enforcement
- **Given** security regression reads or writes provider, media, invocation, visual, speech, event, presentation, authoring, eval, or narrative quality data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Security Regression Suite has explicit acceptance evidence
The system SHALL provide focused validation and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Security Regression Suite is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Full external penetration test program
- SAST/DAST platform rollout
- Public bug bounty process
