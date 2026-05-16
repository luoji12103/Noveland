# Long-run Living World Simulation Eval

## Capability

Run multi-day/multi-turn simulations to detect character drift, narrative breaks, and world state pollution. This capability belongs to v0.6 Runtime Narrative Quality and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Long-run Living World Simulation Eval provides the planned workflow
The system SHALL provide Long-run Living World Simulation Eval capability for Long-run eval scenario, Drift metrics, Failure reports while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Long-run Living World Simulation Eval
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse LongRunEvalRun, multimodal eval service, runtime diagnostics rather than creating a parallel subsystem.

### Requirement: Long-run Living World Simulation Eval preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Long-run Living World Simulation Eval, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Long-run Living World Simulation Eval reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Long-run Living World Simulation Eval has explicit acceptance evidence
The system SHALL provide focused validation for Long-run Living World Simulation Eval and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Long-run Living World Simulation Eval is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- External observability platform
- Human scoring system
