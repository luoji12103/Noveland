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

#### Scenario: Member lists agent runtime runs
- **GIVEN** a world member lists agent runtime runs through member-readable routes
- **WHEN** agent run records contain prompt text, raw/model response text, provider profile refs, diagnostics, storage refs, bytes, or base64 evidence
- **THEN** the member response SHALL omit those operator-only run internals while preserving safe run status and timing fields
- **AND** admin run routes MAY continue to expose execution details required for diagnosis and world management.

#### Scenario: Member lists agents
- **GIVEN** a world member lists agents through member-readable routes
- **WHEN** agent records contain provider profile refs, execution/provider config, raw prompt/output markers, storage refs, bytes, base64, or other admin-only configuration evidence
- **THEN** the member response SHALL omit those operator-only agent internals while preserving safe public agent identity and characterization fields
- **AND** admin agent routes MAY continue to expose configuration details required for world management.

#### Scenario: Member reads world profile
- **GIVEN** a world member reads a world profile through member-readable routes
- **WHEN** the world record contains rules config, memory backend profile refs, plugin identifiers, plugin config, raw prompt/output markers, storage refs, bytes, base64, or other admin-only configuration evidence
- **THEN** the member response SHALL omit those operator-only world internals while preserving safe public world identity fields
- **AND** admin world routes MAY continue to expose configuration details required for world management.

#### Scenario: Member lists schedule rules
- **GIVEN** a world member lists schedule rules through member-readable routes
- **WHEN** schedule rules contain config with provider refs, raw prompt/output markers, storage refs, bytes, base64, or other admin-only scheduling evidence
- **THEN** the member response SHALL omit schedule rule config while preserving safe rule identity, kind, and enabled state
- **AND** admin schedule rule routes MAY continue to expose configuration details required for world management.

#### Scenario: Member reads narrative artifacts
- **GIVEN** a world member lists or fetches published narrative artifacts through member-readable routes
- **WHEN** artifact records or publication records contain source run refs, artifact metadata, continuity metadata/status, publication metadata, publication gate evidence, source draft refs, published-by user refs, raw prompt/output markers, storage refs, bytes, base64, or other admin-only evidence
- **THEN** the member response SHALL omit those operator-only narrative internals while preserving safe artifact content, title, kind, agent identity, conversation linkage, publication status, reader visibility, and publication timing
- **AND** admin narrative routes MAY continue to expose metadata and publication evidence required for world management and review.

#### Scenario: Member lists organizations
- **GIVEN** a world member lists organizations through member-readable routes
- **WHEN** organization records contain hidden summaries, metadata with raw prompt/output markers, storage refs, bytes, base64, provider refs, secret/auth refs, or other admin-only evidence
- **THEN** the member response SHALL omit hidden summaries and metadata while preserving safe public organization identity and public summary fields
- **AND** admin organization routes MAY continue to expose hidden summaries and metadata required for world management.

#### Scenario: Member lists organization memberships and faction tracks
- **GIVEN** a world member lists organization memberships or faction progress tracks through member-readable routes
- **WHEN** those records contain metadata with raw prompt/output markers, storage refs, bytes, base64, provider refs, secret/auth refs, or other admin-only evidence
- **THEN** the member response SHALL omit membership and faction-track metadata while preserving safe organization identity, agent identity, role, visibility, responsibility, progress, pressure, and summary fields
- **AND** admin organization management routes MAY continue to expose membership and faction-track metadata required for world management.

#### Scenario: Member lists worldlines
- **GIVEN** a world member lists worldlines through member-readable routes
- **WHEN** worldline records contain metadata with raw prompt/output markers, storage refs, bytes, base64, provider refs, secret/auth refs, or other admin-only evidence
- **THEN** the member response SHALL omit worldline metadata while preserving safe branch identity, parent/fork references, status, actor ref, and timing fields
- **AND** admin worldline management routes MAY continue to expose metadata required for world management.

#### Scenario: Member reads player choices
- **GIVEN** a world member creates or lists player choices through member-readable routes
- **WHEN** player choice records contain prompt text with raw prompt/output markers, storage refs, bytes, base64, provider refs, secret/auth refs, or other admin-only evidence
- **THEN** the member response SHALL omit player choice prompt text while preserving safe choice identity, selected option, context, consequence preview, applied event ref, and timing fields
- **AND** admin player-choice routes MAY continue to expose prompt text required for world management and review.

#### Scenario: Member previews player choice consequences
- **GIVEN** a world member previews player choice consequences through member-readable routes
- **WHEN** the preview contains diagnostics with raw prompt/output markers, storage refs, bytes, base64, provider refs, secret/auth refs, or other admin-only evidence
- **THEN** the member response SHALL omit diagnostics while preserving safe relationship, faction, and offscreen consequence preview fields
- **AND** admin player-choice preview routes MAY continue to expose diagnostics required for world management and review.

#### Scenario: Member reads living world dashboard
- **GIVEN** a world member reads the living world dashboard through member-readable routes
- **WHEN** the dashboard contains hidden secret counts or other hidden/admin-only state counters
- **THEN** the member response SHALL omit or zero hidden/admin-only counters while preserving safe aggregate activity counters
- **AND** admin dashboard routes MAY continue to expose hidden counters required for world management and review.

#### Scenario: Member reads journal, notification, and intervention records
- **GIVEN** a world member creates or lists player journal, notification, or intervention records through member-readable routes
- **WHEN** those records contain source event refs, source refs, prompt text, choice/event linkage, metadata with raw prompt/output markers, storage refs, bytes, base64, provider refs, secret/auth refs, or other admin-only evidence
- **THEN** the member response SHALL omit those operator-only journal, notification, and intervention internals while preserving safe user-facing titles, bodies, statuses, target identity fields, and timing fields
- **AND** admin routes MAY continue to expose source refs, prompt text, choice/event linkage, and metadata required for world management and review.

#### Scenario: Player exports privacy data
- **GIVEN** a world member requests a player privacy data export
- **WHEN** the export includes player journal, notification, or intervention records with source refs, source event refs, choice/event linkage, prompt text, metadata, storage refs, bytes, base64, provider refs, secret/auth refs, or other operator-only evidence
- **THEN** the export SHALL omit those operator-only internals while preserving safe player-owned titles, bodies, selected options, statuses, target identity fields, and timing fields
- **AND** privacy request audit records SHALL continue to contain safe summaries and actor refs only.

#### Scenario: Member reads agent relationship and calendar metadata
- **GIVEN** a world member lists agent relationships or agent calendar entries through member-readable routes
- **WHEN** those records contain metadata with raw prompt/output markers, storage refs, bytes, base64, provider refs, secret/auth refs, source evidence refs, or other admin-only scheduling/relationship evidence
- **THEN** the member response SHALL omit metadata while preserving safe relationship scores, relationship identities, calendar titles, descriptions, times, recurrence, status, and timing fields
- **AND** admin routes MAY continue to expose metadata required for world management, scheduling, and review.

#### Scenario: Member reads scene and location graph rules
- **GIVEN** a world member lists scenes or location edges through member-readable routes
- **WHEN** scene opening rules or location traversal rules contain provider refs, storage refs, raw prompt/output markers, bytes, base64, secret/auth refs, hidden route conditions, or other admin-only movement/rule evidence
- **THEN** the member response SHALL omit those rule/config internals while preserving safe scene and location graph identity, names, public descriptions, region/location tags, travel labels, active state, and timing fields
- **AND** admin routes MAY continue to expose opening and traversal rules required for world management and runtime planning.

#### Scenario: Member reads latest snapshot
- **GIVEN** a world member fetches the latest world snapshot through member-readable routes
- **WHEN** the snapshot record contains inline payload, payload_uri, payload_location, metadata, storage refs, bytes, base64, provider refs, or other replay/storage evidence
- **THEN** the member response SHALL omit payload, payload_uri, payload_location, and metadata while preserving safe snapshot identity, worldline, sequence coverage, schema version, status, source event ref, and creation time
- **AND** admin routes MAY continue to expose snapshot payload and storage evidence required for replay diagnostics and world management.


#### Scenario: Member reads release profile
- **GIVEN** a world member fetches the living-world release profile through member-readable routes
- **WHEN** the profile contains release policies, checklist evidence refs, gate decisions, metadata, storage refs, bytes, base64, provider refs, secret/auth refs, or other operator-only release evidence
- **THEN** the member response SHALL omit branch_policy, backup_policy, content_review_policy, player_permission_policy, worldline_policy, checklist, and metadata while preserving safe profile identity, status, and timing fields
- **AND** admin routes MAY continue to expose release policies, checklist evidence, and metadata required for release management and review.

#### Scenario: Member reads world bible
- **GIVEN** a world member fetches the world bible through member-readable routes
- **WHEN** the bible contains raw source material/import notes, continuity config, metadata, storage refs, bytes, base64, provider refs, secret/auth refs, or other operator-only canon-management evidence
- **THEN** the member response SHALL omit source_material, continuity_config, and metadata while preserving safe canon timeline, setting rules, forbidden changes, sequel boundaries, continuity status, identity, and timing fields
- **AND** admin routes MAY continue to expose source material, continuity configuration, and metadata required for canon management and review.

#### Scenario: Member reads agent presence
- **GIVEN** a world member fetches agent presence through member-readable routes
- **WHEN** the presence record contains scheduled movement plans, last event linkage, storage refs, provider refs, raw prompt/output markers, bytes, base64, secret/auth refs, or other operator-only scheduling evidence
- **THEN** the member response SHALL omit scheduled_movement and last_event_id while preserving safe current scene, visibility, encounter eligibility, identity, worldline, and timing fields
- **AND** admin routes MAY continue to expose scheduled movement and last event linkage required for world management and runtime diagnostics.

#### Scenario: Member reads conversation session metadata
- **GIVEN** a world member lists or fetches conversation sessions through member-readable routes
- **WHEN** the session contains objective text, opening prompts, policy settings, writer/provider/plugin configuration, memory configuration, group context, storage refs, provider refs, raw prompt/output markers, bytes, base64, secret/auth refs, or other operator-only conversation orchestration evidence
- **THEN** the member response SHALL omit those session internals while preserving safe session identity, worldline, scene, title, scope, mode, status, turn counters, terminal state, and timing fields
- **AND** admin routes MAY continue to expose session orchestration internals required for conversation management and runtime diagnostics.

#### Scenario: Member lists conversation narrative artifacts
- **GIVEN** a world member lists narrative artifacts through a conversation-scoped member-readable route
- **WHEN** the conversation has draft, unpublished, non-reader-visible, or published artifacts containing source run refs, artifact metadata, raw prompt/output markers, storage refs, bytes, base64, provider refs, secret/auth refs, or other operator-only narrative evidence
- **THEN** the member response SHALL include only published reader-visible artifacts for that conversation
- **AND** the member response SHALL omit source run refs and artifact metadata while preserving safe artifact identity, title, content, kind, conversation linkage, and creation time
- **AND** admin routes MAY continue to list draft artifacts and expose source refs and metadata required for conversation narrative management.

#### Scenario: Member lists conversation turns
- **GIVEN** a world member lists conversation turns through member-readable routes
- **WHEN** turn records contain runtime run IDs, provider/plugin error text, raw prompt/output markers, storage refs, bytes, base64, provider refs, secret/auth refs, or other operator-only execution evidence
- **THEN** the member response SHALL omit run IDs and error text while preserving safe turn identity, speaker, transcript text, status, and timing fields
- **AND** admin routes MAY continue to expose run IDs and error text required for conversation management and runtime diagnostics.

## ADDED Requirements

### Requirement: Web API proxies preserve backend route boundaries
The system SHALL build same-origin Web proxy backend URLs from fixed backend route templates and encoded dynamic path segments so decoded route parameters cannot broaden backend route scope.

#### Scenario: Web proxies realtime stream paths
- **GIVEN** a Web API route proxies a world or conversation realtime stream
- **AND** the requested world or conversation identifier contains encoded path separators or other reserved path characters
- **WHEN** the route constructs the backend stream URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the backend path
- **AND** the original query string SHALL be preserved only as a query string, not as part of any path segment.

#### Scenario: Web proxies runtime query parameters
- **GIVEN** a Web API route proxies a runtime backend route with query parameters
- **WHEN** the shared runtime proxy helper appends the original request query string
- **THEN** route handlers SHALL pass only the fixed backend path and encoded dynamic path segments to the helper
- **AND** query parameters SHALL be appended exactly once
- **AND** query parameters SHALL NOT be embedded into the backend path argument before proxying.

### Requirement: Web realtime clients preserve backend route boundaries
The system SHALL build browser-initiated realtime backend URLs from fixed backend route templates and encoded dynamic path segments so decoded identifiers cannot broaden backend route scope.

#### Scenario: Web client opens conversation live sockets
- **GIVEN** browser-side Web realtime code opens a conversation live WebSocket
- **AND** the world or conversation identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the backend WebSocket URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the backend path
- **AND** the configured WebSocket base URL SHALL remain separate from dynamic path segments.

### Requirement: Web API clients preserve same-origin route boundaries
The system SHALL build browser-side same-origin API request URLs from fixed frontend route templates and encoded dynamic path segments so decoded identifiers cannot broaden frontend or backend route scope.

#### Scenario: Web client controls conversation sessions
- **GIVEN** browser-side Web client code issues conversation session read or control requests through same-origin API routes
- **AND** the world or conversation identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.

#### Scenario: Web client manages provider integrations
- **GIVEN** browser-side Web client code issues provider integration read, configuration, health-check, model-discovery, or smoke-test requests through same-origin API routes
- **AND** the world or provider identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.
