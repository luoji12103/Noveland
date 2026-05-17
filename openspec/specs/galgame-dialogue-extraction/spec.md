# Galgame Dialogue Extraction Specification

## Purpose
This spec captures the current v0.9 galgame script dialogue extraction behavior on `main`. It covers deterministic extraction, manual-label fallback, source traceability, proposal-only output, and optional provider-backed extraction through the provider kernel.

## Requirements
### Requirement: Script extraction creates reviewable dialogue proposals
The system SHALL extract dialogue, narration, speaker candidates, scene candidates, choices, route markers, emotion hints, and relationship hints as reviewable proposals.

#### Scenario: Sample script extraction
- **Given** a source fragment contains simple script dialogue
- **When** extraction runs
- **Then** the system SHALL produce proposal records for speaker candidate, line text, scene candidate, route marker, and optional emotion or relationship hints
- **And** the proposals SHALL preserve source fragment traceability.

### Requirement: Unknown formats keep manual labeling paths
The system SHALL preserve raw source fragments and allow manual labeling when deterministic parsing cannot recognize the format.

#### Scenario: Unknown script syntax
- **Given** a script file uses an unknown format
- **When** extraction runs
- **Then** the system SHALL keep the source fragment available for admin review
- **And** it SHALL create uncertainty or manual-label proposals rather than silently discarding content.

### Requirement: Provider-backed extraction remains optional and ledger-backed
The system SHALL use provider-backed extraction only when explicitly scoped and SHALL record invocation and prompt snapshot evidence through the provider kernel.

#### Scenario: Optional provider extraction
- **Given** an authorized operator enables provider extraction for a source batch
- **When** the extraction agent runs
- **Then** the call SHALL use `ProviderExecutionService`
- **And** provider output SHALL create proposals only, not direct memory or canon writes.
