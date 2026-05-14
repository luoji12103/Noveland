# Authoring Regression Fixture

## Capability

Create a small galgame import fixture for regression of scripts, characters, relationships, assets, and memory migration. This capability belongs to v0.5 Authoring & Import Studio and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Authoring Regression Fixture provides the planned workflow
The system SHALL provide Authoring Regression Fixture capability for Script fixture, Character fixture, Relationship fixture, Asset fixture, Memory migration fixture while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Authoring Regression Fixture
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse test fixture patterns, multimodal sample-world regression, and the Phase 1 authoring import core rather than creating a parallel subsystem.

### Requirement: Authoring Regression Fixture preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Authoring Regression Fixture, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Authoring Regression Fixture reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Authoring Regression Fixture has explicit acceptance evidence
The system SHALL provide focused validation for Authoring Regression Fixture and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Authoring Regression Fixture is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Production seed framework
- Quality benchmark for all content
