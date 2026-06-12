## MODIFIED Requirements

### Requirement: Worldline-scoped state validates world and worldline identity
The system SHALL treat `world_id` and `worldline_id` as first-class identifiers for worldline-scoped records and SHALL reject links that cross worlds or worldlines.

#### Scenario: Reader media object delivery requires scoped worldline identity
- **GIVEN** a reader-visible media object belongs to a worldline-scoped media asset
- **WHEN** a reader/member/player/admin downloads the media object through reader media delivery
- **THEN** the delivery route SHALL require a worldline identifier in the route path or explicit request scope
- **AND** the service SHALL reject missing or mismatched worldline scope before reading storage bytes.

#### Scenario: World-level voice profiles do not reference fork media assets
- **GIVEN** a voice profile omits `worldline_id` so it can act as a world-level default
- **WHEN** the profile includes a media reference asset
- **THEN** the speech service SHALL reject worldline-scoped media assets rather than allowing fork-specific audio to become a world-level voice reference
- **AND** worldline-scoped voice profiles SHALL continue to require reference assets from the same worldline.

#### Scenario: Offscreen resolution writes safe world event payloads
- **GIVEN** an offscreen event queue item contains payload JSON copied from admin input, GM macro planning, player choice effects, or forked queue state
- **WHEN** the autonomy service resolves the queue item into `world_events.payload`
- **THEN** the persisted world event payload SHALL omit storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, and base64-like values while preserving safe event context fields.

#### Scenario: GM proposal resolution writes safe world event payloads
- **GIVEN** a GM event proposal contains proposed payload JSON copied from admin input, macro planning, or provider-backed planning evidence
- **WHEN** the GM service resolves the proposal into `world_events.payload`
- **THEN** the persisted world event payload SHALL omit storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, and base64-like values while preserving safe proposal identity and event context fields.

#### Scenario: Event store enforces safe world event payloads
- **GIVEN** any service appends a world event payload containing storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, or base64-like values
- **WHEN** `WorldEventStore.append_event()` persists the event
- **THEN** the stored `world_events.payload` SHALL omit forbidden keys and values while preserving safe event context fields, regardless of the producer.

#### Scenario: Event store normalizes forbidden world event payload key variants
- **GIVEN** any service appends a world event payload containing forbidden keys written in snake_case, camelCase, compact, or mixed punctuation forms such as raw_prompt, rawPrompt, rawprompt, storage_uri, storageUri, prompt_snapshot, or promptSnapshotId
- **WHEN** `WorldEventStore.append_event()` persists the event
- **THEN** the stored `world_events.payload` SHALL omit those forbidden keys and values while preserving safe event context fields, regardless of the producer.

#### Scenario: Agent memory backend calls require validated worldline scope
- **GIVEN** an agent memory search or deletion request includes an explicit `worldline_id`
- **WHEN** the API prepares to call a memory backend, external memory provider, or local vector store for that request
- **THEN** the service SHALL first verify that the `worldline_id` exists in the requested `world_id`
- **AND** invalid or cross-world worldline identifiers SHALL be rejected before any backend search or delete call is made
- **AND** valid worldline-scoped memory operations SHALL continue to use the resolved worldline identifier.

#### Scenario: Agent memory read routes reject invalid worldline scope consistently
- **GIVEN** an agent memory list, profile snapshot read, or profile snapshot refresh request includes an explicit `worldline_id`
- **WHEN** the `worldline_id` is missing from the requested `world_id` or belongs to another world
- **THEN** the API SHALL reject the request with a validation response instead of returning an empty successful response or raising an unhandled server error
- **AND** the service SHALL validate the worldline before backend list calls or profile snapshot reads/writes
- **AND** valid worldline-scoped list and profile snapshot operations SHALL continue to return records for the resolved worldline.

#### Scenario: Player privacy request lists reject invalid worldline scope
- **GIVEN** a player privacy request list query includes an explicit `worldline_id`
- **WHEN** the `worldline_id` is missing from the requested `world_id` or belongs to another world
- **THEN** the API SHALL reject the request instead of returning an empty successful response
- **AND** valid worldline-scoped privacy request list queries SHALL continue to return only privacy request records from the resolved worldline.

#### Scenario: Reader media routes reject invalid worldline scope
- **GIVEN** a reader media list, detail, or object download request includes an explicit `worldline_id`
- **WHEN** the `worldline_id` is missing from the requested `world_id` or belongs to another world
- **THEN** the API SHALL reject the request instead of returning an empty successful list or treating the cross-world identifier as a valid filter
- **AND** valid worldline-scoped reader media list, detail, and download operations SHALL continue to return only reader-deliverable media from the resolved worldline.

### Requirement: Reader and member APIs hide admin evidence
The system SHALL keep prompt snapshots, raw prompts, raw outputs, resolved provider secrets, hidden/developer-only records, storage URIs, filesystem paths, bytes, base64, provider health metadata, and admin diagnostics out of reader/member API responses.

#### Scenario: Non-admin reads world content
- **GIVEN** a non-admin has access to reader or member routes
- **WHEN** they request world content
- **THEN** the response SHALL omit admin evidence and internal storage/provider details.

#### Scenario: Member playback fetches safe turn presentation records
- **GIVEN** a conversation turn has canonical presentation state for reader playback
- **WHEN** an ordinary world member fetches the turn presentation through the conversation presentation GET route
- **THEN** the backend SHALL return a member-readable presentation DTO instead of requiring world-admin access
- **AND** the response SHALL preserve only safe playback fields such as speaker, emotion, render state, visible media asset identifiers, record identifiers, and timestamps
- **AND** the response SHALL NOT expose internal sprite-set, sprite-variant, voice-profile, transcript, provider, prompt snapshot, model invocation, media job, storage URI/path, bytes, or base64 evidence.
- **AND** presentation mutation, visual rendering, speech rendering, and audio transcription routes SHALL remain world-admin-only.
- **AND** media asset identifiers in the member response SHALL be present only when the same asset is reader-deliverable for that worldline.

#### Scenario: Beta feedback reporters do not receive admin triage evidence
- **GIVEN** a beta feedback reporter can list or fetch their own report through member-readable routes
- **WHEN** an admin has triaged the report with admin evidence refs, repair proposal refs, moderation refs, actor refs, or metadata
- **THEN** the reporter response SHALL hide those admin-only triage fields while preserving safe report status and severity
- **AND** admin beta feedback routes MAY continue to expose triage evidence required for repair and moderation workflows.

#### Scenario: Member-owned state JSON uses normalized sensitive-key filtering
- **GIVEN** a world member creates or reads player resume state or beta feedback metadata through member-readable routes
- **WHEN** route state, resume state, report metadata, evidence metadata, or repair metadata contains sensitive keys written in snake_case, camelCase, compact, or mixed punctuation forms such as raw_prompt, rawPrompt, rawprompt, storage_uri, storageUri, prompt_snapshot, or promptSnapshotId
- **THEN** the persisted and returned member-owned JSON SHALL omit those forbidden keys and values while preserving safe state and feedback metadata
- **AND** admin routes MAY continue to expose only the already-sanitized stored metadata, never raw prompt/output, storage, secret, bytes, or base64 evidence.

#### Scenario: Review and onboarding metadata uses normalized sensitive-key filtering
- **GIVEN** private beta invite metadata, player privacy export/request JSON, or moderation report/review metadata is created, persisted, or read through member/admin routes
- **WHEN** the JSON contains sensitive keys written in snake_case, camelCase, compact, or mixed punctuation forms such as raw_prompt, rawPrompt, rawprompt, storage_uri, storageUri, prompt_snapshot, or promptSnapshotId
- **THEN** the service SHALL omit or redact those forbidden keys and values before persistence/readback while preserving safe metadata fields
- **AND** admin routes MAY continue to expose only the already-sanitized stored metadata, never raw prompt/output, storage, secret, token, bytes, or base64 evidence.


#### Scenario: Member reads agent character profiles
- **GIVEN** a world member lists agents through the member-readable agent catalog
- **WHEN** an agent character profile contains arbitrary profile JSON with storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, or base64
- **THEN** the member response SHALL omit the forbidden character profile keys and values while retaining safe public characterization fields
- **AND** admin agent reads MAY continue to expose the full character profile for authoring and repair workflows.

#### Scenario: Member reads player choice metadata
- **GIVEN** a world member records or lists player choices through member-readable routes
- **WHEN** the choice context or consequence preview contains arbitrary JSON with storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, or base64
- **THEN** the member response SHALL omit the forbidden keys and values while retaining safe choice metadata and diagnostics
- **AND** admin player choice reads MAY continue to expose full review metadata required for authoring and repair workflows.

#### Scenario: Member previews player choice effect metadata
- **GIVEN** a world member previews player choice consequences through member-readable routes
- **WHEN** the preview relationship updates, faction updates, or offscreen event metadata contain arbitrary JSON with storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, or base64
- **THEN** the member preview response SHALL omit the forbidden keys and values while retaining safe public consequence preview fields
- **AND** admin player choice preview routes MAY continue to expose full effect metadata required for world management and review.

#### Scenario: Member reads journal and notification text
- **GIVEN** a world member lists player journal entries or in-world notifications
- **WHEN** the title or body text contains storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, or base64
- **THEN** the member response SHALL blank the sensitive-looking text while preserving safe text and non-sensitive status fields
- **AND** admin journal and notification reads MAY continue to expose full review text and metadata required for authoring and repair workflows.


#### Scenario: Member reads player actor profiles
- **GIVEN** a world member lists or binds player actor profiles through member-readable routes
- **WHEN** the player actor profile contains arbitrary profile JSON with storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, or base64
- **THEN** the member response SHALL omit the forbidden profile keys and values while retaining safe profile fields
- **AND** writes through the player actor binding route SHALL sanitize profile JSON before persistence.

#### Scenario: Member reads media asset catalog
- **GIVEN** a world member can list, search, or fetch visible media assets through member media APIs
- **WHEN** a visible media asset has internal storage references such as storage_uri, preview_uri, or thumbnail_uri, internal provider/source IDs, provider kinds, or actor refs
- **THEN** the member response SHALL redact internal storage references and SHALL blank internal provider/source IDs, provider kinds, and actor refs
- **AND** member catalog/search filters SHALL reject provider/source filter parameters that target internal source event IDs, source invocation IDs, or provider kinds
- **AND** admin media routes MAY continue to expose those fields and filters for media management.

#### Scenario: Member reads media job diagnostics
- **GIVEN** a world member can access member-scoped media routes
- **WHEN** they request media job list or detail responses
- **THEN** the response SHALL NOT expose provider configuration JSON, request JSON, result JSON, error text, actor refs, raw prompts, raw outputs, storage refs, bytes, or base64 execution evidence
- **AND** admin media management routes MAY continue to expose job internals required for operator diagnosis.


#### Scenario: Member reads media asset lineage
- **GIVEN** a world member can read visible media asset lineage
- **WHEN** lineage includes input/output source job IDs or related visible media assets with internal storage references, provider/source IDs, provider kinds, or actor refs
- **THEN** every member lineage response SHALL blank input/output source job IDs and SHALL redact related asset storage, provider/source, provider kind, and actor ref fields
- **AND** admin media routes MAY continue to expose those lineage internals for media management.

#### Scenario: Member reads media metadata-bearing DTOs
- **GIVEN** a world member can read visible media asset, context, input, tag, collection, item, references, or lineage responses
- **WHEN** those records contain arbitrary metadata with forbidden keys or values such as storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, or base64, or member-visible catalog wrappers carry internal actor refs
- **THEN** the member response SHALL omit the forbidden metadata keys and values while retaining safe metadata and SHALL blank internal actor refs
- **AND** admin media routes MAY continue to expose full metadata and actor refs for media management and diagnostics.

#### Scenario: Member media and presentation JSON normalize sensitive key variants
- **GIVEN** a world member reads media metadata-bearing DTOs or conversation turn presentation JSON through member-readable routes
- **WHEN** metadata or presentation JSON contains sensitive keys written in snake_case, camelCase, compact, or mixed punctuation forms such as raw_prompt, rawPrompt, rawprompt, storage_uri, storageUri, prompt_snapshot, or promptSnapshotId
- **THEN** the member response SHALL omit those forbidden keys and values while retaining safe metadata and presentation fields
- **AND** admin media and presentation routes MAY continue to expose unsanitized authoring/operator JSON required for diagnostics and management.


#### Scenario: Member subscribes to realtime world or conversation streams
- **GIVEN** a world member subscribes to world or conversation realtime streams
- **WHEN** agent runs, diagnostics, conversations, or narrative artifacts change
- **THEN** the member stream SHALL NOT expose raw prompts, raw outputs, provider execution diagnostics, admin-only diagnostic details, hidden or unpublished narrative artifact content, provider profile refs, storage refs, bytes, or base64 evidence
- **AND** admin realtime consumers MAY continue to receive operator diagnostics and execution details required for world management.

#### Scenario: Member lists agent runtime runs
- **GIVEN** a world member lists agent runtime runs through member-readable routes
- **WHEN** agent run records contain prompt text, raw/model response text, provider profile refs, diagnostics, source calendar/schedule/event refs, storage refs, bytes, or base64 evidence
- **THEN** the member response SHALL omit those operator-only run internals while preserving safe run status and timing fields
- **AND** admin run routes MAY continue to expose execution details required for diagnosis and world management.

#### Scenario: Member lists agents
- **GIVEN** a world member lists agents through member-readable routes
- **WHEN** agent records contain provider profile refs, source preset refs/versions, execution/provider config, raw prompt/output markers, storage refs, bytes, base64, or other admin-only configuration evidence
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
- **WHEN** player choice records contain prompt text, applied event refs, raw prompt/output markers, storage refs, bytes, base64, provider refs, secret/auth refs, or other admin-only evidence
- **THEN** the member response SHALL omit player choice prompt text and applied event refs while preserving safe choice identity, selected option, context, consequence preview, and timing fields
- **AND** admin player-choice routes MAY continue to expose prompt text and applied event refs required for world management and review.

#### Scenario: Member previews player choice consequences
- **GIVEN** a world member previews player choice consequences through member-readable routes
- **WHEN** the preview contains diagnostics or effect metadata with raw prompt/output markers, storage refs, bytes, base64, provider refs, secret/auth refs, or other admin-only evidence
- **THEN** the member response SHALL omit diagnostics and forbidden effect metadata while preserving safe relationship, faction, and offscreen consequence preview fields
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

#### Scenario: Platform admins manage player journal, notification, and intervention records
- **GIVEN** a platform admin accesses a world without a direct world membership
- **WHEN** they list player journal, notification, or intervention records, request another user's player records, or create an intervention for a world member
- **THEN** the response SHALL use the same management visibility and cross-user access semantics as world admins
- **AND** ordinary world members SHALL remain limited to their own player records and member-safe response fields.

#### Scenario: Player exports privacy data
- **GIVEN** a world member requests a player privacy data export
- **WHEN** the export includes player choices, journal, notification, or intervention records with applied event refs, source refs, source event refs, choice/event linkage, prompt text, metadata, storage refs, bytes, base64, provider refs, secret/auth refs, or other operator-only evidence
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
- **WHEN** the snapshot record contains inline payload, payload_uri, payload_location, metadata, created-by event refs, storage refs, bytes, base64, provider refs, or other replay/storage evidence
- **THEN** the member response SHALL omit payload, payload_uri, payload_location, metadata, and created-by event refs while preserving safe snapshot identity, worldline, sequence coverage, schema version, status, and creation time
- **AND** admin routes MAY continue to expose snapshot payload, storage evidence, and created-by event refs required for replay diagnostics and world management.

#### Scenario: Member reads replay state
- **GIVEN** a world member reads replay state through member-readable routes
- **WHEN** replay clock state contains source event identifiers or event sequence evidence
- **THEN** the member response SHALL omit those operator-only replay source refs while preserving safe reconstructed clock state, source sequence, worldline, and aggregate event counts
- **AND** admin replay routes MAY continue to expose source event refs needed for replay and snapshot diagnosis.


#### Scenario: Member reads release profile
- **GIVEN** a world member fetches the living-world release profile through member-readable routes
- **WHEN** the profile contains release policies, checklist evidence refs, gate decisions, metadata, storage refs, bytes, base64, provider refs, secret/auth refs, or other operator-only release evidence
- **THEN** the member response SHALL omit branch_policy, backup_policy, content_review_policy, player_permission_policy, worldline_policy, checklist, and metadata while preserving safe profile identity, status, and timing fields
- **AND** admin routes MAY continue to expose release policies, checklist evidence, and metadata required for release management and review.

#### Scenario: Member reads world bible
- **GIVEN** a world member fetches the world bible through member-readable routes
- **WHEN** the bible contains raw source material/import notes, continuity config, metadata, or public canon timeline, setting rule, forbidden change, and sequel boundary JSON values containing storage refs, bytes, base64, provider refs, secret/auth refs, raw prompt/output markers, or other operator-only canon-management evidence
- **THEN** the member response SHALL omit source_material, continuity_config, and metadata and SHALL sanitize canon_timeline, setting_rules, forbidden_changes, and sequel_boundaries by removing forbidden keys/values while preserving safe canon timeline, setting rule, forbidden change, sequel boundary, continuity status, identity, and timing fields
- **AND** admin routes MAY continue to expose source material, continuity configuration, metadata, and unsanitized canon-management JSON required for canon management and review.

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
- **WHEN** turn records contain runtime run IDs, provider/plugin error text, transcript text with raw prompt/output markers, storage refs, bytes, base64, provider refs, secret/auth refs, or other operator-only execution evidence
- **THEN** the member response SHALL omit run IDs and error text and SHALL blank sensitive-looking transcript text while preserving safe turn identity, speaker, safe transcript text, status, and timing fields
- **AND** admin routes MAY continue to expose run IDs, error text, and unsanitized transcript text required for conversation management and runtime diagnostics.

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

#### Scenario: Web non-auth proxies do not relay backend cookie mutation headers
- **GIVEN** a Web API route proxies a non-auth backend route for worlds, runtime, plugins, private beta, presets, or world composition helpers
- **WHEN** the backend response contains one or more `Set-Cookie` headers
- **THEN** the Web proxy response SHALL omit those `Set-Cookie` headers
- **AND** authenticated auth routes MAY continue to relay backend cookie mutation headers required for login, logout, and CSRF flows.

#### Scenario: Web proxies preserve media response safety headers
- **GIVEN** a Web API route proxies a backend media object download or other byte response
- **WHEN** the backend response contains safe response metadata such as content type, content disposition, content length, or `X-Content-Type-Options`
- **THEN** the Web proxy response SHALL preserve the safe response metadata needed for browser download/rendering safety
- **AND** it SHALL continue to omit backend cookie mutation headers unless an auth route explicitly opts in.

#### Scenario: Web proxies preserve request body bytes
- **GIVEN** a Web API route proxies a non-GET backend request such as media upload, world import, auth, runtime, or private-beta mutation
- **WHEN** the frontend request body contains JSON, multipart form-data, or arbitrary bytes
- **THEN** the Web proxy SHALL forward the original request body bytes without text decoding or re-encoding
- **AND** empty request bodies SHALL remain absent when forwarded to the backend.

#### Scenario: Login requires double-submit CSRF before session cookie creation
- **GIVEN** a browser client submits credentials to the login route
- **WHEN** the login request would create a new authenticated session cookie
- **THEN** the backend SHALL require a matching CSRF cookie and `X-CSRF-Token` header before creating the session
- **AND** the Web auth client SHALL obtain and forward that CSRF token with the login request.

#### Scenario: Memory backend profile configuration preserves secret-reference boundaries
- **GIVEN** a platform admin creates or updates a memory backend profile
- **WHEN** the profile includes vector store, LLM, embedder, reranker, or secret reference configuration
- **THEN** the backend SHALL reject persisted config keys or values that contain raw secret material
- **AND** memory backend `secret_refs` SHALL store only safe reference names used to resolve secrets from runtime configuration.

#### Scenario: Web memory admin JSON panels normalize sensitive memory evidence
- **GIVEN** an authorized platform admin views memory backend profile config, secret refs, health details, or write/retrieval log summaries in the Web memory backend admin console
- **WHEN** memory JSON contains resolved secret, token, authorization, raw prompt/output, prompt snapshot, storage URI, file/object path, bytes, or base64 keys written in snake_case, camelCase, compact, or mixed punctuation forms such as client_secret, clientSecret, bearerToken, rawPrompt, storageUri, filePath, or promptSnapshotId
- **THEN** the Web UI SHALL redact or omit those sensitive keys and values before rendering editable JSON panels or diagnostic summaries
- **AND** safe memory configuration fields and safe `secret_refs` reference values such as `env:MEMORY_OPENAI_API_KEY` SHALL remain visible.

#### Scenario: Provider secret-bearing JSON normalizes sensitive key variants
- **GIVEN** provider integration config, provider execution request JSON, provider budget metadata, package provider templates, or multimodal diagnostic inputs contain arbitrary JSON
- **WHEN** secret-bearing keys are written in snake_case, camelCase, compact, or mixed punctuation forms such as client_secret, clientSecret, clientsecret, bearer_token, bearerToken, private_key, privateKey, secret_key, or secretKey
- **THEN** backend validators SHALL reject raw persisted or executable provider JSON containing those keys
- **AND** package exports, persisted safe DTOs, and diagnostic leak checks SHALL omit, redact, or flag those keys using the same normalized sensitive-key semantics.

#### Scenario: Budget and diagnostics JSON normalize storage and prompt key variants
- **GIVEN** provider budget policy JSON, multimodal prompt-snapshot diagnostics, or narrative quality dashboard evidence contains arbitrary JSON
- **WHEN** storage, path, bytes, base64, raw prompt/output, or prompt snapshot keys are written in snake_case, camelCase, compact, or mixed punctuation forms such as storage_uri, storageUri, storageuri, raw_prompt, rawPrompt, rawprompt, prompt_snapshot, promptSnapshotId, file_path, or filePath
- **THEN** provider budget validators SHALL reject persisted policy JSON containing those keys
- **AND** diagnostics and dashboard responses SHALL flag and sanitize those keys using the same normalized leaky-key semantics while preserving safe operational metadata.

#### Scenario: Package and authoring validators normalize storage and prompt key variants
- **GIVEN** world package manifests, authoring source metadata, or asset generation policy/proposal JSON contain arbitrary JSON
- **WHEN** storage, path, bytes, base64, raw prompt/output, or prompt snapshot keys are written in snake_case, camelCase, compact, or mixed punctuation forms such as storage_uri, storageUri, raw_prompt, rawPrompt, prompt_snapshot, promptSnapshotId, filesystem_path, or filesystemPath
- **THEN** contract validators SHALL reject those keys before accepting imports, authoring records, or asset generation configuration
- **AND** safe non-operational metadata SHALL remain accepted.

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

#### Scenario: Web provider admin JSON panels normalize sensitive provider evidence
- **GIVEN** an authorized admin views provider integration config, provider profile plugin config, default params, capability JSON, or health metadata in the Web provider admin console
- **WHEN** provider JSON contains resolved secret, token, authorization, raw prompt/output, prompt snapshot, storage URI, file/object path, local model path, bytes, or base64 keys written in snake_case, camelCase, compact, or mixed punctuation forms such as client_secret, clientSecret, bearerToken, rawPrompt, storageUri, filePath, localModelPath, or promptSnapshotId
- **THEN** the Web UI SHALL redact or omit those sensitive keys and values before rendering editable JSON panels, schema-derived plugin config inputs, submitting provider profile JSON payloads, or rendering metadata summaries
- **AND** safe provider configuration keys such as model_discovery_path, chat_completions_path, endpoint, timeout_seconds, temperature, dry_run, max_tokens, and json_mode SHALL remain visible.

#### Scenario: Web client manages speech admin records
- **GIVEN** browser-side Web client code issues speech voice profile, agent voice binding, style mapping, transcript, TTS, or STT requests through same-origin API routes
- **AND** the world, agent, voice profile, binding, or style mapping identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.

#### Scenario: Web client manages visual admin records
- **GIVEN** browser-side Web client code issues visual sprite set, sprite variant, scene background, resolver, or compose-scene requests through same-origin API routes
- **AND** the world, sprite set, sprite variant, or background identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters
- **AND** visual admin POST, PATCH, PUT, or DELETE requests, including resolver preview requests, SHALL include the same double-submit CSRF header used by other Web admin mutations.

#### Scenario: Web client manages media admin records
- **GIVEN** browser-side Web client code issues media asset, object, reference, job, upload, or download requests through same-origin API routes
- **AND** the world, media asset, media job, or media object identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.

#### Scenario: Web client manages invocation ledger records
- **GIVEN** browser-side Web client code issues model invocation list, detail, prompt snapshot, tag, or redaction requests through same-origin API routes
- **AND** the world, invocation, or tag identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.

#### Scenario: Web invocation ledger evidence normalizes sensitive key variants
- **GIVEN** an authorized admin views invocation or prompt snapshot evidence in the Web invocation ledger
- **WHEN** evidence JSON contains storage, path, bytes, base64, raw prompt/output, prompt snapshot, secret, token, or auth keys written in snake_case, camelCase, compact, or mixed punctuation forms such as storage_uri, storageUri, raw_prompt, rawPrompt, prompt_snapshot, promptSnapshotId, clientSecret, or bearerToken
- **THEN** the Web UI SHALL redact those evidence keys and values before rendering the evidence block
- **AND** safe non-sensitive evidence fields SHALL remain visible.

#### Scenario: Web runtime admin diagnostics normalize sensitive text
- **GIVEN** an authorized admin views runtime health, external tool policy, scale readiness, or runtime diagnostic entries in the Web runtime admin console
- **WHEN** those text fields contain resolved secrets, tokens, authorization headers, raw prompt/output markers, prompt snapshot identifiers, storage URIs, file/object paths, bytes, base64, or local model paths from dirty legacy API or SSE data
- **THEN** the Web UI SHALL redact those sensitive-looking text values before rendering runtime notices, compact lists, readiness summaries, or diagnostic rows
- **AND** safe operational strings such as policy modes, audit field names, iteration status, readiness areas, and recommendations SHALL remain visible.

#### Scenario: Web dashboard management JSON panels normalize sensitive config evidence
- **GIVEN** an authorized world or platform admin views agent config, schedule rule config, provider profile capabilities, persona behavior policy, observation metadata, or narrative artifact metadata in the Web dashboard
- **WHEN** dashboard JSON contains resolved secrets, tokens, authorization headers, raw prompt/output markers, prompt snapshot identifiers, storage URIs, file/object paths, bytes, base64, or local model paths written in snake_case, camelCase, compact, or mixed punctuation forms
- **THEN** the Web UI SHALL redact or omit those sensitive keys and values before rendering editable JSON panels or submitting dashboard JSON payloads
- **AND** safe dashboard configuration fields such as behavior tone, schedule hours, provider capability flags, and non-sensitive metadata SHALL remain visible.

#### Scenario: Web agent detail panels normalize sensitive agent evidence
- **GIVEN** an authorized world admin views or updates agent detail records in the Web agent builder
- **WHEN** agent character profile, agent config, relationship metadata, persona behavior policy, persona plugin config, observation metadata, run summary text, or run diagnostics contain resolved secrets, tokens, authorization headers, raw prompt/output markers, prompt snapshot identifiers, storage URIs, file/object paths, bytes, base64, or local model paths written in common key or value variants
- **THEN** the Web UI SHALL redact or omit those sensitive keys and values before rendering editable JSON panels, read-only JSON summaries, run text, or submitting agent-builder JSON payloads
- **AND** safe characterization, relationship, persona, and operational metadata SHALL remain visible.

#### Scenario: Web preset admin panels normalize sensitive preset evidence
- **GIVEN** an authorized platform admin views, creates, or updates platform-managed agent presets in the Web preset admin console
- **WHEN** preset behavior policy, calendar blueprint entries or metadata, or advanced config contain resolved secrets, tokens, authorization headers, raw prompt/output markers, prompt snapshot identifiers, storage URIs, file/object paths, bytes, base64, or local model paths written in common key or value variants
- **THEN** the Web UI SHALL redact or omit those sensitive keys and values before rendering editable preset JSON panels or submitting preset JSON payloads
- **AND** safe preset behavior, calendar schedule, metadata, and operational config fields SHALL remain visible.

#### Scenario: Web world overview panels normalize sensitive world evidence
- **GIVEN** an authorized world admin or platform admin views, filters, imports, validates, or updates world overview records in the Web world overview console
- **WHEN** world memory/rules plugin config, world bible JSON, release profile policies/checklists/metadata, world composition rules config, or event payload JSON contain resolved secrets, tokens, authorization headers, raw prompt/output markers, prompt snapshot identifiers, storage URIs, file/object paths, bytes, base64, or local model paths written in common key or value variants
- **THEN** the Web UI SHALL redact or omit those sensitive keys and values before rendering editable JSON panels, compact event payload summaries, or submitting world-overview JSON payloads
- **AND** safe world configuration, continuity, release policy, composition validation, and event audit fields SHALL remain visible.

#### Scenario: Web narrative surfaces normalize sensitive writer and artifact evidence
- **GIVEN** an authorized world admin updates conversation narrative writer configuration or a reader views a published narrative artifact detail page
- **WHEN** writer plugin config or artifact metadata contain resolved secrets, tokens, authorization headers, raw prompt/output markers, prompt snapshot identifiers, storage URIs, file/object paths, bytes, base64, or local model paths written in common key or value variants
- **THEN** the Web UI SHALL redact or omit those sensitive keys and values before rendering writer config panels, submitting writer config payloads, or rendering reader-visible artifact metadata
- **AND** safe writer configuration and reader-facing artifact metadata SHALL remain visible.

#### Scenario: Web client manages multimodal diagnostics records
- **GIVEN** browser-side Web client code issues multimodal diagnostics or eval-run list, detail, or run requests through same-origin API routes
- **AND** the world or eval-run identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.

#### Scenario: Web server admin loaders fetch scoped backend records
- **GIVEN** server-rendered Web admin loader code fetches world-scoped provider, media, visual, speech, invocation, or multimodal diagnostics records from backend API routes
- **AND** the world identifier or a nested backend record identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web server loader constructs the backend API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the backend API path
- **AND** query-string filters SHALL be encoded as query data
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.


#### Scenario: Web beta feedback server loader fetches scoped backend records
- **GIVEN** server-rendered Web beta feedback loader code fetches world-scoped worldline, feedback report, or membership records from backend API routes
- **AND** the world identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web server loader constructs the backend API URL
- **THEN** the world identifier segment SHALL be encoded before it is appended to the backend API path
- **AND** query-string and fragment delimiters SHALL remain encoded inside the world identifier path segment rather than becoming request query parameters or fragments.

#### Scenario: Web server workspace loaders fetch scoped backend records
- **GIVEN** server-rendered Web loader code fetches world workspace, agent detail, conversation, player, reader, worldline, or platform memory backend records from backend API routes
- **AND** the world identifier or a nested backend record identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web server loader constructs the backend API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the backend API path
- **AND** query-string filters SHALL be encoded as query data
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.

#### Scenario: Web client manages core world operations
- **GIVEN** browser-side Web client code issues core world management, worldline, GM, resolution rule, player actor, or player choice requests through same-origin API routes
- **AND** the world identifier or nested route identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string filters SHALL be encoded as query data
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.

#### Scenario: Web client manages clock, replay, and scene graph operations
- **GIVEN** browser-side Web client code issues world clock, replay, snapshot, event audit, scene, or location-edge requests through same-origin API routes
- **AND** the world identifier or nested scene/location-edge identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string filters SHALL be encoded as query data
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.

#### Scenario: Web client manages organizations, agents, calendars, and schedule rules
- **GIVEN** browser-side Web client code issues organization, organization membership, faction track, agent relationship, agent presence, agent calendar, schedule rule, or calendar conflict requests through same-origin API routes
- **AND** the world identifier or nested organization, membership, track, agent, relationship, calendar entry, or schedule rule identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string filters SHALL be encoded as query data
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.

#### Scenario: Web client manages daily-life and offscreen event operations
- **GIVEN** browser-side Web client code issues daily-life preview, daily-life generation, daily-life candidate, offscreen event create/list, or offscreen event resolve requests through same-origin API routes
- **AND** the world identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string filters SHALL be encoded as query data
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.


#### Scenario: Web client manages story, route, ending, authoring, release, and beta checklist operations
- **GIVEN** browser-side Web client code issues story hook, plot thread, route affinity, route milestone, ending candidate, long-run eval, authoring template, release profile, or beta checklist requests through same-origin API routes
- **AND** the world identifier or nested ending, authoring template, or checklist run identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string filters SHALL be encoded as query data
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.

#### Scenario: Web client manages event trigger, scene beat, episode, group, relationship, conflict, rumor, and dashboard operations
- **GIVEN** browser-side Web client code issues event trigger condition, scene beat, daily episode, group interaction, relationship suggestion, organization conflict, rumor, rumor propagation, or living-world dashboard requests through same-origin API routes
- **AND** the world identifier or nested condition, group interaction, relationship suggestion, organization conflict, or rumor propagation identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string filters SHALL be encoded as query data
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.


#### Scenario: Web client manages knowledge, secret, emotion, relationship repair, player record, privacy, and review operations
- **GIVEN** browser-side Web client code issues knowledge, secret, emotional state, relationship repair, player journal, notification, intervention, player privacy, GM style review, or narrative continuity review requests through same-origin API routes
- **AND** the world identifier or nested secret or relationship repair identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string filters SHALL be encoded as query data
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.


#### Scenario: Web client manages agent memory, persona, observation, run, and narrative artifact operations
- **GIVEN** browser-side Web client code issues agent memory, memory profile snapshot, agent run, agent persona, agent observation, manual agent run, narrative artifact, publish/unpublish, agent update, or agent deactivate requests through same-origin API routes
- **AND** the world identifier or nested agent, run, or narrative artifact identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string filters SHALL be encoded as query data
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters
- **AND** agent memory POST requests, including memory search requests with request bodies, SHALL include the same double-submit CSRF header used by other Web world mutations.


#### Scenario: Web client manages memberships, member candidates, and world diagnostics
- **GIVEN** browser-side Web client code issues membership list, membership upsert/delete, member candidate search, or world diagnostics requests through same-origin API routes
- **AND** the world identifier or nested user identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string filters SHALL be encoded as query data
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.

#### Scenario: Web client manages platform admin presets, memory backends, memory jobs, and provider profiles
- **GIVEN** browser-side Web client code issues platform admin agent preset, memory backend profile, memory write job retry, or provider profile requests through same-origin API routes
- **AND** the preset, memory backend profile, memory write job, or provider profile identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string filters SHALL be encoded as query data
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.

#### Scenario: Web client manages private beta onboarding and beta feedback
- **GIVEN** browser-side Web client code issues private beta player profile bootstrap, beta feedback report list/create/triage requests, or private beta player-surface navigation
- **AND** the world identifier or beta feedback report identifier contains encoded path separators or other reserved path characters
- **WHEN** the Web client constructs the same-origin API URL or local player-surface link
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path or app route path
- **AND** query-string filters SHALL be encoded as query data
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.


#### Scenario: Web clients normalize backend error details before notices
- **GIVEN** browser-side auth, admin, world, media, private-beta, or beta-feedback clients receive non-2xx JSON error responses from same-origin API routes
- **WHEN** `detail` or `detail.message` contains provider secrets, auth tokens, storage refs, filesystem or object-storage paths, local model paths, raw prompt/output markers, prompt snapshot refs, bytes, or base64-like evidence
- **THEN** the thrown client error message SHALL use the route-appropriate generic failure text instead of preserving the forbidden key or value
- **AND** safe business error text such as forbidden/validation messages MAY be preserved when it contains no forbidden marker
- **AND** structured publication gate summaries MAY be preserved only when the resulting summary contains no forbidden marker.


#### Scenario: Web server loaders normalize backend error details before thrown errors
- **GIVEN** server-side Web loaders for worlds or beta feedback receive non-2xx JSON error responses from backend API routes
- **WHEN** `detail` contains provider secrets, auth tokens, storage refs, filesystem or object-storage paths, local model paths, raw prompt/output markers, prompt snapshot refs, bytes, or base64-like evidence
- **THEN** any loader error that is rethrown to the Next.js server error boundary or server logs SHALL use the route-appropriate generic failure text instead of preserving the forbidden key or value
- **AND** loaders that convert backend failures into fixed page `loadError` strings SHALL continue to return those fixed strings.


#### Scenario: Web API proxies normalize backend JSON error bodies
- **GIVEN** same-origin Web API proxies relay non-2xx JSON responses from backend API routes to browser clients
- **WHEN** the response body `detail`, `detail.message`, or nested error fields contain provider secrets, auth tokens, storage refs, filesystem or object-storage paths, local model paths, raw prompt/output markers, prompt snapshot refs, bytes, or base64-like evidence
- **THEN** the proxied browser response body SHALL replace or omit the forbidden key or value before it reaches the browser
- **AND** successful JSON, binary media, no-content responses, safe error summaries, streaming responses, and explicit auth cookie relay behavior SHALL remain unchanged.


#### Scenario: Web dashboard world navigation preserves query boundaries
- **GIVEN** browser-side dashboard code navigates to a selected or newly created world through the local `world` query parameter
- **AND** the world identifier contains query-string or fragment delimiters
- **WHEN** the component calls local navigation
- **THEN** the world identifier SHALL be encoded as a single query parameter value
- **AND** delimiter characters SHALL NOT become additional query parameters or fragments.

#### Scenario: Web UI links preserve local app route boundaries
- **GIVEN** browser-side Web UI components render local workspace, agent, conversation, player, reader, or narrative links
- **AND** the world identifier or nested app route identifier contains encoded path separators or other reserved path characters
- **WHEN** the component constructs a Next.js `Link` href or a browser navigation path
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the app route path
- **AND** query-string delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters.


#### Scenario: Web client event stream subscriptions preserve local API route boundaries
- **GIVEN** browser-side Web UI components subscribe to world or conversation event streams through same-origin Next API routes
- **AND** the world identifier or conversation identifier contains encoded path separators or other reserved path characters
- **WHEN** the component constructs the EventSource URL
- **THEN** every dynamic identifier segment SHALL be encoded before it is appended to the frontend API path
- **AND** query-string and fragment delimiters SHALL remain encoded inside identifier path segments rather than becoming request query parameters or fragments.

#### Scenario: Web reader media rendering accepts scoped download paths
- **GIVEN** browser-side Web playback or scene components render reader media descriptors
- **AND** a descriptor supplies a `download_url` value
- **WHEN** the client converts the descriptor URL into a same-origin media path
- **THEN** it SHALL accept only exact reader media object download routes with UUID world, worldline, and object path segments
- **AND** it SHALL reject query strings, fragments, extra path segments, non-reader media routes, and non-backend media schemes before rendering image or audio sources.
