# World Packaging Specification

## Purpose

This spec captures the current v0.8 safe world packaging contract on `main`. It covers manifest-based export preview, import preview, reviewed apply, portable media references, and exclusion of secrets, storage internals, and raw prompt/provider data.

## Requirements
### Requirement: World export uses safe manifests
The system SHALL export world and media manifests that use portable references and exclude secrets, storage internals, raw prompts, and raw outputs.

#### Scenario: Export manifest generation
- **Given** an admin exports a world package
- **When** the manifest is generated
- **Then** it SHALL include portable world, worldline, media, publication, and presentation references
- **And** it SHALL NOT include `storage_uri`, filesystem paths, resolved secrets, raw prompt snapshots, or raw provider outputs.

### Requirement: World import uses preview before apply
The system SHALL validate imports in a preview step before mutating world state.

#### Scenario: Import preview detects incompatibility
- **Given** a package references an unsupported capability
- **When** import preview runs
- **Then** it SHALL report a blocker
- **And** it SHALL NOT create world, media, or provider records.

### Requirement: Media references remain portable
The system SHALL map packaged media references through the existing media kernel during import apply.

#### Scenario: Apply portable media manifest
- **Given** a package has a valid media manifest
- **When** an admin applies the import
- **Then** media records SHALL be created or linked through existing media services
- **And** no second media framework SHALL be introduced.

### Requirement: World packaging has explicit acceptance evidence
The implementation SHALL include manifest, preview/apply, compatibility, and leak tests.

#### Scenario: Phase acceptance
- **Given** World Packaging implementation is complete
- **When** targeted tests and the full local gate run
- **Then** all checks SHALL pass before fast-forward merge.

## Non-goals

- Including secrets or internal storage URIs in bundles.
- Marketplace distribution.
- Bulk historical backfill.
