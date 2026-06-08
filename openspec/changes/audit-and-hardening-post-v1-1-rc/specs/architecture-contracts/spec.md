## MODIFIED Requirements

### Requirement: Reader and member APIs hide admin evidence
The system SHALL keep prompt snapshots, raw prompts, raw outputs, resolved provider secrets, hidden/developer-only records, storage URIs, filesystem paths, bytes, base64, provider health metadata, and admin diagnostics out of reader/member API responses.

#### Scenario: Non-admin reads world content
- **GIVEN** a non-admin has access to reader or member routes
- **WHEN** they request world content
- **THEN** the response SHALL omit admin evidence and internal storage/provider details.

#### Scenario: Member reads media asset catalog
- **GIVEN** a world member can list, search, or fetch visible media assets through member media APIs
- **WHEN** a visible media asset has internal storage references such as storage_uri, preview_uri, or thumbnail_uri
- **THEN** the member response SHALL redact those internal storage references
- **AND** admin media routes MAY continue to expose them for media management.

#### Scenario: Member reads media job diagnostics
- **GIVEN** a world member can access member-scoped media routes
- **WHEN** they request media job list or detail responses
- **THEN** the response SHALL NOT expose provider configuration JSON, request JSON, result JSON, error text, actor refs, raw prompts, raw outputs, storage refs, bytes, or base64 execution evidence
- **AND** admin media management routes MAY continue to expose job internals required for operator diagnosis.


#### Scenario: Member reads media asset lineage
- **GIVEN** a world member can read visible media asset lineage
- **WHEN** lineage includes related visible media assets with internal storage references
- **THEN** every related asset in the member response SHALL redact storage_uri, preview_uri, and thumbnail_uri
- **AND** admin media routes MAY continue to expose those related asset storage references for media management.

#### Scenario: Member reads media metadata-bearing DTOs
- **GIVEN** a world member can read visible media asset, context, input, tag, collection, item, references, or lineage responses
- **WHEN** those records contain arbitrary metadata with forbidden keys or values such as storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, or base64
- **THEN** the member response SHALL omit the forbidden metadata keys and values while retaining safe metadata
- **AND** admin media routes MAY continue to expose full metadata for media management and diagnostics.


#### Scenario: Member subscribes to realtime world or conversation streams
- **GIVEN** a world member subscribes to world or conversation realtime streams
- **WHEN** agent runs, diagnostics, conversations, or narrative artifacts change
- **THEN** the member stream SHALL NOT expose raw prompts, raw outputs, provider execution diagnostics, admin-only diagnostic details, hidden or unpublished narrative artifact content, provider profile refs, storage refs, bytes, or base64 evidence
- **AND** admin realtime consumers MAY continue to receive operator diagnostics and execution details required for world management.
