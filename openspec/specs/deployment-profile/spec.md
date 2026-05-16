# Deployment Profile Specification

## Purpose

This spec captures the current v0.7 local/single-host deployment profile on `main`. It covers supported local deployment expectations, startup/config checks, compose validation, and operator documentation without cloud lock-in.
## Requirements
### Requirement: Deployment profile is explicit
The system SHALL document the supported production-like deployment shape, required environment variables, startup order, health checks, backup prerequisites, migration commands, and rollback guidance.

#### Scenario: Operator prepares deployment
- **Given** the operator is preparing a local/single-host production-like deployment
- **When** they follow the deployment profile
- **Then** the profile SHALL identify API, database, NATS, object storage, migrations, provider env refs, and backup readiness
- **And** it SHALL distinguish internal readiness from public launch readiness.

### Requirement: Health checks are safe
The system SHALL expose or document health checks that reveal operational status without exposing secrets or admin-only evidence.

#### Scenario: Health endpoint is requested
- **Given** a health check endpoint or command runs
- **When** it reports API, dependency, provider, migration, or storage status
- **Then** it SHALL return safe status, not resolved secrets, storage paths, raw prompts, raw outputs, bytes, or base64.

### Requirement: Deployment validation is local and repeatable
The system SHALL validate deployment configuration with local commands and no managed-cloud lock-in.

#### Scenario: Deployment profile validation runs
- **Given** the repository is checked out locally
- **When** validation runs
- **Then** it SHALL include compose config validation and any accepted health/config checks
- **And** it SHALL NOT require Kubernetes, managed cloud services, or public CDN configuration.

### Requirement: Deployment Profile preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for deployment profile work.

#### Scenario: Boundary enforcement
- **Given** deployment profile work reads provider, media, invocation, visual, speech, event, presentation, diagnostics, or storage data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Deployment Profile has explicit acceptance evidence
The system SHALL provide focused validation and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Deployment Profile is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Managed cloud platform lock-in.
- Kubernetes orchestration.
- Autoscaling.
- Public launch checklist.
