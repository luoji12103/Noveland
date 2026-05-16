# Import / Export Stability

## ADDED Requirements

### Requirement: World package roundtrip is stable
The system SHALL support repeatable export/import roundtrips for world packages, media manifests, persona/memory manifests, and provider config metadata without secrets.

#### Scenario: Package roundtrip
- **Given** a valid world package is exported
- **When** it is imported through preview and reviewed apply
- **Then** world, worldline, media, persona, memory, and provider config references SHALL validate
- **And** the import SHALL NOT bypass preview/apply.

### Requirement: Export excludes unsafe data
The system SHALL exclude resolved secrets, storage paths, raw prompt snapshots by default, bytes, base64, and raw provider outputs from exported packages.

#### Scenario: Export manifest generated
- **Given** a world contains provider integrations and media assets
- **When** export preview runs
- **Then** the manifest SHALL include safe metadata and portable references only.

### Requirement: Sample package imports repeatedly
The system SHALL keep the sample world package repeatably importable for regression.

#### Scenario: Sample package repeat import
- **Given** the sample package has been imported once
- **When** it is imported again into an allowed target
- **Then** preview SHALL identify duplicates or compatibility actions safely
- **And** apply SHALL remain explicit.

## Non-goals

- Marketplace distribution.
- Exporting resolved secrets.
- Raw prompt snapshot export by default.
