# Multimodal Diagnostics Dashboard

## Capability

Visualize Phase 12 multimodal diagnostic results. This capability belongs to v0.4 Operator/Admin UX and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Multimodal Diagnostics Dashboard provides the planned workflow
The system SHALL provide Multimodal Diagnostics Dashboard capability for Diagnostics overview, Missing asset checks, Secret/storage/prompt leak checks, Provider health summary, Sample fixture status, Cost/latency summaries while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Multimodal Diagnostics Dashboard
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse MultimodalEvalService, long_run_eval_runs, provider/media/invocation diagnostics rather than creating a parallel subsystem.

### Requirement: Multimodal Diagnostics Dashboard preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Multimodal Diagnostics Dashboard, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Multimodal Diagnostics Dashboard reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Multimodal Diagnostics Dashboard has explicit acceptance evidence
The system SHALL provide focused validation for Multimodal Diagnostics Dashboard and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Multimodal Diagnostics Dashboard is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Diagnostics backend rule changes
- Public launch gate
