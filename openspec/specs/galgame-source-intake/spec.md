# Galgame Source Intake Specification

## Purpose
This spec captures the current v0.9 galgame source intake behavior on `main`. It covers user-provided already-unpacked source directories, media/source registry storage, source traceability, restricted raw-source visibility, and the prohibition on unpacking or DRM bypass.

## Requirements
### Requirement: Intake accepts only already-unpacked user-provided sources
The system SHALL accept user-provided already-unpacked galgame asset and script directories and SHALL NOT implement cracking, unpacking, decryption, DRM bypass, scraping, or automatic acquisition.

#### Scenario: Operator imports a source directory
- **Given** an authorized operator selects a local directory containing already-unpacked sprites, backgrounds, voice audio, and scripts
- **When** the intake preview runs
- **Then** the system SHALL create a traceable inventory of source assets and fragments
- **And** it SHALL NOT mutate world canon.

### Requirement: Intake stores assets through media and authoring boundaries
The system SHALL store imported files through the media kernel and source registry while preserving source traceability.

#### Scenario: Sprite file is imported
- **Given** a sprite file is accepted by the intake preview
- **When** the operator applies the import source registration
- **Then** the file SHALL be represented by media asset/object records and source asset references
- **And** `world_events.payload` SHALL NOT contain storage URIs, filesystem paths, bytes, base64, raw prompts, or raw outputs.

### Requirement: Raw source visibility remains restricted
The system SHALL keep raw source content and original file details admin-scoped unless later explicitly published through safe reader/player DTOs.

#### Scenario: Reader requests media
- **Given** imported source media exists
- **When** a reader/player/member route returns visible content
- **Then** the response SHALL NOT expose raw source paths, hidden assets, developer-only assets, private assets, or source fragments.
