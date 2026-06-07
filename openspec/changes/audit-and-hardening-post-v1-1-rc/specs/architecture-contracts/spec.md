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
