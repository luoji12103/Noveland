# Media Asset Admin Console Specification

## Purpose

This spec captures the current v0.4 world-scoped media asset admin console on `main`. The console lets authorized admins inspect assets, objects, jobs, references, filters, and upload/download flows through existing media APIs without adding public delivery or storage backend behavior.

## Requirements

### Requirement: Media admin page lists and filters assets
The system SHALL provide a world-scoped Web admin page for media assets using existing media catalog APIs and safe Web client helpers.

#### Scenario: Admin filters media assets
- **GIVEN** an authorized world admin opens `/worlds/{worldId}/media`
- **WHEN** they filter by asset status, kind, visibility, tags, or search inputs
- **THEN** the page SHALL display matching media asset summaries
- **AND** it SHALL not expose raw storage paths, bytes, base64 payloads, or filesystem locations.

### Requirement: Media detail shows objects, jobs, and references
The system SHALL allow admins to inspect selected media asset details, media objects, job status, references, lineage, and verification state.

#### Scenario: Admin inspects a media asset
- **GIVEN** a selected media asset has objects, jobs, and references
- **WHEN** the detail panel renders
- **THEN** the panel SHALL show safe object metadata, job status, reference targets, and lineage
- **AND** it SHALL keep opaque storage details behind existing backend APIs.

### Requirement: Upload and download use existing media routes
The system SHALL support admin upload and safe object download actions through existing media API routes.

#### Scenario: Admin uploads an asset
- **GIVEN** an authorized admin chooses a file for upload
- **WHEN** the upload action runs
- **THEN** the Web client SHALL call the existing media upload route
- **AND** created records SHALL remain owned by the backend media kernel.

### Requirement: Media admin preserves media framework ownership
The system SHALL reuse media assets, objects, jobs, references, tags, collections, and lineage services instead of creating a second media framework.

#### Scenario: Admin views visual or speech media
- **GIVEN** an image, sprite, background, audio, or transcript-linked asset exists
- **WHEN** it appears in the media admin console
- **THEN** it SHALL be represented by existing media records
- **AND** narrative artifacts SHALL NOT be used as media storage.

## Non-goals

- This spec does not define public reader media delivery.
- This spec does not define new storage backends.
- This spec does not define automatic asset generation or provider execution.
- This spec does not expose raw storage URIs or media bytes in Web JSON.
