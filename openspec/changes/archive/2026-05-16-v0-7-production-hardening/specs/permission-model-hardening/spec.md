# Permission Model Hardening

## Capability

Establish a concrete owner/admin/member/reader/player permission matrix for the current v0.4-v0.6 route surface. This capability belongs to v0.7 Production Hardening and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Permission matrix is explicit
The system SHALL document and test the expected access level for platform-admin, world-admin, world-member, reader, and player-facing API workflows.

#### Scenario: Route matrix is reviewed
- **Given** the v0.4-v0.6 admin and API route surface exists
- **When** v0.7 Permission Model Hardening begins
- **Then** the implementation SHALL create or update a route permission matrix
- **And** the matrix SHALL identify admin-only evidence, member-safe reads, reader-safe reads, player-private data, and unauthenticated endpoints.

### Requirement: Lower-privilege routes suppress admin evidence
The system SHALL prevent lower-privilege actors from reading prompt snapshots, raw prompts, raw outputs, resolved secret details, hidden/developer-only media, storage paths, and admin-only diagnostic evidence.

#### Scenario: Reader requests admin evidence
- **Given** a reader or player-visible route can identify a world or worldline
- **When** the actor requests provider, invocation, media, diagnostic, authoring, or narrative quality evidence
- **Then** the route SHALL reject the request or return a reader-safe projection
- **And** the response SHALL NOT include prompt snapshots, raw prompts, raw outputs, storage_uri, filesystem paths, resolved secrets, bytes, or base64.

### Requirement: Admin-only v0.5/v0.6 APIs remain admin-scoped
The system SHALL keep authoring/import and narrative quality APIs scoped to authorized admins unless a later accepted change defines a safe public projection.

#### Scenario: World member calls admin-only diagnostics
- **Given** a world member is authenticated but is not a world admin or platform admin
- **When** they call authoring/import review APIs or narrative quality diagnostics
- **Then** the API SHALL return forbidden
- **And** it SHALL NOT leak whether hidden evidence exists.

### Requirement: Permission Model Hardening preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for permission hardening.

#### Scenario: Boundary enforcement
- **Given** permission hardening reads provider, media, invocation, visual, speech, event, presentation, authoring, or narrative quality data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Permission Model Hardening has explicit acceptance evidence
The system SHALL provide focused validation and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Permission Model Hardening is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- New public launch routes
- New role hierarchy UI
- Large auth schema redesign unless explicitly accepted
