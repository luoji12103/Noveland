# Sample World Release Package Specification

## Purpose

This spec captures the current v0.8 sample world release package fixture on `main`. It covers deterministic package creation from the Phase 13 multimodal sample-world fixture, explicit rights/visibility metadata, packaging preview/apply validation, and leak regression evidence.

## Requirements
### Requirement: Sample package links to regression fixture
The system SHALL document and test how the release sample maps to the deterministic Phase 13 multimodal sample-world fixture.

#### Scenario: Fixture-linked package
- **Given** a sample release package is created
- **When** its manifest is inspected
- **Then** it SHALL identify the fixture linkage and expected records
- **And** it SHALL avoid real provider calls during deterministic validation.

### Requirement: Sample package has explicit content rights and visibility
The system SHALL record rights, source, and visibility metadata for bundled content and media.

#### Scenario: Sample media visibility
- **Given** a sprite or background is included in the sample package
- **When** the package manifest is generated
- **Then** the asset visibility and rights metadata SHALL be explicit
- **And** unlicensed third-party content SHALL be excluded.

### Requirement: Sample package imports deterministically
The system SHALL support deterministic import of the sample package using world packaging and media manifests.

#### Scenario: Deterministic sample import
- **Given** a valid sample package
- **When** import preview and apply run in a clean environment
- **Then** the resulting records SHALL match the expected fixture contract.

### Requirement: Sample package has explicit acceptance evidence
The implementation SHALL include sample package, fixture, rights/visibility, and leak tests.

#### Scenario: Phase acceptance
- **Given** Sample World Release Package implementation is complete
- **When** targeted tests and the full local gate run
- **Then** all checks SHALL pass before fast-forward merge.

## Non-goals

- Production seed framework.
- Unlicensed third-party content.
- Real provider calls during sample import validation.
