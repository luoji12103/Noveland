# Observability & Incident Diagnostics

## Capability

Expose safe incident diagnostics and retention controls over provider, media, runtime, eval, cost, and narrative quality evidence. This capability belongs to v0.7 Production Hardening and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Incident summaries use safe evidence refs
The system SHALL aggregate incident context from existing diagnostics and ledgers without exposing raw operational payloads.

#### Scenario: Admin reviews incident summary
- **Given** provider failures, media job failures, model invocation failures, budget blocks, eval blockers, or runtime diagnostics exist
- **When** an authorized admin requests an incident summary
- **Then** the response SHALL include safe counts, status, timestamps, and evidence refs
- **And** it SHALL NOT include resolved secrets, raw prompts, raw outputs, storage paths, bytes, or base64.

### Requirement: Failure replay avoids unsafe payloads
The system SHALL support failure replay metadata only where safe and SHALL not expose raw provider requests, raw provider responses, prompt snapshots, or storage payloads through lower-privilege or public routes.

#### Scenario: Failure replay metadata is requested
- **Given** an invocation or job failed
- **When** replay or diagnostic metadata is returned
- **Then** it SHALL identify the component, safe reason, status, and evidence refs
- **And** it SHALL omit raw prompt/output, authorization headers, resolved secrets, storage_uri, filesystem paths, bytes, and base64.

### Requirement: Diagnostic retention is explicit
The system SHALL provide or document diagnostic retention dry-run and prune behavior for accepted diagnostic records.

#### Scenario: Retention dry-run is requested
- **Given** runtime diagnostics exist
- **When** an authorized admin runs a retention dry-run
- **Then** the system SHALL return pruneable and retained counts
- **And** it SHALL not delete records unless an explicit prune action is accepted and authorized.

### Requirement: Observability & Incident Diagnostics preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for observability work.

#### Scenario: Boundary enforcement
- **Given** observability reads or writes provider, media, invocation, visual, speech, event, presentation, eval, or narrative quality data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Observability & Incident Diagnostics has explicit acceptance evidence
The system SHALL provide focused validation and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Observability & Incident Diagnostics is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- External observability exporter
- Real-time incident Web dashboard
- Raw prompt/output replay
- Public/member incident routes
