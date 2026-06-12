## 1. Planning / Preflight

- [x] 1.1 Reconfirm realtime git status, HEAD, branch, worktree, OpenSpec active changes, OpenSpec strict validation, services/containers, and test entry points from the server.
- [x] 1.2 Read the current harness, architecture contracts, v0.9/v1.0/v1.1 archives, release notes, and spec entry points needed for audit continuity.
- [x] 1.3 Create `feature/audit-and-hardening-post-v1-1-rc` from clean `main` and scaffold this OpenSpec change.
- [x] 1.4 Validate the OpenSpec proposal/design/spec/tasks and record initial harness state for the audit branch.

## 2. Backend Security Audit

- [x] 2.1 Audit FastAPI auth/session dependencies, CSRF requirements, admin/platform/world-member contexts, and router authorization patterns.
- [ ] 2.2 Audit worldline isolation checks across worlds, conversations, media, visual, speech, memory, player sessions, beta feedback, moderation, and observability evidence.
- [x] 2.3 Audit provider spend and secret boundaries across provider execution, image, speech, visual generation, runtime, reliability fallback, and smoke/test paths.
- [ ] 2.4 Audit raw prompt/output, storage URI/path, filesystem path, local model path, bytes/base64, invite token, and prompt snapshot exposure in API DTOs, events, reports, manifests, logs, and tests.
- [x] 2.5 Record backend findings with severity, evidence, affected files/routes, proposed remediation order, and targeted tests.

## 3. Backend Remediation Batches

- [x] 3.1 Implement the first confirmed high-risk backend security fix with the smallest practical code change.
- [x] 3.2 Add or update targeted backend regression tests for the fixed boundary.
- [x] 3.3 Run focused backend ruff/mypy/pytest for the touched files and record results.
- [x] 3.4 Update OpenSpec tasks and harness documents for the backend batch.
- [x] 3.5 Commit the backend batch without pushing.

## 4. Web And E2E Security Audit

- [ ] 4.1 Audit Next route handlers and API proxies for CSRF, auth forwarding, route-boundary preservation, role boundary, evidence redaction, and client-side leaks.
- [ ] 4.2 Audit Web client rendering for XSS-prone content, admin/player/member separation, provider status/degraded state exposure, and forbidden internal metadata.
- [ ] 4.3 Audit existing Playwright/project e2e coverage for security and boundary gaps without using browser/computer-use plugins.
- [ ] 4.4 Record Web/e2e findings with severity, evidence, remediation order, and targeted tests.

## 5. Product Normal-Use Audit

- [ ] 5.1 Audit v1.1 RC normal-use flows: onboarding, player resume, feedback, quota/degraded state, import/export, provider reliability, and release-candidate evidence UX.
- [ ] 5.2 Record product findings with severity, user impact, affected flows, remediation order, and targeted tests.
- [ ] 5.3 Use `impeccable` before any Web UI implementation work in this change.

## 6. Spec And History Compliance Audit

- [ ] 6.1 Compare OpenSpec current specs against implementation and tests for audited backend/security boundaries.
- [ ] 6.2 Compare v0.9/v1.0/v1.1 archives and release notes against current code, tests, and harness records for drift.
- [ ] 6.3 Add required spec deltas or documentation updates before behavior-changing fixes.

## 7. Closeout

- [ ] 7.1 Run OpenSpec strict validation, `git diff --check`, targeted tests, and the broadest practical full gate for completed batches.
- [ ] 7.2 Update `project-index.md`, `file-inventory.md`, `change-journal.md`, and `handoffs/active-session.md` with final branch, commit, tests, findings, and residual risks.
- [ ] 7.3 Ensure git status is clean and report branch, commits, tests run, tests not run, remaining risks, and push status.

## Findings

### F-001 Backend CSRF gaps on persisted moderation/privacy/package mutations

- Severity: High
- Affected boundary: backend auth/session CSRF protection for browser-cookie authenticated write routes.
- Evidence: AST audit found backend/services/api/src/noveland/services/api/moderation.py report/review/action/incident mutations, backend/services/api/src/noveland/services/api/player_privacy.py export/delete/review mutations, and backend/services/api/src/noveland/services/api/world_packaging.py import apply lack require_csrf in function body or route dependencies while using cookie-backed authenticated contexts.
- Impact: a cross-site request from an authenticated browser could submit moderation reports/actions/incidents, create player privacy export/delete requests, review privacy requests, or apply a world package without a matching CSRF token.
- Intended remediation: add decorator-level Depends(require_csrf) to persisted mutation routes only, keep read-only/preview POSTs unchanged for now, and add targeted regression assertions for missing CSRF rejection.
- Status: Remediated in backend CSRF batch 1.
- Verification: uv run pytest tests/test_api_moderation.py tests/test_api_player_privacy.py tests/test_api_world_packaging.py passed with 18 passed; uv run ruff check on the six touched backend/test files passed; uv run mypy on the same six files passed.
- Residual scope: remaining POST endpoints without CSRF are login, package/world-composition validate, visual resolve, memory search, and world package preview/export-preview/import-preview; these are non-persisting/public/query-style paths and remain candidates for later policy review rather than this persisted mutation fix.


### F-002 Legacy provider profile execution bypasses ProviderExecutionService

- Severity: High
- Affected boundary: provider spend/quota, invocation ledger, prompt snapshot, and provider secret execution boundary.
- Evidence: backend/packages/adapters/src/noveland/adapters/model_provider.py ProviderProfileService.invoke_profile resolves API keys from provider_api_keys_json and creates plugin providers directly; backend/services/api/src/noveland/services/api/runtime.py test_provider_profile calls ProviderProfileService.test_profile; backend/services/runtime/src/noveland/services/runtime/agent_loop.py calls ProviderProfileService.invoke_profile during agent runs; backend/services/api/src/noveland/services/api/worlds.py and backend/services/api/src/noveland/services/api/conversations.py construct AgentRuntimeOrchestrator or ConversationNarrativeWriterService with ProviderProfileService; backend/packages/narrative/src/noveland/narrative/services.py invokes the profile service for summary/chapter generation.
- Impact: legacy provider profile test calls, manual agent runs, conversation advancement, runtime daemon turns, and narrative generation can reach external provider plugins/httpx without ProviderExecutionService, the provider registry budget checks, uniform safe auth metadata, and the newer provider execution failure handling. Some agent runtime paths write invocation rows around the call, but quota and centralized secret/provider execution policy are still bypassed.
- Remediation: ProviderProfileService.invoke_profile now blocks legacy profile execution with a safe configuration error before API key lookup, rate-limit accounting, plugin provider creation, or HTTP transport. Provider profile test calls record a failed configuration status instead of executing external spend.
- Verification: uv run pytest tests/test_model_provider.py tests/test_api_runtime.py tests/test_runtime_daemon.py passed with 20 passed; uv run ruff check packages/adapters/src/noveland/adapters/model_provider.py tests/test_model_provider.py passed; uv run mypy packages/adapters/src/noveland/adapters/model_provider.py tests/test_model_provider.py passed.
- Residual scope: migrating legacy platform provider profiles into world-scoped ProviderExecutionService-backed provider integrations remains future work; until then legacy execution is blocked/degraded.


### F-003 Member media asset API leaks internal storage references

- Severity: High
- Affected boundary: reader/member API exposure of internal media storage references.
- Evidence: backend/services/api/src/noveland/services/api/media.py list_media_assets, search_media_assets, and get_media_asset use get_world_member_context but return MediaAssetRecord; backend/packages/media/src/noveland/media/contracts.py MediaAssetRecord includes storage_uri, preview_uri, and thumbnail_uri; backend/packages/media/src/noveland/media/service.py _asset_record copies those fields from MediaAsset without redaction. Uploaded or registered visible assets can therefore expose media:// storage references to ordinary world members.
- Impact: world members can learn internal object-storage keys/URIs for visible media assets outside the reader-safe media descriptor/download route, violating architecture-contracts and increasing storage path disclosure risk.
- Remediation: media asset list/search/get responses now redact asset-level storage_uri, preview_uri, and thumbnail_uri when served to non-admin member contexts, while world admins/platform admins keep storage reference visibility for media management.
- Verification: uv run pytest tests/test_api_media.py tests/test_api_reader_media.py passed with 12 passed; uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py passed; uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py passed.
- Residual scope: member-facing media metadata, context/input/reference metadata, and broader forbidden-data response paths remain under the ongoing 2.4 audit.

### F-004 Member media job APIs expose provider/request/result internals

- Severity: High
- Affected boundary: member media API exposure of provider configuration, request/result payloads, raw prompt/output-like evidence, storage references, and actor refs.
- Evidence: backend/services/api/src/noveland/services/api/media.py list_media_jobs and get_media_job use get_world_member_context and return MediaJobRecord; backend/packages/media/src/noveland/media/contracts.py MediaJobRecord includes provider_config_json, request_json, result_json, error_text, and created_by_actor_ref. Media jobs can contain provider IDs/config, prompts, storage_uri/media object refs, bytes/base64 markers, and execution failures intended for admin diagnostics.
- Impact: any authenticated world member can enumerate or fetch media jobs for their world and read internal provider/media execution evidence that architecture-contracts reserves for admin/operator surfaces.
- Intended remediation: make media job list/detail admin-only using the existing world admin dependency, preserve admin media management visibility, and add targeted regression coverage that ordinary members receive 403 while admins still receive job internals.
- Status: Remediated in backend media job boundary batch.
- Verification: uv run pytest tests/test_api_media.py tests/test_api_reader_media.py passed with 13 passed; uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py passed; uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py passed.

### F-005 Member media lineage leaks related asset storage references

- Severity: High
- Affected boundary: member media API exposure of internal storage references through nested lineage DTOs.
- Evidence: backend/services/api/src/noveland/services/api/media.py media_asset_lineage uses get_world_member_context but returns MediaLineageService.lineage directly; backend/packages/media/src/noveland/media/catalog.py MediaLineageService.lineage builds related_assets with _asset_record(model), which includes storage_uri, preview_uri, and thumbnail_uri from MediaAssetRecord. The F-003 response shaping only redacts top-level media asset list/search/get records, not lineage related_assets.
- Impact: a world member who can read visible media lineage can learn internal object-storage keys/URIs for related visible assets through the nested related_assets array.
- Intended remediation: shape MediaAssetLineage.related_assets through the existing member/admin media asset redaction helper in the API layer and add regression coverage for member redaction plus admin preservation.
- Status: Remediated in backend media lineage redaction batch.
- Verification: uv run pytest tests/test_api_media.py tests/test_api_reader_media.py passed with 13 passed; uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py passed; uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py passed.

### F-006 Member media metadata-bearing DTOs expose arbitrary forbidden data

- Severity: High
- Affected boundary: member media API exposure of admin-authored arbitrary metadata across visible media records.
- Evidence: backend/services/api/src/noveland/services/api/media.py member-readable routes return MediaAssetRecord, MediaContextRecord, MediaAssetInputRecord, MediaAssetTagRecord, MediaAssetCollectionRecord, MediaAssetCollectionItemRecord, MediaAssetReferences, and MediaAssetLineage. backend/packages/media/src/noveland/media/contracts.py defines metadata: dict[str, Any] on these records, and service/catalog record builders copy metadata_json without response sanitization. Admins can attach metadata containing storage_uri/media:// refs, filesystem paths, raw_prompt/raw_output markers, secret/auth keys, bytes, or base64 values, which ordinary members can read when the asset/tag/collection is visible.
- Impact: ordinary world members can receive internal storage paths, raw execution evidence markers, secret-like metadata, or binary/base64 markers through otherwise visible media catalog and lineage endpoints.
- Intended remediation: add API-layer member metadata sanitization for all member-facing media record shapes while preserving admin metadata visibility, and add regression coverage across top-level and nested media DTOs.
- Status: Remediated in backend member media metadata redaction batch.
- Verification: uv run pytest tests/test_api_media.py tests/test_api_reader_media.py passed with 14 passed; uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py passed; uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py passed.

### F-007 Realtime member streams expose internal run, diagnostic, and hidden narrative payloads

- Severity: High
- Affected boundary: member-readable realtime world/conversation streams.
- Evidence: backend/services/api/src/noveland/services/api/realtime.py authenticates the world and conversation stream routes with require_world_member, while collect_world_stream_delta serializes runtime diagnostics, agent run prompt_text, response_text, provider_profile_id, and run diagnostics, all narrative artifacts regardless publication visibility, and conversation session opening_prompt, policy_config, and writer_config. The conversation stream and live snapshot also serialize diagnostic details to ordinary world members.
- Impact: ordinary world members can receive operator-only prompts, raw model output-like run text, provider/run diagnostic evidence, hidden or unpublished narrative content, and conversation policy/writer internals over realtime channels despite admin REST routes keeping diagnostics and event audit admin-only.
- Intended remediation: shape realtime stream payloads by caller role; preserve full diagnostics and execution details for world admins while restricting member streams to safe clock, reader-visible published narrative artifacts, safe conversation/turn updates, and no diagnostic/run internals.
- Status: Remediated in backend realtime member-stream redaction batch.
- Verification: uv run pytest tests/test_api_realtime.py passed with 6 passed; uv run ruff check services/api/src/noveland/services/api/realtime.py tests/test_api_realtime.py passed; uv run mypy services/api/src/noveland/services/api/realtime.py tests/test_api_realtime.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-008 Member agent run list exposes prompt, response, provider, and diagnostic internals

- Severity: High
- Affected boundary: member-readable agent runtime run list REST API.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/agents/{agent_id}/runs with get_world_member_context, and list_agent_runs serializes AgentRunResponse through _agent_run_response. AgentRunResponse includes prompt_text, response_text, provider_profile_id, and diagnostics derived from AgentRuntimeRun records.
- Impact: ordinary world members can read operator prompts, raw/model response-like run output, provider profile references, and execution diagnostics through non-realtime REST responses despite detailed run routes and diagnostic routes being admin-only.
- Intended remediation: shape agent run list responses by caller role; preserve run internals for admins while ordinary members receive only safe identifiers, status, trigger/source linkage, and timing fields with prompt, response, provider, and diagnostic internals redacted.
- Status: Remediated in backend agent run list redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_agent_runs_and_narrative_artifacts_api tests/test_api_worlds.py::test_agent_run_apis_filter_by_worldline passed with 2 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-009 Member agent catalog exposes provider profile refs and admin config

- Severity: High
- Affected boundary: member-readable agent catalog REST API.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/agents with get_world_member_context, and list_agents serializes AgentResponse through _agent_response. AgentResponse includes provider_profile_id derived from agent.config and the full agent.config dictionary, which can contain provider profile refs and arbitrary admin execution/provider configuration.
- Impact: ordinary world members can enumerate provider profile references and internal agent configuration through the agent catalog even though provider/runtime execution details are reserved for admin/operator surfaces.
- Intended remediation: shape agent catalog responses by caller role; preserve full provider/config details for admins while ordinary members receive safe public agent identity and characterization fields with provider refs and config redacted.
- Status: Remediated in backend agent catalog redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_create_agent_from_preset_materializes_persona_calendar_and_provider_mapping tests/test_api_worlds.py::test_world_admin_manages_scenes_agents_and_conflicts tests/test_api_worlds.py::test_agent_runs_and_narrative_artifacts_api passed with 3 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-010 Member world profile exposes plugin refs and admin config

- Severity: High
- Affected boundary: member-readable world profile/list REST APIs.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id} with get_world_member_context and root GET /worlds includes member-owned worlds. Both serialize WorldResponse through _world_response. WorldResponse includes rules_config, memory_plugin_identifier, memory_backend_profile_id, memory_plugin_config, world_rules_plugin_identifier, and world_rules_plugin_config.
- Impact: ordinary world members can read memory backend profile refs, plugin identifiers, rules/plugin configuration, and arbitrary admin-authored config values through world profile/list responses, exposing operator-only implementation details and potential forbidden metadata.
- Intended remediation: shape world profile/list responses by caller role; preserve full world configuration for admins while ordinary members receive safe public world identity fields with rules/plugin/backend config redacted.
- Status: Remediated in backend world profile redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_world_member_can_read_but_not_mutate_and_non_member_is_hidden tests/test_api_worlds.py::test_platform_admin_can_create_list_and_update_worlds passed with 2 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-011 Member schedule rule list exposes admin rule config

- Severity: High
- Affected boundary: member-readable schedule rule list REST API.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/schedule-rules with get_world_member_context, and list_schedule_rules serializes ScheduleRuleResponse through _schedule_rule_response. ScheduleRuleResponse includes config copied from WorldScheduleRule config.
- Impact: ordinary world members can read arbitrary admin-authored schedule rule configuration, including provider/profile refs, prompt-like scheduling instructions, storage refs, or other execution details intended for operators.
- Intended remediation: shape schedule rule list responses by caller role; preserve full rule config for admins while ordinary members receive safe rule identity, kind, and enabled state with config redacted.
- Status: Remediated in backend schedule rule redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_world_admin_manages_calendar_entries_and_schedule_rules tests/test_api_worlds.py::test_world_composition_export_and_import_round_trip passed with 2 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-012 Member narrative artifact REST responses expose publication and artifact internals

- Severity: High
- Affected boundary: member-readable narrative artifact list/detail REST API.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/narrative-artifacts and GET /worlds/{world_id}/narrative-artifacts/{artifact_id} with get_world_member_context. The routes filter ordinary members to published/reader-visible artifacts, but still serialize NarrativeArtifactResponse through _narrative_artifact_response, which returns source_run_id, metadata, continuity_metadata, continuity_status, and nested publication metadata, source_draft_id, published_by_user_id, and publication_gate.
- Impact: ordinary world members can read operator-only run references, arbitrary artifact metadata, continuity/review evidence, publication gate details, and publisher user refs through REST responses despite realtime member streams already redacting those fields.
- Intended remediation: shape narrative artifact REST responses by caller role; preserve metadata and publication evidence for admins while ordinary members receive safe published artifact content, identity, conversation linkage, publication status, reader visibility, and timing fields with internals redacted.
- Status: Remediated in backend narrative artifact REST redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_narrative_reader_api_supports_filters_and_detail_for_world_members tests/test_api_worlds.py::test_narrative_publication_workflow_filters_reader_visibility tests/test_api_realtime.py::test_world_stream_hides_admin_evidence_for_member_payloads passed with 3 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py tests/test_api_realtime.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py tests/test_api_realtime.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs.

### F-013 Member organization list exposes hidden summary and metadata

- Severity: High
- Affected boundary: member-readable organization list REST API.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/organizations with get_world_member_context, and list_organizations serializes OrganizationResponse through _organization_response. OrganizationResponse includes hidden_summary and metadata copied from WorldOrganization records.
- Impact: ordinary world members can read hidden organization narrative/operator summaries and arbitrary admin-authored metadata that may include raw prompt/output markers, storage refs, provider refs, secrets, bytes, base64, or other internal evidence.
- Intended remediation: shape organization list responses by caller role; preserve hidden_summary and metadata for admins while ordinary members receive safe public organization identity, description, public_summary, active state, and timing fields with hidden internals redacted.
- Status: Remediated in backend organization list redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_organization_memberships_and_faction_tracks_append_events passed with 1 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs.

### F-014 Member organization membership and faction track metadata leaks

- Severity: High
- Affected boundary: member-readable organization membership and faction progress track list REST APIs.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/organizations/{organization_id}/memberships and GET /worlds/{world_id}/organizations/{organization_id}/faction-tracks with get_world_member_context, and list responses serialize OrganizationMembershipResponse and FactionProgressTrackResponse through helpers that copy metadata_json directly.
- Impact: ordinary world members can read arbitrary admin-authored organization membership and faction-track metadata that may include raw prompt/output markers, storage refs, provider refs, secrets, bytes, base64, or other internal evidence.
- Intended remediation: shape membership and faction-track list responses by caller role; preserve metadata for admins while ordinary members receive safe organization/agent identity, role, visibility, responsibility, progress, pressure, summary, and timing fields with metadata redacted.
- Status: Remediated in backend organization membership/faction track redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_organization_memberships_and_faction_tracks_append_events passed with 1 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-015 Member worldline list metadata leaks

- Severity: High
- Affected boundary: member-readable worldline list REST API.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/worldlines with get_world_member_context, and list_worldlines serializes WorldlineResponse through _worldline_response, which copies metadata_json directly.
- Impact: ordinary world members can read arbitrary admin-authored worldline metadata that may include raw prompt/output markers, storage refs, provider refs, secrets, bytes, base64, or other internal branch-management evidence.
- Intended remediation: shape worldline list responses by caller role; preserve metadata for admins while ordinary members receive safe branch identity, parent/fork references, status, actor ref, and timing fields with metadata redacted.
- Status: Remediated in backend worldline list redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_world_member_can_read_safe_worldline_comparison_without_mutation passed with 1 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-016 Member player choice prompt leaks

- Severity: High
- Affected boundary: member-readable player choice create/list REST APIs.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/player-choices and POST /worlds/{world_id}/player-choices with get_world_member_context, and responses serialize PlayerChoiceResponse through _player_choice_response, which copies prompt directly.
- Impact: ordinary world members can receive prompt text through player choice responses; prompt text may include raw prompt/output markers, storage refs, provider refs, secrets, bytes, base64, or other internal evidence.
- Intended remediation: shape player choice responses by caller role; preserve prompt text for admins while ordinary members receive safe choice identity, selected option, context, consequence preview, applied event ref, and timing fields with prompt redacted.
- Status: Remediated in backend player choice prompt redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope passed with 1 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-017 Member player choice preview diagnostics leak

- Severity: High
- Affected boundary: member-readable player choice preview REST API.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes POST /worlds/{world_id}/player-choices/preview with get_world_member_context, computes can_manage, but returns ChoiceConsequencePreviewResponse.diagnostics=preview.diagnostics directly.
- Impact: ordinary world members can receive diagnostic strings through player choice preview responses; diagnostics may expose provider refs, raw prompt/output markers, storage refs, secret/auth refs, bytes/base64 markers, or internal rule/effect evidence as preview diagnostics evolve.
- Intended remediation: shape player choice preview responses by caller role; preserve diagnostics for admins while ordinary members receive safe relationship, faction, and offscreen consequence preview fields with diagnostics redacted.
- Status: Remediated in backend player choice preview diagnostics redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope passed with 1 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-018 Member living world dashboard hidden secret count leak

- Severity: High
- Affected boundary: member-readable living world dashboard REST API.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/living-world-dashboard with get_world_member_context and returns _living_world_dashboard_response(dashboard); LivingWorldDashboardResponse includes hidden_secret_count, and _living_world_dashboard_response copies dashboard.hidden_secret_count directly.
- Impact: ordinary world members can infer the existence and count of hidden secrets in a worldline through a general dashboard route, revealing hidden/admin-only narrative state even when secret records themselves remain admin-only.
- Intended remediation: shape living world dashboard responses by caller role; preserve hidden_secret_count for admins while ordinary members receive safe aggregate dashboard fields with hidden_secret_count redacted to zero.
- Status: Remediated in backend living world dashboard hidden count redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_knowledge_player_guardrail_apis_and_acceptance_gap_fixes passed with 1 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-019 Member journal, notification, and intervention evidence leaks

- Severity: High
- Affected boundary: member-readable player journal, in-world notification, and player intervention REST APIs.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/player-journal, GET /worlds/{world_id}/notifications, and GET/POST /worlds/{world_id}/interventions with get_world_member_context. Their responses serialize JournalEntryResponse, InWorldNotificationResponse, and PlayerInterventionResponse through helpers that copy source_event_id, source_ref, metadata_json, prompt, choice_id, and event_id directly.
- Impact: ordinary world members can read source evidence refs, intervention prompt text, choice/event linkage, and arbitrary metadata that may include raw prompt/output markers, storage refs, provider refs, secret/auth refs, bytes, base64, or other operator-only evidence.
- Intended remediation: shape journal, notification, and intervention responses by caller role; preserve source refs, prompt text, choice/event linkage, and metadata for admins while ordinary members receive safe title/body/status/target/timing fields with internals redacted.
- Status: Remediated in backend journal/notification/intervention redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_knowledge_player_guardrail_apis_and_acceptance_gap_fixes tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope passed with 2 targeted tests; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-020 Member agent relationship and calendar metadata leaks

- Severity: High
- Affected boundary: member-readable agent relationship list and agent calendar list REST APIs.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/agents/{agent_id}/relationships and GET /worlds/{world_id}/agents/{agent_id}/calendar with get_world_member_context. The responses serialize AgentRelationshipResponse through _agent_relationship_response and CalendarEntryResponse through _calendar_entry_response, both copying metadata dictionaries directly.
- Impact: ordinary world members can read arbitrary relationship and scheduling metadata that may include raw prompt/output markers, storage refs, provider refs, secret/auth refs, source evidence refs, bytes, base64, or other operator-only evidence.
- Intended remediation: shape agent relationship and calendar list responses by caller role; preserve metadata for admins while ordinary members receive safe relationship identity/score fields and calendar title/time/status fields with metadata redacted.
- Status: Remediated in backend relationship/calendar metadata redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_agent_relationship_graph_enforces_world_scope_and_updates_edges tests/test_api_worlds.py::test_world_admin_manages_calendar_entries_and_schedule_rules passed with 2 targeted tests; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-021 Member latest snapshot payload and storage reference leak

- Severity: High
- Affected boundary: member-readable world snapshot REST API.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/snapshots/latest with get_world_member_context. The route serializes WorldSnapshotResponse through _snapshot_response, which copies snapshot.payload, snapshot.payload_uri, payload_location, and metadata directly from WorldSnapshotRecord.
- Impact: ordinary world members can read internal object-storage URIs for object-backed snapshots or inline replay snapshot payloads and metadata. Snapshot metadata can include storage backend details, payload byte counts, raw event/state evidence markers, storage refs, provider refs, bytes/base64 markers, or other operator-only replay evidence.
- Intended remediation: shape latest snapshot responses by caller role; preserve payload, payload_uri, payload_location, and metadata for admins while ordinary members receive safe snapshot identity, worldline, sequence coverage, schema/status, source event ref, and creation time with snapshot internals redacted.
- Status: Remediated in backend latest snapshot redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_replay_and_snapshot_api_reads_state_and_creates_snapshot passed with 1 targeted test; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.


### F-022 Member release profile policy and evidence leak

- Severity: High
- Affected boundary: member-readable living-world release profile REST API.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/release-profile with get_world_member_context. The route serializes ReleaseProfileResponse through _release_profile_response, which copies branch_policy, backup_policy, content_review_policy, player_permission_policy, worldline_policy, checklist, and metadata directly from LivingWorldReleaseProfile. LivingWorldBetaService.upsert_release_profile adds gate_decision evidence refs into checklist and metadata.
- Impact: ordinary world members can read release policy internals, gate decisions, checklist evidence refs, worldline refs, backup/review requirements, and arbitrary metadata that may include raw prompt/output markers, storage refs, provider refs, secret/auth refs, bytes, base64, or other operator-only release evidence.
- Intended remediation: shape release profile responses by caller role; preserve policies, checklist, and metadata for admins while ordinary members receive safe profile identity, status, and timing fields with release internals redacted.
- Status: Remediated in backend release profile redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_beta_release_readiness_apis_cover_routes_evals_authoring_and_checklist passed with 1 targeted test; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-023 Member world bible source and continuity evidence leak

- Severity: High
- Affected boundary: member-readable world bible REST API.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/bible with get_world_member_context. The route serializes WorldBibleResponse through _world_bible_response, which copies source_material, continuity_config, and metadata directly from WorldBible. The Web overview non-admin branch also renders data.worldBible.source_material.
- Impact: ordinary world members can read raw source material/import notes, continuity configuration, and arbitrary metadata that may include raw prompt/output markers, storage refs, provider refs, secret/auth refs, bytes, base64, or other operator-only canon management evidence.
- Intended remediation: shape world bible responses by caller role; preserve source_material, continuity_config, and metadata for admins while ordinary members receive safe canon timeline, setting rules, forbidden changes, sequel boundaries, continuity status, identity, and timing fields with source/config/metadata internals redacted.
- Status: Remediated in backend world bible redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_world_bible_api_preserves_continuity_contract_and_access passed with 1 targeted test; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-024 Member agent presence scheduling evidence leak

- Severity: High
- Affected boundary: member-readable agent presence REST API.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/agents/{agent_id}/presence with get_world_member_context. The route serializes AgentPresenceResponse through _presence_response, which copies scheduled_movement and last_event_id directly from AgentPresenceState. Existing regression coverage asserted that ordinary members received scheduled_movement.
- Impact: ordinary world members can infer future/offscreen movement plans and source event linkage. Scheduled movement is an arbitrary JSON dictionary and may contain raw prompt/output markers, storage refs, provider refs, secret/auth refs, bytes, base64, scene-planning notes, or other operator-only scheduling evidence.
- Intended remediation: shape agent presence responses by caller role; preserve scheduled_movement and last_event_id for admins while ordinary members receive safe current scene, visibility, encounter eligibility, identity, worldline, and timing fields with scheduling internals redacted.
- Status: Remediated in backend agent presence redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_location_graph_and_agent_presence_enforce_world_scope passed with 1 targeted test; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-025 Member conversation session orchestration internals leak

- Severity: High
- Affected boundary: member-readable conversation session list/detail REST APIs.
- Evidence: backend/services/api/src/noveland/services/api/conversations.py exposes GET /worlds/{world_id}/conversations and GET /worlds/{world_id}/conversations/{conversation_id} with get_world_member_context. Both serialize ConversationSessionResponse through _session_response, which copies objective, opening_prompt, policy, writer_config, memory_config, and group_context directly from ConversationSessionRecord. Realtime member streams were already hardened for similar conversation policy/writer internals, but REST session responses remained unshaped.
- Impact: ordinary world members can read raw opening prompts/objectives, provider profile refs, writer plugin identifiers/config, style/source constraints, memory retrieval/write strategy, group context, and arbitrary JSON config that may contain storage refs, provider refs, raw prompt/output markers, secret/auth refs, bytes, base64, or other operator-only orchestration evidence.
- Intended remediation: shape conversation session list/detail responses by caller role; preserve orchestration internals for admins while ordinary members receive safe session identity, worldline, scene, title, scope, mode, status, turn counters, terminal state, and timing fields with session internals redacted.
- Status: Remediated in backend conversation session redaction batch.
- Verification: uv run pytest tests/test_api_conversations.py::test_conversation_api_enforces_access_and_manual_advance passed with 1 targeted test; uv run ruff check services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py passed; uv run mypy services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-026 Member conversation narrative artifact visibility and evidence leak

- Severity: High
- Affected boundary: member-readable conversation-scoped narrative artifact list REST API.
- Evidence: backend/services/api/src/noveland/services/api/conversations.py exposes GET /worlds/{world_id}/conversations/{conversation_id}/narrative with get_world_member_context. The route calls ConversationNarrativeWriterService.list_conversation_artifacts, which returns all artifacts for the conversation from NarrativeArtifactService.list_artifacts without publication or reader-visible filtering, then serializes ConversationNarrativeArtifactResponse through _narrative_artifact_response with source_run_id and metadata copied directly. The world-level narrative artifact API already filters ordinary members to published reader-visible artifacts and redacts source_run_id/metadata, but the conversation-scoped route bypasses that boundary.
- Impact: ordinary world members can list draft, unpublished, or non-reader-visible conversation summaries and chapter drafts before publication, and can read source run refs plus arbitrary artifact metadata that may include raw prompt/output markers, storage refs, provider refs, secret/auth refs, bytes, base64, or other operator-only narrative evidence.
- Intended remediation: shape conversation-scoped narrative artifact list responses by caller role; preserve full draft visibility, source refs, and metadata for admins while ordinary members receive only published reader-visible artifacts for that conversation with source_run_id and metadata redacted.
- Status: Remediated in backend conversation narrative artifact redaction batch.
- Verification: uv run pytest tests/test_api_conversations.py::test_conversation_narrative_listing_redacts_member_evidence tests/test_api_conversations.py::test_conversation_narrative_generation_and_listing passed with 2 passed; uv run ruff check services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py passed; uv run mypy services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-027 Player privacy export evidence refs leak

- Severity: High
- Affected boundary: member-readable player privacy export REST API.
- Evidence: backend/services/api/src/noveland/services/api/player_privacy.py exposes GET/POST /worlds/{world_id}/player/privacy/export with get_world_member_context. PlayerPrivacyService._build_export_payload serializes PlayerPrivacyJournalExport.source_ref from PlayerJournalEntry.source_ref, PlayerPrivacyNotificationExport.source_ref from InWorldNotification.source_ref, and PlayerPrivacyInterventionExport.choice_id/event_id from PlayerInterventionRecord directly into the player export. F-019 already classified the same player journal, notification, and intervention source refs and choice/event linkage as operator-only evidence in ordinary member-readable routes, but the privacy export still bypasses that redaction boundary.
- Impact: ordinary world members can use the privacy export to recover source evidence refs and choice/event linkage that regular player/member APIs now redact. Those refs can expose internal event, choice, source, or review linkage and may act as stable handles into operator-only evidence or worldline history.
- Intended remediation: redact journal/notification source_ref and intervention choice_id/event_id in privacy exports while preserving safe player-owned titles, bodies, selected options, target identity fields, statuses, counts, and timing fields.
- Status: Remediated in backend player privacy export evidence redaction batch.
- Verification: uv run pytest tests/test_api_player_privacy.py::test_player_privacy_export_is_player_scoped_and_redacted passed with 1 passed; uv run ruff check packages/player_privacy/src/noveland/player_privacy/service.py tests/test_api_player_privacy.py passed; uv run mypy packages/player_privacy/src/noveland/player_privacy/service.py tests/test_api_player_privacy.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-028 Member scene and location graph rule leak

- Severity: High
- Affected boundary: member-readable scene and location graph REST APIs.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/scenes and GET /worlds/{world_id}/location-edges with get_world_member_context. SceneResponse includes opening_rules copied directly from Scene.opening_rules, and SceneLocationEdgeResponse includes traversal_rules copied directly from SceneLocationEdge.traversal_rules. Those admin-authored rule/config dictionaries can contain hidden route conditions, provider refs, storage refs, raw prompt/output markers, bytes/base64 markers, secret/auth refs, or other operator-only movement/rule evidence.
- Impact: ordinary world members can enumerate scene opening conditions and location traversal internals that should remain admin/runtime planning evidence, and arbitrary rule config can leak forbidden internal refs or prompt/storage/provider evidence.
- Intended remediation: shape scene and location edge responses by caller role; preserve opening_rules and traversal_rules for admins while ordinary members receive safe scene/location identity, public descriptions, region/location tags, travel labels, active state, and timing fields with rule/config internals redacted.
- Status: Remediated in backend scene/location rule redaction batch.
- Verification: uv run pytest tests/test_api_worlds.py::test_location_graph_and_agent_presence_enforce_world_scope passed with 1 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-029 Member conversation turn runtime evidence leak

- Severity: High
- Affected boundary: member-readable conversation turn REST API.
- Evidence: backend/services/api/src/noveland/services/api/conversations.py exposes GET /worlds/{world_id}/conversations/{conversation_id}/turns with get_world_member_context. ConversationTurnResponse includes run_id and error_text copied directly from ConversationTurnRecord through _turn_response. Realtime member streams already redact those same turn fields for ordinary members, but the REST turn list still returns them.
- Impact: ordinary world members can read stable agent runtime run handles and provider/plugin failure text. error_text can contain raw output markers, provider diagnostics, storage refs, secret/auth refs, or traceback-like operator evidence, and run_id can link member-visible turns to admin-only runtime/invocation evidence.
- Intended remediation: shape conversation turn list responses by caller role; preserve run_id/error_text for admins while ordinary members receive safe turn identity, speaker, transcript text, status, and timing fields with runtime evidence redacted.
- Status: Remediated in backend conversation turn runtime evidence redaction batch.
- Verification: uv run pytest tests/test_api_conversations.py::test_conversation_api_enforces_access_and_manual_advance passed with 1 passed; uv run ruff check services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py passed; uv run mypy services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-030 Web realtime stream proxy path segment injection

- Severity: High
- Affected boundary: Web same-origin API proxy route-boundary preservation for world and conversation realtime streams.
- Evidence: web/app/api/worlds/[worldId]/stream/route.ts constructs `/worlds/${worldId}/stream` from decoded route params without encoding; web/app/api/worlds/[worldId]/conversations/[conversationId]/stream/route.ts constructs `/worlds/${worldId}/conversations/${conversationId}/stream` the same way. Other dynamic Web API proxies use encodeURIComponent, and the catch-all world/private-beta routes encode every path segment before forwarding.
- Impact: a request whose dynamic route parameter contains an encoded slash or reserved path character can be forwarded to a broader or different backend path than the fixed stream route intended. That weakens the Web proxy route boundary and can expose unintended backend stream behavior through the same-origin proxy if a crafted path still matches the frontend route.
- Intended remediation: encode every dynamic world/conversation stream route segment before constructing the backend path and add focused Web regression coverage proving encoded slashes remain inside the identifier segment rather than becoming backend path separators.
- Status: Remediated in Web realtime stream proxy path boundary batch.
- Verification: npm run test -- lib/realtime/proxy.test.ts passed with 3 passed; npm run lint passed; npm run typecheck passed; full npm run test passed with 42 files and 136 tests; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-031 Web memory backend proxy duplicates query strings

- Severity: Medium
- Affected boundary: Web same-origin runtime proxy query preservation for memory backend job and log list routes.
- Evidence: web/app/api/memory-backend-profiles/[profileId]/jobs/route.ts and web/app/api/memory-backend-profiles/[profileId]/logs/route.ts read `new URL(request.url).search` and append it to the `path` argument passed to `proxyRuntimeRequest`; web/lib/runtime/proxy.ts then appends `request.nextUrl.search` again to every backend fetch URL.
- Impact: requests such as `/api/memory-backend-profiles/{id}/jobs?status=failed&limit=5` can be proxied as `/memory-backend-profiles/{id}/jobs?status=failed&limit=5?status=failed&limit=5`, which can corrupt integer query parsing and status filtering on the backend runtime route. This weakens same-origin proxy correctness for admin memory queue visibility and can break normal diagnostic workflows.
- Intended remediation: remove route-local query concatenation from the memory backend jobs/logs route handlers and add focused Web route-handler tests proving query parameters are forwarded exactly once through the shared runtime proxy.
- Status: Remediated in Web memory backend runtime proxy query preservation batch.
- Verification: npm run test -- lib/runtime/proxy.test.ts passed with 2 passed; npm run lint passed; npm run typecheck passed; full npm run test passed with 43 files and 138 tests; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-032 Web conversation live socket path segment injection

- Severity: High
- Affected boundary: browser-side Web realtime URL construction for conversation live WebSocket control.
- Evidence: web/lib/realtime.ts constructs `${getAuthApiWebSocketBaseUrl()}/worlds/${worldId}/conversations/${conversationId}/live` from decoded identifiers without encoding dynamic path segments.
- Impact: a world or conversation identifier containing an encoded slash or reserved path character can be forwarded to the backend WebSocket router as a broader or different path than the fixed conversation live route intended. Because the live socket accepts state-changing commands such as seed, advance, start, pause, and resume, preserving exact route boundaries is required even when backend authz remains the final enforcement layer.
- Intended remediation: encode the world and conversation identifiers before constructing the backend live WebSocket URL, and add focused Web regression coverage proving encoded slashes remain inside identifier path segments.
- Status: Remediated in Web conversation live socket path boundary batch.
- Verification: npm run test -- lib/realtime.test.ts passed with 2 passed; npm run lint passed; npm run typecheck passed; full npm run test passed with 44 files and 140 tests; npm run build passed; npm run check:next-env passed; full npm run test:e2e was attempted and failed on the scene-view safe-media test after 15 passed and 5 skipped, then the failing scene-view test passed on focused rerun; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-033 Web conversation API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for conversation read and state-changing control helpers.
- Evidence: web/lib/worlds/client.ts builds conversation helper URLs such as `/api/worlds/${worldId}/conversations/${conversationId}/seed`, `/advance`, `/start`, `/pause`, `/resume`, `/stop`, `/participants`, `/turns`, `/speaker-preview`, `/memory/summary`, `/diagnostics/summary`, and `/narrative/*` from decoded identifiers without encoding dynamic path segments.
- Impact: a world or conversation identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional frontend/backend path or query structure instead of staying inside the identifier segment. Because this helper group includes state-changing conversation controls, preserving route boundaries is required even when backend authorization remains the final enforcement layer.
- Intended remediation: encode the scoped conversation helper world and conversation identifiers before constructing same-origin API URLs, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing helpers.
- Status: Remediated in Web conversation API client path boundary batch.
- Verification: npm run test -- lib/worlds/client.test.ts passed with 25 passed; npm run lint passed; npm run typecheck passed; full npm run test passed with 44 files and 141 tests; npm run build passed; npm run check:next-env passed; npm run test:e2e passed with 21 passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-034 Web provider integration API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for provider integration configuration, discovery, health-check, capability, and smoke-test helpers.
- Evidence: web/lib/worlds/provider-integrations.ts builds provider helper URLs such as `/api/worlds/${worldId}/providers`, `/providers/templates`, `/providers/model-discovery`, `/providers/${providerId}`, `/capabilities`, `/health-check`, `/health-checks?limit=...`, and `/smoke-test` from decoded identifiers without encoding dynamic path segments.
- Impact: a world or provider identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional frontend/backend path or query structure instead of staying inside the identifier segment. Because this helper group includes provider configuration mutation, explicit health checks, model discovery, and smoke tests, preserving route boundaries is required even when backend authorization and provider execution boundaries remain final enforcement layers.
- Intended remediation: encode the scoped provider helper world and provider identifiers before constructing same-origin API URLs, preserve `limit` as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing provider helpers.
- Status: Remediated in Web provider integration API client path boundary batch.
- Verification: npm run test -- lib/worlds/provider-integrations.test.ts passed with 5 passed; npm run lint passed; npm run typecheck passed; full npm run test passed with 44 files and 142 tests, with existing runtime-admin React act warnings; npm run build passed; npm run check:next-env passed; npm run test:e2e passed with 21 passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --changes --strict passed with 1 passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-035 Web speech admin API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for speech voice profile, agent voice binding, style mapping, transcript, TTS, and STT helpers.
- Evidence: web/lib/worlds/speech.ts builds speech helper URLs such as `/api/worlds/${worldId}/speech/voice-profiles`, `/speech/voice-profiles/${voiceProfileId}`, `/agents/${agentId}/voice-profiles`, `/voice-profiles/${bindingId}`, `/speech/style-mappings/${mappingId}`, `/speech/transcripts`, `/speech/tts`, and `/speech/stt` from decoded identifiers without encoding dynamic path segments.
- Impact: a world, agent, voice profile, binding, or style mapping identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional frontend/backend path or query structure instead of staying inside the identifier segment. Because this helper group includes voice profile mutation, agent voice binding mutation, style mapping mutation, and explicit TTS/STT actions, preserving route boundaries is required even when backend authorization and provider execution boundaries remain final enforcement layers.
- Intended remediation: encode the scoped speech helper world, agent, voice profile, binding, and style mapping identifiers before constructing same-origin API URLs, preserve filters as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing speech helpers.
- Status: Remediated in Web speech admin API client path boundary batch.
- Verification: npm run test -- lib/worlds/speech.test.ts passed with 3 passed; npm run lint passed; npm run typecheck passed; full npm run test passed with 44 files and 143 tests, with existing runtime-admin React act warnings; npm run build passed; npm run check:next-env passed; full npm run test:e2e was attempted and failed on the workspace/conversation e2e after 11 passed and 9 skipped, then the focused workspace/conversation rerun failed at a different runtime notice assertion, and a second focused rerun passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --changes --strict passed with 1 passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-036 Web visual admin API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for visual sprite set, sprite variant, scene background, resolver, and compose-scene helpers.
- Evidence: web/lib/worlds/visual.ts builds visual helper URLs such as `/api/worlds/${worldId}/visual/sprite-sets`, `/visual/sprite-sets/${spriteSetId}`, `/variants/${variantId}`, `/visual/backgrounds/${backgroundId}`, `/visual/resolve-sprite`, `/visual/resolve-background`, and `/visual/compose-scene` from decoded identifiers without encoding dynamic path segments.
- Impact: a world, sprite set, variant, or background identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional frontend/backend path or query structure instead of staying inside the identifier segment. Because this helper group includes visual binding mutation, resolver previews, and explicit compose-scene actions that interact with media/image boundaries, preserving route boundaries is required even when backend authorization and media/provider boundaries remain final enforcement layers.
- Intended remediation: encode the scoped visual helper world, sprite set, variant, and background identifiers before constructing same-origin API URLs, preserve filters as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing visual helpers.
- Status: Remediated in Web visual admin API client path boundary batch.
- Verification: npm run test -- lib/worlds/visual.test.ts passed with 4 passed; npm run lint passed; npm run typecheck passed; full npm run test passed with 44 files and 144 tests, with existing runtime-admin React act warnings; npm run build passed; npm run test:e2e passed with 21 passed; npm run check:next-env initially failed after e2e/dev regenerated next-env.d.ts to .next/dev/types/routes.d.ts, then passed after restoring the expected .next/types/routes.d.ts import; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --changes --strict passed with 1 passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-037 Web media admin API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for media asset, object, reference, job, upload, and download helpers.
- Evidence: web/lib/worlds/media.ts builds media helper URLs such as `/api/worlds/${worldId}/media/assets`, `/media/assets/${assetId}`, `/objects`, `/references`, `/media/jobs/${jobId}/cancel`, `/retry`, `/media/assets/upload`, and `/media/objects/${objectId}/download` from decoded identifiers without encoding dynamic path segments.
- Impact: a world, media asset, job, or object identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional frontend/backend path or query structure instead of staying inside the identifier segment. Because this helper group includes media upload, asset mutation, job retry/cancel, and backend download helpers, preserving route boundaries is required even when backend authorization and media storage boundaries remain final enforcement layers.
- Intended remediation: encode the scoped media helper world, asset, job, and object identifiers before constructing same-origin API URLs, preserve filters as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing media helpers.
- Status: Remediated in Web media admin API client path boundary batch.
- Verification: npm run test -- lib/worlds/media.test.ts passed with 5 passed; npm run lint passed; npm run typecheck passed; full npm run test passed with 44 files and 145 tests, with existing runtime-admin React act warnings; npm run build passed; npm run test:e2e passed with 21 passed; npm run check:next-env initially failed after e2e/dev regenerated next-env.d.ts to .next/dev/types/routes.d.ts, then passed after restoring the expected .next/types/routes.d.ts import; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --changes --strict passed with 1 passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-038 Web invocation ledger API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for model invocation ledger, prompt snapshot, tag, and redaction helpers.
- Evidence: web/lib/worlds/invocations.ts builds invocation ledger helper URLs such as `/api/worlds/${worldId}/model-invocations`, `/model-invocations/${invocationId}`, `/prompt-snapshot`, `/tags`, `/tags/${tagId}`, and `/redact` from decoded identifiers without encoding dynamic path segments.
- Impact: a world, invocation, or tag identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional frontend/backend path or query structure instead of staying inside the identifier segment. Because this helper group includes prompt snapshot retrieval, invocation tagging, tag deletion, and redaction writes over raw prompt/output evidence, preserving route boundaries is required even when backend authorization and invocation redaction boundaries remain final enforcement layers.
- Intended remediation: encode the scoped invocation helper world, invocation, and tag identifiers before constructing same-origin API URLs, preserve filters as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing invocation helpers.
- Status: Remediated in Web invocation ledger API client path boundary batch.
- Verification: npm run test -- lib/worlds/invocations.test.ts passed with 3 passed; npm run lint passed; npm run typecheck passed; full npm run test passed with 44 files and 146 tests, with existing runtime-admin React act warnings; npm run build passed; npm run test:e2e passed with 21 passed; npm run check:next-env initially failed after e2e/dev regenerated next-env.d.ts to .next/dev/types/routes.d.ts, then passed after restoring the expected .next/types/routes.d.ts import; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --changes --strict passed with 1 passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-039 Web multimodal diagnostics API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for multimodal diagnostics and eval-run helpers.
- Evidence: web/lib/worlds/diagnostics.ts builds diagnostics helper URLs such as `/api/worlds/${worldId}/diagnostics/multimodal`, `/multimodal-evals`, `/multimodal-evals/${runId}`, and `/multimodal-evals/run` from decoded identifiers without encoding dynamic path segments.
- Impact: a world or eval-run identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional frontend/backend path or query structure instead of staying inside the identifier segment. Because this helper group includes admin diagnostics, eval-run history/detail, and explicit eval execution, preserving route boundaries is required even when backend authorization and diagnostics redaction boundaries remain final enforcement layers.
- Intended remediation: encode the scoped diagnostics helper world and eval-run identifiers before constructing same-origin API URLs, preserve filters as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing diagnostics helpers.
- Status: Remediated in Web multimodal diagnostics API client path boundary batch.
- Verification: npm run test -- lib/worlds/diagnostics.test.ts passed with 3 passed; npm run lint passed; npm run typecheck passed; full npm run test passed with 44 files and 147 tests, with existing runtime-admin React act warnings; npm run build passed; npm run test:e2e passed with 21 passed; npm run check:next-env initially failed after e2e/dev regenerated next-env.d.ts to .next/dev/types/routes.d.ts, then passed after restoring the expected .next/types/routes.d.ts import; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --changes --strict passed with 1 passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-040 Web server admin loader backend path segment injection

- Severity: High
- Affected boundary: server-rendered Web admin data loaders that fetch world-scoped provider, media, visual, speech, invocation, and multimodal diagnostics records from backend API routes.
- Evidence: web/lib/worlds/server.ts constructs backend fetch paths such as `/worlds/${worldId}/providers/${provider.id}/capabilities`, `/media/assets/${asset.id}/objects`, `/visual/sprite-sets/${spriteSet.id}/variants`, `/agents/${agent.id}/voice-profiles`, and `/model-invocations/${invocation.id}/tags` from decoded route and backend record identifiers without encoding dynamic path segments; several selected worldline query filters in the same loader group are also appended without query encoding.
- Impact: a world or nested record identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional backend path or query structure during SSR data loading instead of staying inside the identifier segment. Because these loaders hydrate admin-facing provider, media, prompt/invocation, speech, visual, and diagnostics surfaces, route-boundary preservation is required even though backend authorization and DTO redaction remain final enforcement layers.
- Intended remediation: encode scoped server-loader world and nested record identifiers before constructing backend API URLs, encode loader query filters with URLSearchParams/encodeURIComponent, and add focused Web server-loader regression coverage proving reserved characters remain encoded inside representative admin backend paths.
- Status: Remediated in Web server admin loader backend path boundary batch.
- Verification: npm run test -- lib/worlds/server.test.ts passed with 1 passed; npm run lint passed; npm run typecheck passed; full npm run test passed with 45 files and 148 tests, with existing runtime-admin React act warnings; npm run build passed; npm run test:e2e was attempted twice and hit existing flake points, first at publication blocker after 12 passed and 8 skipped, then at scene view after 15 passed and 5 skipped; focused reruns for publication blocker and scene view passed, and a focused group covering the skipped player/privacy/worldline/release-gate/member tests passed with 5 passed; npm run check:next-env passed after restoring the expected .next/types/routes.d.ts import regenerated by e2e/dev; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --changes --strict passed with 1 passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.

### F-041 Web core world API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for core world management, worldline, GM, resolution rule, player actor, and player choice helpers in `web/lib/worlds/client.ts`.
- Evidence: `web/lib/worlds/client.ts` constructs same-origin URLs such as `/api/worlds/${worldId}`, `/worldlines/${baseWorldlineId}/compare/${compareWorldlineId}`, `/gm/agendas/${agendaId}`, `/gm/proposals/${proposalId}/review`, and `/resolution-rules/${ruleId}/dry-run` from decoded identifiers without encoding dynamic path segments.
- Impact: a world or nested route identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional same-origin frontend/backend path or query structure instead of staying inside the identifier segment. These helpers include world administration, explicit GM proposal review/drafting, resolution rule dry-runs, and player choice writes, so route-boundary preservation is required even though backend authorization remains final enforcement.
- Intended remediation: encode the scoped core world client helper world and nested identifiers before constructing same-origin API URLs, preserve existing filters as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing helpers.
- Status: Remediated in Web core world API client path boundary batch.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 26 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 149 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.

### F-042 Web clock, replay, and scene graph API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for world clock, replay, snapshot, event audit, scene, and location-edge helpers in `web/lib/worlds/client.ts`.
- Evidence: `web/lib/worlds/client.ts` constructs same-origin URLs such as `/api/worlds/${worldId}/clock`, `/replay/state`, `/snapshots/latest`, `/events`, `/scenes/${sceneId}`, and `/location-edges/${edgeId}` from decoded identifiers without encoding dynamic path segments.
- Impact: a world, scene, or location-edge identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional same-origin frontend/backend path or query structure instead of staying inside the identifier segment. These helpers include clock control, replay/snapshot reads and writes, event audit filters, and scene graph mutation, so route-boundary preservation is required even though backend authorization remains final enforcement.
- Intended remediation: encode the scoped clock/replay/scene helper world and nested identifiers before constructing same-origin API URLs, preserve existing filters as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing helpers.
- Status: Remediated in Web clock/replay/scene API client path boundary batch.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 27 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 150 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.

### F-043 Web organization, agent, calendar, and schedule API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for organization, organization membership, faction track, agent relationship, agent presence, agent calendar, schedule rule, and calendar conflict helpers in `web/lib/worlds/client.ts`.
- Evidence: `web/lib/worlds/client.ts` constructs same-origin URLs such as `/api/worlds/${worldId}/organizations/${organizationId}`, `/memberships/${membershipId}`, `/faction-tracks/${trackId}`, `/agents/${agentId}/relationships/${relationshipId}`, `/presence`, `/calendar/${entryId}`, `/schedule-rules/${ruleId}`, and `/calendar/conflicts` from decoded identifiers without encoding dynamic path segments.
- Impact: a world or nested route identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional same-origin frontend/backend path or query structure instead of staying inside the identifier segment. These helpers include organization administration, faction progress, agent relationship and presence state, calendar entry mutation, schedule rule mutation, and conflict reports, so route-boundary preservation is required even though backend authorization remains final enforcement.
- Intended remediation: encode the scoped organization/agent/calendar/schedule helper world and nested identifiers before constructing same-origin API URLs, preserve existing filters as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing helpers.
- Status: Remediated in Web organization/agent/calendar/schedule API client path boundary batch.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 28 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 151 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.

### F-044 Web daily-life and offscreen event API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for daily-life preview/generation/candidate and offscreen event create/list/resolve helpers in `web/lib/worlds/client.ts`.
- Evidence: `web/lib/worlds/client.ts` constructs same-origin URLs such as `/api/worlds/${worldId}/daily-life/preview`, `/daily-life/generate`, `/daily-life/candidates`, `/offscreen-events`, and `/offscreen-events/resolve` from decoded identifiers without encoding dynamic path segments.
- Impact: a world identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional same-origin frontend/backend path or query structure instead of staying inside the identifier segment. These helpers include worldline-scoped daily-life previews, candidate generation, offscreen event creation, and offscreen event resolution, so route-boundary preservation is required even though backend authorization remains final enforcement.
- Intended remediation: encode the scoped daily-life/offscreen helper world identifier before constructing same-origin API URLs, preserve existing filters as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing helpers.
- Status: Remediated in Web daily-life/offscreen API client path boundary batch.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 29 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 152 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.


### F-045 Web story, route, ending, authoring, release, and beta checklist API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for story hook, plot thread, route affinity, route milestone, ending candidate, long-run eval, authoring template, release profile, and beta checklist helpers in `web/lib/worlds/client.ts`.
- Evidence: `web/lib/worlds/client.ts` constructs same-origin URLs such as `/api/worlds/${worldId}/story-hooks`, `/plot-threads`, `/route-affinities`, `/route-milestones`, `/ending-candidates/${endingId}/dry-run`, `/long-run-evals`, `/authoring-templates/${templateId}/preview`, `/release-profile`, and `/beta-checklists/${runId}/items` from decoded identifiers without encoding dynamic path segments.
- Impact: a world or nested route identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional same-origin frontend/backend path or query structure instead of staying inside the identifier segment. These helpers include story/route planning, ending dry-runs, long-run eval creation, authoring template preview/apply, release profile mutation, and beta checklist reads/writes, so route-boundary preservation is required even though backend authorization remains final enforcement.
- Intended remediation: encode the scoped living-world story/route/ending/authoring/release/beta helper world and nested identifiers before constructing same-origin API URLs, preserve existing filters as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing helpers.
- Status: Remediated in Web story/route/ending/authoring/release/beta API client path boundary batch.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 30 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 153 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.

### F-046 Web event trigger, scene beat, episode, group, relationship, conflict, rumor, and dashboard API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for event trigger condition, scene beat, daily episode, group interaction, relationship suggestion, organization conflict, rumor, rumor propagation, and living-world dashboard helpers in `web/lib/worlds/client.ts`.
- Evidence: `web/lib/worlds/client.ts` constructs same-origin URLs such as `/api/worlds/${worldId}/event-trigger-conditions`, `/event-trigger-conditions/${conditionId}/dry-run`, `/scene-beats`, `/daily-episodes`, `/group-interactions/${contextId}/execute`, `/relationship-suggestions/${suggestionId}`, `/organization-conflicts/${conflictId}/resolve`, `/rumor-propagations/${propagationId}/deliver`, and `/living-world-dashboard` from decoded identifiers without encoding dynamic path segments.
- Impact: a world or nested route identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional same-origin frontend/backend path or query structure instead of staying inside the identifier segment. These helpers include trigger condition mutation and dry-runs, scene/daily episode creation, group interaction execution, relationship suggestion acceptance, organization conflict resolution, rumor delivery, and dashboard reads, so route-boundary preservation is required even though backend authorization remains final enforcement.
- Intended remediation: encode the scoped helper world and nested identifiers before constructing same-origin API URLs, preserve existing filters as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing helpers.
- Status: Remediated in Web event/episode/group/relationship/conflict/rumor/dashboard API client path boundary batch.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 31 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 154 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.


### F-047 Web knowledge, secret, emotion, repair, player, privacy, and review API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for knowledge fact, secret, emotional state, relationship repair, player journal, notification, intervention, player privacy, GM style review, and narrative continuity review helpers in `web/lib/worlds/client.ts`.
- Evidence: `web/lib/worlds/client.ts` constructs same-origin URLs such as `/api/worlds/${worldId}/knowledge`, `/secrets/${secretId}/reveal`, `/emotional-states`, `/relationship-repairs/${repairId}/apply`, `/player-journal`, `/notifications`, `/interventions`, `/player/privacy/export`, `/gm-style-reviews`, and `/narrative-continuity-reviews` from decoded identifiers without encoding dynamic path segments.
- Impact: a world or nested route identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional same-origin frontend/backend path or query structure instead of staying inside the identifier segment. These helpers include secret reveal, relationship repair application, player privacy export/delete requests, notifications/interventions, and review creation, so route-boundary preservation is required even though backend authorization remains final enforcement.
- Intended remediation: encode the scoped helper world and nested identifiers before constructing same-origin API URLs, preserve existing filters as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing helpers.
- Status: Remediated in Web knowledge/secret/player/privacy/review API client path boundary batch.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 32 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 155 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import.


### F-048 Web agent memory, persona, run, observation, narrative artifact, and agent mutation API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for agent memory, memory profile snapshot, agent runs, agent persona, agent observations, manual agent run, narrative artifact, publish/unpublish, agent update, and agent deactivate helpers in `web/lib/worlds/client.ts`.
- Evidence: `web/lib/worlds/client.ts` constructs same-origin URLs such as `/api/worlds/${worldId}/agents/${agentId}/memory`, `/memory/profile-snapshot/refresh`, `/runs/${runId}`, `/persona/validate`, `/observations/refresh`, `/run`, `/narrative-artifacts/${artifactId}/publish`, `/narrative-artifacts/${artifactId}/unpublish`, and `/agents/${agentId}` from decoded identifiers without encoding dynamic path segments.
- Impact: a world, agent, run, or narrative artifact identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional same-origin frontend/backend path or query structure instead of staying inside the identifier segment. These helpers include memory search/forget, persona mutation/validation, observation refresh, manual agent run, narrative artifact publication, and agent update/deactivation, so route-boundary preservation is required even though backend authorization remains final enforcement.
- Intended remediation: encode the scoped helper world and nested identifiers before constructing same-origin API URLs, preserve existing filters as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing helpers.
- Status: Remediated in Web agent memory/run/persona/narrative API client path boundary batch.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 33 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 156 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import.


### F-049 Web membership, member candidate, and diagnostics API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for membership list/upsert/delete, member candidate search, and world diagnostics helpers in `web/lib/worlds/client.ts`.
- Evidence: `web/lib/worlds/client.ts` constructs same-origin URLs such as `/api/worlds/${worldId}/memberships`, `/memberships/${userId}`, `/member-candidates?query=...`, and `/diagnostics` from decoded identifiers without encoding dynamic path segments.
- Impact: a world or user identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional same-origin frontend/backend path or query structure instead of staying inside the identifier segment. These helpers include role membership mutation, member candidate search, and world diagnostics reads, so route-boundary preservation is required even though backend authorization remains final enforcement.
- Intended remediation: encode the scoped helper world and nested user identifiers before constructing same-origin API URLs, preserve existing filters as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing helpers.
- Status: Remediated in Web membership/candidate/diagnostics API client path boundary batch.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 34 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 157 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import.

### F-050 Web admin preset, memory backend, memory write job, and provider profile API client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction for platform admin agent preset, memory backend profile, memory write job retry, and provider profile helpers in `web/lib/worlds/client.ts`.
- Evidence: `web/lib/worlds/client.ts` constructs same-origin URLs such as `/api/agent-presets/${presetId}`, `/api/agent-presets/${presetId}/update-preview`, `/api/memory-backend-profiles/${profileId}`, `/logs`, `/jobs`, `/eval-smoke`, `/api/memory-write-jobs/${jobId}/retry`, `/api/provider-profiles/${profileId}`, and `/test-call` from decoded identifiers without encoding dynamic path segments.
- Impact: a preset, memory profile, memory job, or provider profile identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional same-origin frontend/backend path or query structure instead of staying inside the identifier segment. These helpers include platform-admin preset mutation, provider profile mutation/test calls, memory backend profile health/log/job/eval operations, and memory job retry, so route-boundary preservation is required even though backend authorization remains final enforcement.
- Intended remediation: encode the scoped preset/profile/job identifiers before constructing same-origin API URLs, preserve existing filters as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative read and state-changing helpers.
- Status: Remediated in Web admin preset/memory/provider API client path boundary batch.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 35 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 158 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.

### F-051 Web private beta and beta feedback client path segment injection

- Severity: High
- Affected boundary: browser-side Web same-origin API URL construction and private-beta player navigation for private beta onboarding and beta feedback helpers.
- Evidence: `web/lib/private-beta/client.ts` constructs `/api/worlds/${worldId}/private-beta/onboarding/player-profile` from a decoded world identifier; `web/lib/beta-feedback/client.ts` constructs `/api/worlds/${worldId}/beta-feedback/reports`, report list filters, and `/reports/${reportId}/triage` from decoded world and report identifiers; `web/features/private-beta/private-beta-onboarding.tsx` links to `/worlds/${item.world_id}/player` from a decoded world identifier.
- Impact: a world or beta feedback report identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional same-origin frontend/backend path or query structure instead of staying inside the identifier segment. These helpers include private beta player profile bootstrap, beta feedback report creation/listing/triage, and private beta player-surface navigation, so route-boundary preservation is required even though backend authorization remains final enforcement.
- Intended remediation: encode the scoped private beta and beta feedback world/report identifiers before constructing same-origin API URLs or local player-surface links, preserve existing feedback filters as query data, and add focused Web regression coverage proving reserved characters remain encoded inside identifier path segments for representative private beta and beta feedback helpers.
- Status: Remediated in Web private beta/beta feedback client path boundary batch.
- Verification: `npm run test -- lib/private-beta/client.test.ts lib/beta-feedback/client.test.ts features/private-beta/private-beta-onboarding.test.tsx` passed with 3 files and 6 tests; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 47 files and 162 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.


### F-052 Web server workspace loader backend path segment injection

- Severity: High
- Affected boundary: server-rendered Web loader backend API URL construction in `web/lib/worlds/server.ts` for world workspace, agent detail, conversation, player, reader, worldline, and platform memory backend admin data.
- Evidence: `web/lib/worlds/server.ts` constructs backend URLs such as `/worlds/${worldId}/...`, `/worlds/${worldId}/agents/${agentId}/...`, `/worlds/${worldId}/conversations/${conversationId}/...`, `/worlds/${worldId}/narrative-artifacts/${artifactId}`, `/worlds/${worldId}/worldlines/${baseId}/compare/${compareId}`, and `/memory-backend-profiles/${profile.id}/...` from decoded route parameters or backend record identifiers without encoding dynamic path segments.
- Impact: a world, agent, conversation, artifact, worldline, turn, organization, beta checklist, or memory backend profile identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional backend path or query structure instead of staying inside the identifier segment during server-side rendering. These loaders run with the user session cookie and fetch admin/player/member surfaces, so route-boundary preservation is required even though backend authorization remains final enforcement.
- Intended remediation: encode all dynamic world, nested route, and memory backend profile identifiers before constructing backend API URLs in server loaders, preserve filters as query data, and add focused server-loader regression coverage proving reserved characters remain encoded inside backend path segments for representative workspace, conversation/player/reader, worldline, and memory backend paths.
- Status: Remediated in Web server workspace loader backend path boundary batch.
- Verification: `npm run test -- lib/worlds/server.test.ts` passed with 2 tests; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 47 files and 163 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.


### F-053 Web UI local app route link path segment injection

- Severity: High
- Affected boundary: browser-side Web local app route construction for workspace navigation, world index navigation, agent builder links, conversation transcript links, player resume/privacy links, overview shortcut links, reader playback/scene links, and narrative reader links.
- Evidence: Web components construct local route hrefs such as `/worlds/${worldId}`, `/worlds/${worldId}/agents/${agent.id}`, `/worlds/${worldId}/conversations/${conversation.id}`, `/worlds/${worldId}/reader/${artifact.id}`, and `/worlds/${worldId}/reader/conversations/${conversationId}/playback` from decoded route or backend identifiers without encoding every dynamic path segment.
- Impact: a world, agent, conversation, narrative artifact, or resume conversation identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional local app route path, query, or fragment structure instead of staying inside the identifier segment. These links cross admin, reader, and player surfaces, so route-boundary preservation is required even though server-side loaders and backend authorization remain final enforcement.
- Intended remediation: encode dynamic world and nested app route identifiers before constructing Next.js `Link` hrefs or browser navigation paths, preserve existing safe media download helpers, and add focused Web component regression coverage proving reserved characters remain encoded inside local route path segments.
- Status: Remediated in Web UI local app route link boundary batch.
- Verification: `npm run test -- features/agents/agent-list.test.tsx features/conversations/conversation-list.test.tsx features/workspace/workspace-shell.test.tsx features/worlds/worlds-index.test.tsx features/worlds/player-interactions.test.tsx features/worlds/conversation-playback.test.tsx features/worlds/conversation-scene-view.test.tsx features/worlds/narrative-reader.test.tsx features/worlds/world-overview.test.tsx` passed with 9 files and 25 tests; a focused source scan for raw local `/worlds/` route interpolation patterns in `web/features`, `web/components`, and `web/app` returned no matches; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 49 files and 169 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.


### F-054 Web non-auth proxy Set-Cookie relay boundary

- Severity: High
- Affected boundary: Web same-origin non-auth proxy response handling in `web/lib/api-proxy.ts`, `web/lib/worlds/proxy.ts`, `web/lib/runtime/proxy.ts`, and `web/lib/private-beta/proxy.ts` through shared `buildProxyResponse()` behavior.
- Evidence: `buildProxyResponse()` in `web/lib/auth/proxy.ts` unconditionally appends backend `Set-Cookie` headers, and the non-auth Web proxy helpers reuse it for worlds, runtime/admin, plugins/presets/world-composition, and private beta routes. A non-auth backend response that includes `Set-Cookie` would therefore mutate browser cookies through same-origin Web API routes.
- Impact: non-auth API surfaces that should only relay data/status can overwrite or inject browser cookies if the backend route accidentally emits `Set-Cookie`; this widens session/CSRF fixation and cookie-scope mutation risk outside the dedicated auth boundary.
- Intended remediation: make `Set-Cookie` relay opt-in for auth proxy calls only, keep non-auth proxies on the existing status/body/content-type/cache-control contract without cookie mutation headers, and add focused proxy regression coverage proving auth flows still relay cookies while world/runtime/private-beta/generic API proxies strip backend `Set-Cookie`.
- Status: Remediated in Web non-auth proxy response cookie boundary batch.
- Verification: `npm run test -- lib/auth/proxy.test.ts lib/worlds/proxy.test.ts lib/runtime/proxy.test.ts lib/private-beta/proxy.test.ts lib/api-proxy.test.ts` passed with 5 files and 12 tests; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 51 files and 175 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.


### F-055 Auth login CSRF session fixation boundary

- Severity: High
- Affected boundary: Backend `/auth/login` session-cookie creation and Web auth client login request construction.
- Evidence: `backend/services/api/src/noveland/services/api/auth.py` creates a new authenticated session and sets `noveland_session`/`noveland_csrf` cookies in `login()` without calling `require_csrf(request)`. `web/features/auth/login-form.tsx` calls `requestCsrf()` before login, but `web/lib/auth/client.ts` sends the login POST without `X-CSRF-Token`, so the backend cannot enforce double-submit CSRF for session creation.
- Impact: a cross-site request can attempt to create or replace the browser's authenticated session cookie through the login endpoint without proving same-origin access to the readable CSRF cookie. Even when credentials are not exposed, this widens login CSRF/session-fixation risk outside the intended auth mutation boundary.
- Intended remediation: require double-submit CSRF on backend login before creating the session, make the Web auth client obtain and send the CSRF token with login requests, preserve logout CSRF behavior, and add backend/Web regression coverage for missing/wrong login CSRF and successful CSRF-protected login.
- Status: Remediated in auth login CSRF session fixation boundary batch.
- Verification: `cd backend && uv run pytest tests/test_api_auth.py` passed with 7 tests; `cd backend && uv run pytest tests/test_api_auth_integration.py` skipped 3 integration tests because `NOVELAND_TEST_DATABASE_URL` was not set; `cd backend && uv run ruff check .` passed; `cd backend && uv run mypy .` passed; `cd backend && uv run pytest` passed with 561 passed and 8 skipped; `cd web && npm run test -- lib/auth/client.test.ts features/auth/login-form.test.tsx` passed with 2 files and 9 tests; `cd web && npm run typecheck` passed; `cd web && npm run lint` passed; full `cd web && npm run test` passed with 51 files and 177 tests, with existing runtime-admin React act warnings; `cd web && npm run build` passed; `cd web && npm run test:e2e` passed with 21 passed; `cd web && npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.

### F-056 Memory backend profile secret-reference persistence boundary

- Severity: High
- Affected boundary: Platform-admin memory backend profile create/update APIs, memory backend profile persistence, and Web admin memory backend profile display.
- Evidence: `backend/packages/memory/src/noveland/memory/service.py` persists `vector_store_config`, `llm_config`, `embedder_config`, `reranker_config`, and `secret_refs` directly from `MemoryBackendProfileCreate`/`MemoryBackendProfileUpdate`. `backend/services/api/src/noveland/services/api/runtime.py` returns those fields in `MemoryBackendProfileResponse`, and `web/features/admin/memory-backend-admin.tsx` renders `secret_refs` back into editable form state. The mem0 backend later treats `secret_refs` values as lookup keys into `NOVELAND_MEMORY_BACKEND_SECRETS_JSON`, but no service/API validation prevents direct `api_key` config or obvious raw secret values such as `sk-...` from being persisted and returned.
- Impact: a platform admin or compromised admin browser can accidentally persist raw memory-provider secrets in database-backed memory profile config. Those values are then returned by profile list/update APIs and rendered in Web admin, widening secret exposure beyond the intended runtime-only `NOVELAND_MEMORY_BACKEND_SECRETS_JSON` resolution boundary.
- Intended remediation: reject sensitive config keys and raw-secret-looking values in memory backend profile config, validate `secret_refs` as non-empty reference names rather than raw secrets, preserve safe reference lookup behavior for runtime backends, and add service/API regression coverage proving raw secret material is rejected without echoing it.
- Status: Remediated in memory backend profile secret-reference boundary batch.
- Verification: `cd backend && uv run pytest tests/test_memory_backend.py::test_memory_backend_profile_rejects_raw_secret_material tests/test_api_runtime.py::test_memory_backend_profile_api_rejects_raw_secret_material` passed with 2 tests; `cd backend && uv run pytest tests/test_memory_backend.py tests/test_api_runtime.py` passed with 26 tests; `cd backend && uv run ruff check .` passed; `cd backend && uv run mypy .` passed; `cd backend && uv run pytest` passed with 563 passed and 8 skipped; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.


### F-057 Web reader media download URL route-boundary overacceptance

- Severity: Medium
- Affected boundary: browser-side reader playback and scene media rendering from reader media descriptors.
- Evidence: `web/lib/worlds/media.ts` accepts any descriptor `download_url` beginning with `/api/worlds/` or `/worlds/` and returns it for `<audio src>` or CSS `url(...)` rendering in `web/features/worlds/conversation-playback.tsx` and `web/features/worlds/conversation-scene-view.tsx`; the backend reader media service generates only `/worlds/{world_uuid}/reader/media/objects/{object_uuid}/download` paths.
- Impact: a malformed or compromised descriptor can cause the reader UI to fetch an unintended same-origin world route instead of the scoped reader-media object download route, widening the low-privilege media rendering boundary even though backend authorization remains final enforcement.
- Intended remediation: constrain Web reader media URL conversion to exact UUID reader-media object download paths, reject query strings, fragments, extra path segments, alternate world routes, and non-backend schemes, and add focused Web regression coverage for accepted and rejected descriptor URLs.
- Status: Remediated in Web reader media route-boundary batch.
- Verification: `cd web && npm run test -- lib/worlds/media.test.ts features/worlds/conversation-playback.test.tsx features/worlds/conversation-scene-view.test.tsx` passed with 3 files and 13 tests; `cd web && npm run lint` passed; `cd web && npm run typecheck` passed; full `cd web && npm run test` passed with 51 files and 177 tests, with existing runtime-admin React act warnings; `cd web && npm run build` passed; `cd web && npm run test:e2e` passed with 21 tests; `cd web && npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.


### F-058 Media byte response safety header loss through Web proxy

- Severity: Medium
- Affected boundary: backend media byte download responses and Web same-origin non-auth proxy response shaping.
- Evidence: `backend/services/api/src/noveland/services/api/reader_media.py` sets `X-Content-Type-Options: nosniff` on reader media downloads, but `web/lib/auth/proxy.ts` `buildProxyResponse()` only forwards `content-type`, cache policy, and optional auth cookies, so `/api/worlds/.../reader/media/objects/.../download` loses the backend nosniff header. `backend/services/api/src/noveland/services/api/media.py` admin media downloads return raw media bytes without setting nosniff at the backend boundary.
- Impact: media byte responses rendered or downloaded through the Web surface lose an explicit browser sniffing defense, and admin media downloads lack that defense entirely, widening the impact of incorrect or hostile media content types even though backend authorization and content generation remain separate controls.
- Intended remediation: add nosniff to backend admin media byte downloads, preserve a minimal allowlist of safe response headers through Web non-auth proxies, continue stripping `Set-Cookie`, and add focused backend/Web proxy regression coverage.
- Status: Remediated in media response safety header batch.
- Verification: `cd backend && uv run pytest tests/test_api_media.py::test_media_api_upload_download_objects_and_restricted_visibility` passed with 1 test; `cd web && npm run test -- lib/worlds/proxy.test.ts` passed with 1 file and 4 tests; `cd backend && uv run pytest tests/test_api_media.py tests/test_api_reader_media.py` passed with 14 tests; `cd web && npm run test -- lib/auth/proxy.test.ts lib/worlds/proxy.test.ts lib/runtime/proxy.test.ts lib/private-beta/proxy.test.ts lib/api-proxy.test.ts` passed with 5 files and 13 tests; `cd backend && uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py` passed; `cd backend && uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py` passed; `cd backend && uv run pytest` passed with 563 tests and 8 skipped; `cd web && npm run lint` passed; `cd web && npm run typecheck` passed; full `cd web && npm run test` passed with 51 files and 178 tests, with existing runtime-admin React act warnings; `cd web && npm run build` passed; `cd web && npm run test:e2e` passed with 21 tests; `cd web && npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import. `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.


### F-059 Web proxy request body byte preservation gap

- Severity: Medium
- Affected boundary: Web same-origin proxy forwarding for media uploads and other non-GET backend mutations.
- Evidence: `web/lib/worlds/media.ts` sends media uploads as `FormData` to `/api/worlds/{world_id}/media/assets/upload`, but `web/lib/worlds/proxy.ts` reads every non-GET request body with `request.text()` before forwarding it. The same text-decoding pattern exists in auth, generic API, runtime, and private-beta proxy helpers.
- Impact: multipart or binary request bodies can be decoded as UTF-8 text and re-encoded before reaching the backend, corrupting uploaded media bytes or package/import payloads and weakening byte-level integrity expectations for proxied uploads.
- Intended remediation: forward non-GET proxy request bodies as raw `ArrayBuffer` bytes, keep empty bodies absent, preserve existing headers/CSRF/cookie behavior, and add focused proxy regression coverage proving binary bytes survive forwarding.
- Status: Remediated in Web proxy request body preservation batch.
- Verification: `cd web && npm run test -- lib/worlds/proxy.test.ts lib/auth/proxy.test.ts lib/runtime/proxy.test.ts lib/private-beta/proxy.test.ts lib/api-proxy.test.ts` passed with 5 files and 14 tests; `cd web && npm run lint` passed; `cd web && npm run typecheck` passed; full `cd web && npm run test` passed with 51 files and 179 tests, with existing runtime-admin React act warnings; `cd web && npm run build` passed; `cd web && npm run test:e2e` passed with 21 tests; `cd web && npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import. `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.


### F-060 Web EventSource subscription path segment injection

- Severity: Medium
- Affected boundary: browser-side Web same-origin event-stream URL construction for world and conversation stream subscriptions.
- Evidence: `web/features/conversations/conversation-detail.tsx`, `web/features/worlds/world-overview.tsx`, `web/features/worlds/narrative-workspace.tsx`, and `web/features/worlds/narrative-reader.tsx` construct EventSource paths such as `/api/worlds/${worldId}/stream` and `/api/worlds/${worldId}/conversations/${conversationId}/stream` from decoded identifiers without encoding dynamic path segments before the browser requests the Next API route.
- Impact: a world or conversation identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional frontend route path, query, or fragment structure before the request reaches the route handler, breaking stream delivery and widening route-boundary assumptions for realtime reader/member/admin surfaces.
- Intended remediation: encode world and conversation identifiers before constructing same-origin EventSource paths and add focused component coverage proving reserved characters remain inside encoded route segments.
- Status: Remediated in Web EventSource route-boundary batch.
- Verification: `cd web && npm run test -- lib/realtime.test.ts features/conversations/conversation-detail.test.tsx features/worlds/world-overview.test.tsx features/worlds/narrative-workspace.test.tsx features/worlds/narrative-reader.test.tsx` passed with 5 files and 18 tests; `cd web && npm run lint` passed; `cd web && npm run typecheck` passed; full `cd web && npm run test` passed with 51 files and 184 tests, with existing RuntimeAdmin React act warnings; `cd web && npm run build` passed; `cd web && npm run test:e2e -- --grep publication blockers` passed after one initial full-suite transient miss on that test; rerun full `cd web && npm run test:e2e` passed with 21 tests; `cd web && npm run check:next-env` passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs.


### F-061 Web beta feedback server loader backend path segment injection

- Severity: High
- Affected boundary: server-rendered Web beta feedback loader backend API URL construction in `web/lib/beta-feedback/server.ts`.
- Evidence: `getBetaFeedbackData()` constructs backend URLs such as `/worlds/${worldId}/worldlines`, `/worlds/${worldId}/beta-feedback/reports`, and `/worlds/${worldId}/memberships` from the decoded Next route parameter without encoding the dynamic world path segment.
- Impact: a world identifier containing an encoded slash, query delimiter, or fragment delimiter can become additional backend path or query structure during server-side rendering while forwarding the user session cookie, breaking route-boundary preservation for the private beta feedback surface even though backend authorization remains final enforcement.
- Intended remediation: encode the world identifier before constructing beta feedback server-loader backend paths and add focused server-loader regression coverage proving reserved characters remain inside the encoded world path segment.
- Status: Remediated in Web beta feedback server-loader route-boundary batch.
- Verification: `cd web && npm run test -- lib/beta-feedback/server.test.ts lib/beta-feedback/client.test.ts features/private-beta/beta-feedback-panel.test.tsx` passed with 3 files and 6 tests; `cd web && npm run lint` passed; `cd web && npm run typecheck` passed; full `cd web && npm run test` passed with 52 files and 185 tests, with existing RuntimeAdmin React act warnings; `cd web && npm run build` passed; `cd web && npm run test:e2e` passed with 21 tests; `cd web && npm run check:next-env` passed after restoring the expected `.next/types/routes.d.ts` import.


### F-062 Backend reader media object download missing worldline scope

- Severity: High
- Affected boundary: backend reader media object byte delivery, reader media descriptor download URLs, and Web playback/scene reader media URL validation.
- Evidence: `ReaderMediaDeliveryService._reader_objects()` generated `/worlds/{world_id}/reader/media/objects/{object_id}/download` without embedding the object's `worldline_id`, and `download_reader_media_object()` accepted that route with `worldline_id=None`, causing `read_object()` to validate only `world_id` before reading storage bytes. Existing tests only covered wrong explicit `worldline_id`, not the unscoped default route.
- Impact: an authenticated world member who obtains or guesses a reader-visible media object UUID from another fork in the same world can download that object's bytes through the reader media route without proving the active worldline scope, weakening fork isolation for reader/player playback media.
- Intended remediation: generate reader media object download URLs with UUID worldline path scope, keep query strings rejected in Web rendering, reject unscoped legacy reader-media object downloads before storage reads, and add backend/Web regressions for scoped success and unscoped/cross-worldline rejection.
- Status: Remediated in reader media worldline-scoped download batch.
- Verification: `cd backend && uv run pytest tests/test_api_moderation.py::test_applied_moderation_takedown_hides_reader_media_without_admin_route_change tests/test_api_reader_media.py` passed with 6 tests; `cd backend && uv run ruff check packages/reader_delivery/src/noveland/reader_delivery/service.py services/api/src/noveland/services/api/reader_media.py tests/test_api_reader_media.py tests/test_api_moderation.py` passed; `cd backend && uv run mypy packages/reader_delivery/src/noveland/reader_delivery/service.py services/api/src/noveland/services/api/reader_media.py tests/test_api_reader_media.py tests/test_api_moderation.py` passed; full `cd backend && uv run pytest` passed with 563 passed and 8 skipped after an initial expected failure exposed the moderation reader-media test using the old unscoped route; `cd web && npm run test -- lib/worlds/media.test.ts features/worlds/conversation-playback.test.tsx features/worlds/conversation-scene-view.test.tsx` passed with 3 files and 13 tests; `cd web && npm run lint` passed; `cd web && npm run typecheck` passed; full `cd web && npm run test` passed with 52 files and 185 tests, with existing RuntimeAdmin React act warnings; `cd web && npm run build` passed; `cd web && npm run test:e2e -- --grep "reader playback|reader scene"` passed with 2 tests; full `cd web && npm run test:e2e` passed with 21 tests; `cd web && npm run check:next-env` passed after restoring the expected `.next/types/routes.d.ts` import regenerated by e2e/dev; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 change; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.

### F-063 Backend world-level voice profiles can reference fork-scoped audio assets

- Severity: High
- Affected boundary: speech voice profile reference-asset validation and worldline isolation.
- Evidence: `VoiceProfileService._validate_reference_asset()` accepted a `reference_asset_id` whenever the audio asset belonged to the same world, and only checked `asset.worldline_id` when the voice profile also had a non-null `worldline_id`. Media assets are worldline-scoped, while world-level voice profiles and bindings can be listed or resolved as defaults across worldlines.
- Impact: a world-level voice profile could promote fork-specific source audio into a reusable world-level voice reference, weakening fork isolation for voice clone/reference material and leaking a worldline-scoped media asset reference into other forks' speech defaults.
- Intended remediation: keep world-level provider/default voice profiles allowed, but reject `reference_asset_id` on world-level profiles because no world-level media asset exists; continue requiring exact same-worldline audio assets for scoped voice profiles.
- Status: Remediated in speech voice profile reference-asset boundary batch.
- Verification: `cd backend && uv run pytest tests/test_voice_profiles.py` passed with 4 tests; `cd backend && uv run pytest tests/test_speech_service.py tests/test_api_speech.py tests/test_voice_profiles.py` passed with 11 tests; `cd backend && uv run ruff check packages/speech/src/noveland/speech/voice_profiles.py tests/test_voice_profiles.py` passed; `cd backend && uv run mypy packages/speech/src/noveland/speech/voice_profiles.py tests/test_voice_profiles.py` passed; full `cd backend && uv run pytest` passed with 564 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.


### F-064 Beta feedback reporter reads expose admin triage evidence refs

- Severity: High
- Affected boundary: member-readable beta feedback report list/detail responses and admin triage evidence.
- Evidence: `BetaFeedbackService.list_reports()` and `get_report()` scoped non-admin callers to their own reports, but both returned `_read(report)` with full `evidence_refs_json`, `repair_proposal_refs_json`, `triage_note`, `triaged_by_actor_ref`, `moderation_report_id`, and report metadata. Admin triage can replace evidence refs with media job or invocation refs and link repair proposals, causing those admin-only references and actor refs to flow back to the reporter on later reads.
- Impact: a beta tester could read admin-only triage evidence identifiers, repair proposal refs, moderation refs, admin actor refs, or metadata from their own report after operator triage, weakening the intended separation between reporter-private feedback UX and admin repair/moderation evidence.
- Intended remediation: make beta feedback read shaping role-aware; preserve full triage evidence for admin routes while reporter/member reads keep safe status and severity, filter evidence refs to reporter-safe kinds, and omit repair/moderation/admin actor/metadata fields.
- Status: Remediated in beta feedback reporter triage evidence redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_beta_feedback.py` passed with 4 tests; `cd backend && uv run pytest tests/test_api_moderation.py tests/test_api_authoring.py` passed with 19 tests; `cd backend && uv run ruff check packages/beta_feedback/src/noveland/beta_feedback/service.py tests/test_api_beta_feedback.py` passed; `cd backend && uv run mypy packages/beta_feedback/src/noveland/beta_feedback/service.py tests/test_api_beta_feedback.py` passed; OpenSpec strict validations and `git diff --check` passed.

### F-065 Runtime diagnostics preserve sensitive marker values in text fields

- Severity: High
- Affected boundary: observability runtime diagnostics persistence and admin diagnostics API/UI responses.
- Evidence: `RuntimeDiagnosticsService.record()` only redacted detail values by sensitive key and stored `event_type`/`message` verbatim; `_record()` returned stored diagnostic message/details directly. A diagnostic with secret-looking values, storage locators, filesystem paths, raw prompt/output markers, bytes, or base64 under otherwise safe keys could therefore persist and return those values through platform-admin runtime diagnostics, world-admin diagnostics, conversation diagnostics, and realtime admin diagnostic payloads. Focused `uv run pytest tests/test_observability.py tests/test_observability_incidents.py -q` also failed during collection because `conversations.services` imported `noveland.observability` at module import time while observability imported beta feedback/conversations models, exposing a circular import in the observability test path.
- Impact: runtime/provider/conversation diagnostics can accidentally retain and expose resolved secrets or internal payload locators in diagnostic text even though observability specs require API/UI diagnostics to omit them; the circular import also breaks the observability focused gate.
- Intended remediation: break the conversations-to-observability package import cycle, redact sensitive marker values in runtime diagnostic event type, message, and details before persistence, reapply redaction on read for historical diagnostics, and add focused observability regression coverage.
- Status: Remediated in observability diagnostics redaction batch.
- Verification: `cd backend && uv run pytest tests/test_observability.py tests/test_observability_incidents.py -q` passed with 6 tests; `cd backend && uv run pytest tests/test_api_conversations.py tests/test_api_realtime.py tests/test_api_worlds.py::test_world_diagnostics_require_world_admin -q` passed with 13 tests; focused backend ruff/mypy passed for observability/conversations services and observability tests; full `cd backend && uv run pytest` passed with 564 passed and 8 skipped; full `cd backend && uv run ruff check .` and `cd backend && uv run mypy .` passed.

### F-066 Speech TTS/STT API responses expose media storage URIs and raw invocation text

- Severity: High
- Affected boundary: world-admin speech test action API responses and speech admin console data boundary.
- Evidence: `POST /worlds/{world_id}/speech/tts` returns `TTSResult` with `output_asset: MediaAssetRecord`, `output_objects: list[MediaObjectRecord]`, and `model_invocation: InvocationRecordView`. Dynamic API verification showed a successful TTS response contained `output_asset.storage_uri` and `output_objects[0].storage_uri` values beginning with `media://...`, and `model_invocation.input_text` echoed the submitted test text. `Speech Admin Console` spec requires explicit TTS/STT test response rendering to avoid raw audio bytes, storage paths, and resolved secrets, and the broader architecture audit treats raw prompt/output and storage locator exposure as forbidden outside dedicated safe admin evidence surfaces.
- Impact: speech test API responses can leak internal object-storage locators and raw provider invocation payload fields directly to the speech admin UI instead of requiring the dedicated media/invocation admin surfaces for deeper diagnostics.
- Intended remediation: keep speech service persistence and provider execution unchanged, but shape `/speech/tts` and `/speech/stt` API responses through speech-specific safe response DTOs that preserve IDs/status/MIME/checksum/transcript/invocation IDs while omitting media storage locators, raw invocation text/json/error payloads, and provider request/result internals.
- Status: Remediated in speech safe response shaping batch.
- Verification: `cd backend && uv run pytest tests/test_api_speech.py -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_speech.py tests/test_speech_service.py tests/test_voice_profiles.py -q` passed with 11 tests; focused backend `uv run ruff check services/api/src/noveland/services/api/speech.py tests/test_api_speech.py` passed; focused backend `uv run mypy services/api/src/noveland/services/api/speech.py tests/test_api_speech.py` passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 564 passed and 8 skipped.

### F-067 Member player actor profiles expose arbitrary forbidden profile JSON

- Severity: High
- Affected boundary: member-readable player actor list/bind responses and player actor profile persistence.
- Evidence: backend/services/api/src/noveland/services/api/worlds.py exposes GET /worlds/{world_id}/player-actors and PUT /worlds/{world_id}/player-actors with get_world_member_context, and _player_actor_response() returns PlayerActorProfile.profile_json directly as profile. Dynamic API verification showed a world admin could bind a profile for a member with storage_uri=media://hidden and nested raw_prompt=secret, after which the ordinary member own GET /player-actors response returned those forbidden values verbatim.
- Impact: ordinary world members can receive internal storage refs, raw prompt/output markers, secret/auth refs, bytes, base64, or other operator-only evidence through player actor profile JSON when admin-authored or historically dirty profile metadata exists.
- Intended remediation: sanitize player actor profile JSON on bind before persistence and sanitize again on response shaping for historical records, preserving safe profile keys while omitting forbidden keys/values.
- Status: Remediated in player actor profile redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 38 tests; focused backend `uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; focused backend `uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 564 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.

### F-068 Member agent character profiles expose arbitrary forbidden profile JSON

- Severity: High
- Affected boundary: member-readable agent catalog REST API and agent character profile response shaping.
- Evidence: `backend/services/api/src/noveland/services/api/worlds.py` exposes `GET /worlds/{world_id}/agents` with `get_world_member_context`, and `_agent_response()` returns `Agent.character_profile` directly even when `include_admin_fields` is false. Dynamic API verification showed a world admin could create an agent with `character_profile.storage_uri=media://private/agent-profile` and nested `raw_prompt=operator prompt`, after which an ordinary member `GET /agents` response returned those forbidden values verbatim while provider/config fields were already redacted.
- Impact: ordinary world members can receive internal storage refs, raw prompt/output markers, secret/auth refs, bytes, base64, or other operator-only evidence embedded in agent character profile JSON despite the agent catalog being a member-facing surface.
- Intended remediation: sanitize agent character profile JSON for non-admin agent catalog responses, preserving safe public characterization fields while omitting forbidden keys/values; keep admin authoring responses unchanged.
- Status: Remediated in agent character profile redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_create_agent_from_preset_materializes_persona_calendar_and_provider_mapping -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope tests/test_api_worlds.py::test_create_agent_from_preset_materializes_persona_calendar_and_provider_mapping -q` passed with 2 tests; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 38 tests; focused backend `uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; focused backend `uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 564 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.

### F-069 Member player choices expose arbitrary context and consequence preview JSON

- Severity: High
- Affected boundary: member-readable player choice create/list REST responses and player choice metadata response shaping.
- Evidence: `backend/services/api/src/noveland/services/api/worlds.py` exposes `GET /worlds/{world_id}/player-choices` and `POST /worlds/{world_id}/player-choices` with `get_world_member_context`, and `_player_choice_response()` redacts `prompt` for non-admins but returns `PlayerChoiceRecord.context_json` and `consequence_preview` directly. Dynamic API verification showed an ordinary member could create a choice with `context.storage_uri=media://private/choice`, nested `raw_prompt=operator prompt`, and `effects.offscreen_events[].raw_output=provider output`; both the create response and later member list response returned those forbidden values verbatim.
- Impact: member/player choice APIs can leak internal storage refs, raw prompt/output markers, secret/auth refs, bytes, base64, or historically dirty review metadata through context and consequence preview JSON even after prompt text redaction.
- Intended remediation: sanitize player choice context and consequence preview JSON for non-admin choice responses, preserving safe diagnostics and public choice metadata while omitting forbidden keys/values; keep admin review responses unchanged.
- Status: Remediated in player choice metadata redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope tests/test_api_worlds.py::test_create_agent_from_preset_materializes_persona_calendar_and_provider_mapping -q` passed with 2 tests; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 38 tests; focused backend `uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; focused backend `uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 564 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.

### F-070 Member journal and notification text expose forbidden markers

- Severity: High
- Affected boundary: member-readable player journal and in-world notification list responses.
- Evidence: `backend/services/api/src/noveland/services/api/worlds.py` exposes `GET /worlds/{world_id}/player-journal` and `GET /worlds/{world_id}/notifications` with `get_world_member_context`. F-019 already hides source refs and metadata for non-admins, but `_journal_entry_response()` and `_notification_response()` still return `title` and `body` verbatim. Dynamic API verification showed a world admin could create a journal entry for a member with body `raw_prompt operator prompt` and a notification with title `media://private/notice` plus body `raw_output provider output`; the ordinary member list responses returned those forbidden text values verbatim.
- Impact: ordinary members can receive raw prompt/output markers, storage refs, filesystem paths, secret/auth refs, bytes, or base64-looking evidence through journal/notification free text even though source refs and metadata are redacted.
- Intended remediation: sanitize journal and notification title/body text for non-admin responses, preserving safe text and status fields while blanking sensitive-looking text; keep admin review responses unchanged.
- Status: Remediated in journal and notification text redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_knowledge_player_guardrail_apis_and_acceptance_gap_fixes -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 38 tests; focused backend `uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; focused backend `uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 564 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.

### F-071 Member player choice preview exposes arbitrary effect JSON

- Severity: High
- Affected boundary: member-readable player choice preview REST response and player choice effect metadata response shaping.
- Evidence: `backend/services/api/src/noveland/services/api/worlds.py` exposes `POST /worlds/{world_id}/player-choices/preview` with `get_world_member_context`; the endpoint hides diagnostics for non-admins but returns `ChoiceConsequencePreview.relationship_updates`, `faction_updates`, and `offscreen_events` directly from arbitrary request `effects`. Static audit showed ordinary members can include `storage_uri`, `media://`, `raw_prompt`, `raw_output`, or filesystem path markers in preview effect JSON and receive them back in the preview response.
- Impact: member/player preview APIs can leak internal storage refs, raw prompt/output markers, secret/auth refs, bytes, base64, or historically copied operator evidence through consequence preview JSON even after F-017 diagnostics redaction and F-069 create/list metadata redaction.
- Intended remediation: sanitize relationship updates, faction updates, and offscreen event preview JSON for non-admin preview responses, preserving safe public preview fields while omitting forbidden keys/values; keep admin preview responses unchanged.
- Status: Remediated in player choice preview effect redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope -q` passed with 1 test after first reproducing the raw `raw_prompt` preview leak; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 38 tests; focused backend `uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; focused backend `uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 564 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.

### F-072 Offscreen event resolution persists unsafe payload JSON

- Severity: High
- Affected boundary: world event payload persistence through offscreen event resolution.
- Evidence: `backend/packages/worlds/src/noveland/worlds/autonomous.py` resolves `OffscreenEventQueueItem.payload_json` into `WorldEventAppend(payload=...)` without sanitization. Queue payloads can originate from admin offscreen-event creation in `backend/services/api/src/noveland/services/api/worlds.py`, GM macro plan payloads, player choice effect payloads, and forked queue state in `backend/packages/worlds/src/noveland/worlds/gm.py`.
- Impact: storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, or base64-like values in queued offscreen payloads can be persisted into `world_events.payload`, violating the world event payload prohibition boundary even when member-facing previews and responses are redacted.
- Intended remediation: sanitize queued offscreen payload JSON before appending resolved world events, preserving safe event context fields and applying the protection to historical queue rows regardless of their source.
- Status: Remediated in offscreen event payload persistence redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_offscreen_resolution_sanitizes_persisted_world_event_payload -q` first failed on unredacted `storage_uri` persisted in `WorldEventModel.payload`, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 39 tests; focused backend `uv run ruff check packages/worlds/src/noveland/worlds/autonomous.py tests/test_api_worlds.py` passed; focused backend `uv run mypy packages/worlds/src/noveland/worlds/autonomous.py tests/test_api_worlds.py` passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 565 passed and 8 skipped. `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

### F-073 GM proposal resolution persists unsafe proposed payload JSON

- Severity: High
- Affected boundary: world event payload persistence through GM event proposal resolution.
- Evidence: `backend/packages/worlds/src/noveland/worlds/gm.py` resolves a `GMEventProposal` with `payload={**proposal.proposed_payload, "proposal_id": ..., "proposal_title": ...}` and writes it through `WorldEventAppend`. `GMProposalCreateRequest.proposed_payload` in `backend/services/api/src/noveland/services/api/worlds.py` accepts arbitrary JSON, and macro planning also persists proposed payload JSON before later review.
- Impact: storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, or base64-like values in GM proposal payloads can be persisted into `world_events.payload`, violating the world event payload prohibition boundary despite admin-only proposal review.
- Intended remediation: sanitize the merged GM proposal event payload at the domain persistence boundary before `WorldEventAppend`, preserving safe proposal identity and event context fields while applying the same protection to historical dirty proposal rows.
- Status: Remediated in GM proposal event payload persistence redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_gm_proposal_resolution_sanitizes_persisted_world_event_payload -q` first failed on unredacted `storage_uri` persisted in `WorldEventModel.payload`, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_worlds.py::test_offscreen_resolution_sanitizes_persisted_world_event_payload tests/test_api_worlds.py::test_gm_proposal_resolution_sanitizes_persisted_world_event_payload -q` passed with 2 tests; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 40 tests; focused backend `uv run ruff check packages/worlds/src/noveland/worlds/sanitization.py packages/worlds/src/noveland/worlds/autonomous.py packages/worlds/src/noveland/worlds/gm.py tests/test_api_worlds.py` passed; focused backend `uv run mypy packages/worlds/src/noveland/worlds/sanitization.py packages/worlds/src/noveland/worlds/autonomous.py packages/worlds/src/noveland/worlds/gm.py tests/test_api_worlds.py` passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 566 passed and 8 skipped. `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

### F-074 Event store accepts unsafe payloads from remaining producers

- Severity: High
- Affected boundary: global world event payload persistence in `WorldEventStore.append_event()`.
- Evidence: `backend/packages/events/src/noveland/events/event_store.py` writes `payload=event_input.payload` directly into `WorldEventModel`. F-072 and F-073 added producer-level sanitization for offscreen resolution and GM proposal resolution, but other producers such as `LivingWorldGuardrailService.reveal_secret()` still pass arbitrary admin-authored metadata into event payloads.
- Impact: any missed producer can persist storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, or base64-like values into `world_events.payload`, violating the event payload prohibition and making the safety boundary depend on every caller remembering to sanitize.
- Intended remediation: move world event payload sanitization into the `events` package and apply it inside `WorldEventStore.append_event()` before persistence; keep producer-level payloads safe by construction where useful, but make the event store the final enforcement point for historical and future producers.
- Status: Remediated in event store payload safety enforcement batch.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_event_store_sanitizes_secret_reveal_event_payload -q` first failed on unredacted `storage_uri` persisted in `WorldEventModel.payload`, then passed after remediation; `cd backend && uv run pytest tests/test_api_worlds.py::test_offscreen_resolution_sanitizes_persisted_world_event_payload tests/test_api_worlds.py::test_gm_proposal_resolution_sanitizes_persisted_world_event_payload tests/test_api_worlds.py::test_event_store_sanitizes_secret_reveal_event_payload -q` passed with 3 tests; `cd backend && uv run pytest tests/test_api_worlds.py tests/test_event_contracts.py -q` passed with 49 tests; focused backend ruff/mypy passed for `events/sanitization.py`, `event_store.py`, `autonomous.py`, `gm.py`, `test_api_worlds.py`, and `test_event_contracts.py`; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 567 passed and 8 skipped. `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

### F-075 Member world bible public canon JSON leaks forbidden evidence

- Severity: High
- Affected boundary: member-readable world bible REST API and canon-management public JSON response shaping.
- Evidence: `backend/services/api/src/noveland/services/api/worlds.py` exposes `GET /worlds/{world_id}/bible` with `get_world_member_context`; F-023 hid `source_material`, `continuity_config`, and `metadata` for non-admins, but `_world_bible_response()` still returned `canon_timeline`, `setting_rules`, `forbidden_changes`, and `sequel_boundaries` directly. Those fields are arbitrary JSON (`list[dict[str, Any]]` / `dict[str, Any]`) accepted from admin upserts and can contain storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, base64, or other operator-only canon-management evidence.
- Impact: ordinary world members can receive forbidden internal evidence through otherwise public world bible canon JSON even though source material/config/metadata are redacted.
- Intended remediation: sanitize member-facing world bible public canon JSON with the existing public JSON sanitizer while preserving safe canon timeline, setting rule, forbidden change, and sequel boundary fields; preserve full unsanitized canon-management JSON for admin routes.
- Status: Remediated in world bible public canon JSON redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_world_bible_api_preserves_continuity_contract_and_access -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests; focused backend `uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; focused backend `uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 567 passed and 8 skipped. `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

### F-076 Member conversation turn transcript text exposes forbidden markers

- Severity: High
- Affected boundary: member-readable conversation turn REST API and transcript response shaping.
- Evidence: `backend/services/api/src/noveland/services/api/conversations.py` exposes `GET /worlds/{world_id}/conversations/{conversation_id}/turns` with `get_world_member_context`. F-029 hid `run_id` and `error_text` for non-admins, but `_turn_response()` still returned `ConversationTurnRecord.input_text` and `output_text` verbatim. Admin-created seed turns and provider-backed agent turns can contain storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, base64, or other operator-only execution evidence in transcript text.
- Impact: ordinary world members can receive forbidden internal evidence through conversation transcript text even though runtime run IDs and error diagnostics are redacted.
- Intended remediation: blank sensitive-looking transcript text for non-admin turn responses while preserving safe transcript text, identity, speaker, status, and timing fields; preserve unsanitized transcript text for admin conversation management and diagnostics.
- Status: Remediated in conversation turn transcript text redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_conversations.py::test_conversation_api_enforces_access_and_manual_advance -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_conversations.py -q` passed with 6 tests; focused backend `uv run ruff check services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py` passed; focused backend `uv run mypy services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py` passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 567 passed and 8 skipped. `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.


### F-077 Member media asset catalog exposes internal provider/source refs

- Severity: High
- Affected boundary: member-readable media asset catalog, search, lineage, tag, and collection response shaping.
- Evidence: `backend/services/api/src/noveland/services/api/media.py` exposes `GET /worlds/{world_id}/media/assets`, `/assets/search`, `/assets/{asset_id}`, `/assets/{asset_id}/lineage`, tags, and collections with `get_world_member_context`. F-020/F-021 hid storage URIs and metadata for non-admins, but member `MediaAssetRecord` responses still returned `provider_kind`, `source_job_id`, `source_event_id`, `source_invocation_id`, and `created_by_actor_ref`; member lineage input records still returned `source_job_id`; member tags/collections still returned `created_by_actor_ref`. Member list/search filters also accepted source event, source invocation, and provider kind filters that could reveal internal provenance by result-set inference.
- Impact: ordinary world members can receive or infer provider/source/internal actor provenance for visible media assets even though storage refs and media job diagnostics are redacted.
- Intended remediation: blank media asset provider/source/actor fields, lineage input source job IDs, and tag/collection actor refs for non-admin responses; reject member catalog/search filters that target internal source event IDs, source invocation IDs, or provider kinds; preserve full fields and filters for admin media management.
- Status: Remediated in media catalog internal provenance redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_media.py::test_media_api_member_visibility_acl_and_csrf tests/test_api_media.py::test_media_api_member_metadata_redaction_across_visible_records -q` passed with 2 tests; `cd backend && uv run pytest tests/test_api_media.py -q` passed with 9 tests; focused backend `uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py` passed; focused backend `uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py` passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 567 passed and 8 skipped. `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.


### F-078 Member playback presentation GET is admin-only and lacks member-safe DTO shaping

- Severity: High
- Affected boundary: member/reader conversation playback and conversation turn presentation API exposure.
- Evidence: `web/lib/worlds/server.ts:getConversationPlaybackData()` fetches `/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation` for playback, while `backend/services/api/src/noveland/services/api/conversation_presentations.py` protects the GET route with `get_world_admin_context`. The same canonical presentation record can also contain internal sprite/voice/transcript authoring refs and generated `presentation_json` provenance such as media job or model invocation IDs.
- Impact: ordinary world members cannot load otherwise safe playback presentation state through the documented reader/member playback flow; if the route is made member-readable without response shaping, it risks exposing authoring/provenance refs and dirty historical presentation JSON to reader/member surfaces.
- Intended remediation: make presentation GET member-readable, preserve full records for world/platform admins, and return a member-safe presentation record for ordinary members that keeps playback asset IDs/state while blanking internal authoring refs and recursively removing forbidden storage/provider/prompt/invocation/media-job evidence from `presentation_json`. Keep PUT, PATCH, render-visual, render-speech, and transcribe-audio admin-only.
- Status: Remediated in member-safe conversation presentation GET batch.
- Verification: `cd backend && uv run pytest tests/test_api_conversation_presentations.py -q` passed with 2 tests; `cd backend && uv run pytest tests/test_api_permission_matrix.py tests/test_security_regression_suite.py tests/test_api_conversation_presentations.py -q` passed with 9 tests; focused backend ruff/mypy passed for `conversation_presentations.py`, `test_api_conversation_presentations.py`, `test_api_permission_matrix.py`, and `test_security_regression_suite.py`; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 567 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.


### F-079 Member presentation DTO exposes non-deliverable media asset IDs

- Severity: High
- Affected boundary: member/reader conversation playback presentation DTO and reader media delivery visibility.
- Evidence: F-078 made presentation GET member-readable and redacted authoring/provenance fields, but non-admin responses still preserve `background_asset_id`, `composite_scene_asset_id`, and `tts_media_asset_id` directly from `conversation_turn_presentations`. Presentation rendering and admin upsert paths can store `WORLD_ADMIN`, `PRIVATE`, `HIDDEN`, suppressed, unreferenced, or otherwise non-reader-deliverable media asset IDs in those fields while reader media delivery would not return descriptors or bytes for them.
- Impact: ordinary members can learn internal media asset UUIDs for admin-only or hidden playback assets even when the actual media bytes and descriptors are blocked, creating a side channel across the reader media visibility boundary and making playback DTOs disagree with reader media delivery.
- Intended remediation: for ordinary member presentation GET responses, keep media asset IDs only when `ReaderMediaDeliveryService` can produce a descriptor for the same worldline; otherwise return `null` for the presentation media asset field. Preserve full media IDs for world/platform admins and keep mutation/render routes admin-only.
- Status: Remediated in member presentation media visibility filtering batch.
- Verification: `cd backend && uv run pytest tests/test_api_conversation_presentations.py -q` passed with 3 tests; `cd backend && uv run pytest tests/test_api_permission_matrix.py tests/test_security_regression_suite.py tests/test_api_conversation_presentations.py -q` passed with 10 tests; focused backend ruff/mypy passed for `conversation_presentations.py` and `test_api_conversation_presentations.py`; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.


### F-080 Dashboard world selector navigation does not encode query values

- Severity: Medium
- Affected boundary: Web local app route navigation and route-boundary preservation.
- Evidence: `web/features/dashboard/world-management-dashboard.tsx` built dashboard navigation with unencoded `/?world=${nextWorldId}` when switching worlds and unencoded `/?world=${world.id}` after creating a world. These values come from API data or action responses and are appended directly into a query string.
- Impact: a malformed or malicious world identifier containing `&`, `?`, or `#` can escape the intended `world` query parameter and become extra query parameters or a fragment in local navigation, creating a frontend route-boundary injection point even though backend IDs are normally UUIDs.
- Intended remediation: encode dashboard world query values before local navigation and add focused component coverage for world IDs containing reserved URL characters.
- Status: Remediated in dashboard world query navigation encoding batch.
- Verification: `cd web && npm run test -- features/dashboard/world-management-dashboard.test.tsx` passed with 6 tests; `cd web && npm run lint` passed; `cd web && npm run typecheck` passed; full `cd web && npm run test` passed with 52 files and 187 tests, with existing RuntimeAdmin React act warnings; `cd web && npm run build` passed; `cd web && npm run check:next-env` passed after restoring the expected `.next/types/routes.d.ts` import regenerated by e2e/dev; `cd web && npm run test:e2e` passed with 21 tests; OpenSpec strict validations and `git diff --check` passed.

### F-081 Member agent run source evidence leak

- Severity: High
- Affected boundary: member-readable agent runtime run list REST API.
- Evidence: `backend/services/api/src/noveland/services/api/worlds.py` exposes `GET /worlds/{world_id}/agents/{agent_id}/runs` with `get_world_member_context` and serializes runs through `_agent_run_response(run, include_admin_fields=can_manage)`. The helper already redacts prompt text, response text, provider profile refs, and diagnostics for ordinary members, but still returns `source_calendar_entry_id`, `source_schedule_rule_id`, and `created_event_id` directly.
- Impact: ordinary world members can correlate operator/runtime execution evidence to internal calendar entries, schedule rules, and world events through a member-readable status route even though those source references are operator-only run internals.
- Intended remediation: redact source calendar, schedule rule, and created event refs from non-admin agent run responses while preserving admin diagnostics and safe member run status/timing fields.
- Status: Remediated in member agent run source evidence redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_agent_runs_and_narrative_artifacts_api -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_worlds.py::test_agent_runs_and_narrative_artifacts_api tests/test_api_worlds.py::test_agent_run_apis_filter_by_worldline -q` passed with 2 tests; focused backend ruff/mypy passed for `worlds.py` and `test_api_worlds.py`; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped.

### F-082 Member replay state clock source evidence leak

- Severity: High
- Affected boundary: member-readable replay state REST API.
- Evidence: `backend/services/api/src/noveland/services/api/worlds.py` exposes `GET /worlds/{world_id}/replay/state` with `get_world_member_context` and returns `WorldReplayService.replay_state()` directly. `backend/packages/events/src/noveland/events/replay.py` populates `ClockReplayState.last_event_id` and `last_event_sequence` from the source clock event, so ordinary members can read source event evidence through replay state even though clock transition audit and world event audit routes are admin-only.
- Impact: ordinary world members can correlate replay clock state to internal world event identifiers and event sequencing evidence, bypassing the operator-only source-ref redaction pattern applied to presence, snapshots, and agent runs.
- Intended remediation: shape replay state responses by caller role; preserve clock source refs for admins while ordinary members receive safe reconstructed replay state with clock `last_event_id` and `last_event_sequence` redacted.
- Status: Remediated in member replay state source evidence redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_replay_and_snapshot_api_reads_state_and_creates_snapshot -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_worlds.py::test_replay_and_snapshot_api_reads_state_and_creates_snapshot tests/test_api_worlds.py::test_world_event_audit_requires_admin_and_filters_events -q` passed with 2 tests; focused backend ruff/mypy passed for `worlds.py` and `test_api_worlds.py`; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped.

### F-083 Member agent catalog source preset provenance leak

- Severity: High
- Affected boundary: member-readable agent catalog REST API.
- Evidence: `backend/services/api/src/noveland/services/api/worlds.py` exposes `GET /worlds/{world_id}/agents` with `get_world_member_context` and serializes rows through `_agent_response(agent, include_admin_fields=can_manage)`. The helper already redacts provider profile IDs, execution config, and unsafe character profile JSON for ordinary members, but still returns `source_preset_id` and `source_preset_version` directly.
- Impact: ordinary world members can correlate public agent catalog entries to operator-authored preset provenance and versioning evidence even though platform agent presets are admin-managed records and other agent configuration internals are redacted.
- Intended remediation: redact source preset IDs and versions from non-admin agent catalog responses while preserving admin create/update/list diagnostics and safe member agent identity/characterization fields.
- Status: Remediated in member agent catalog source preset provenance redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_create_agent_from_preset_materializes_persona_calendar_and_provider_mapping -q` first failed on unredacted `source_preset_id`, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests; focused backend ruff/mypy passed for `worlds.py` and `test_api_worlds.py`; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.

### F-084 Member latest snapshot created event evidence leak

- Severity: High
- Affected boundary: member-readable latest world snapshot REST API.
- Evidence: `backend/services/api/src/noveland/services/api/worlds.py` exposes `GET /worlds/{world_id}/snapshots/latest` with `get_world_member_context` and serializes records through `_snapshot_response(snapshot, include_admin_fields=can_manage)`. F-021 redacted payload, payload_uri, payload_location, and metadata for ordinary members, but `_snapshot_response()` still returns `created_by_event_id` directly.
- Impact: ordinary world members can correlate snapshot records to internal world event identifiers even though world event audit and snapshot integrity routes are admin-only, and despite later source-ref redactions for replay state and agent runs.
- Intended remediation: redact `created_by_event_id` from non-admin latest snapshot responses while preserving admin snapshot diagnostics and safe member snapshot identity, worldline, sequence coverage, schema/status, and creation time.
- Status: Remediated in member latest snapshot source evidence redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_replay_and_snapshot_api_reads_state_and_creates_snapshot -q` first failed on unredacted `created_by_event_id`, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_worlds.py::test_replay_and_snapshot_api_reads_state_and_creates_snapshot tests/test_api_worlds.py::test_world_event_audit_requires_admin_and_filters_events -q` passed with 2 tests; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests; focused backend ruff/mypy passed for `worlds.py` and `test_api_worlds.py`; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.

### F-085 Member player choice applied event evidence leak

- Severity: High
- Affected boundary: member-readable player choice create/list REST APIs.
- Evidence: `backend/services/api/src/noveland/services/api/worlds.py` exposes `POST /worlds/{world_id}/player-choices` and `GET /worlds/{world_id}/player-choices` with `get_world_member_context`. `_player_choice_response(choice, include_admin_fields=can_manage)` already redacts prompt text and sanitizes context/consequence preview JSON for ordinary members, but still returns `applied_event_id` directly. `LivingWorldGMService.record_player_choice()` always appends a `player.choice_recorded` event and sets `choice.applied_event_id`.
- Impact: ordinary world members can correlate their player-choice records to internal world event identifiers even though world event audit is admin-only and other member source/event refs are now redacted.
- Intended remediation: redact `applied_event_id` from non-admin player choice create/list responses while preserving admin review diagnostics and safe member choice identity, selected option, sanitized context/consequence preview, and timing fields.
- Status: Remediated in member player choice event evidence redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope -q` first failed on unredacted `applied_event_id`, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests; focused backend ruff/mypy passed for `worlds.py` and `test_api_worlds.py`; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.

### F-086 Player privacy export choice applied event evidence leak

- Severity: High
- Affected boundary: member-readable player privacy export REST API.
- Evidence: `backend/services/api/src/noveland/services/api/player_privacy.py` exposes `GET/POST /worlds/{world_id}/player/privacy/export` with `get_world_member_context`. `PlayerPrivacyService._build_export_payload()` already redacts journal source refs, notification source refs, and intervention choice/event linkage, but still serializes `PlayerChoiceRecord.applied_event_id` into `PlayerPrivacyChoiceExport.applied_event_id`.
- Impact: ordinary world members can recover internal player choice world event IDs through privacy export even though normal member player choice responses now redact `applied_event_id` and world event audit is admin-only.
- Intended remediation: redact choice `applied_event_id` from player privacy exports while preserving safe player-owned choice identity, selected option, kind, actor linkage, and timing fields.
- Status: Remediated in player privacy export choice event evidence redaction batch.
- Verification: `cd backend && uv run pytest tests/test_api_player_privacy.py::test_player_privacy_export_is_player_scoped_and_redacted -q` first failed on unredacted choice `applied_event_id`, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_player_privacy.py -q` passed with 3 tests; focused backend ruff/mypy passed for `player_privacy/service.py` and `test_api_player_privacy.py`; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.

### F-087 Member-owned JSON sanitizers miss camelCase sensitive keys

- Severity: High
- Affected boundary: member-readable player session resume state and beta feedback metadata persistence/response shaping.
- Evidence: `backend/packages/player_sessions/src/noveland/player_sessions/service.py` strips sensitive JSON keys by lowercasing and comparing against snake_case markers, while `backend/packages/beta_feedback/src/noveland/beta_feedback/service.py` only rejects exact lower-case sensitive keys. Web/client state commonly uses camelCase keys such as `rawPrompt`, `rawOutput`, `storageUri`, and `promptSnapshotId`, which are not matched by the current filters when their values are otherwise safe-looking strings.
- Impact: ordinary members can persist and later read raw prompt/output labels, storage refs, prompt snapshot references, or similarly sensitive metadata through player resume state or feedback metadata, violating the member API no-leak boundary and preserving unsafe data for admin reads as well.
- Intended remediation: normalize JSON keys before sensitive-key comparison in both services, expand value marker matching for common camelCase/compact sensitive terms, and preserve safe metadata fields.
- Status: Remediated in member-owned JSON sensitive-key normalization batch.
- Verification: `cd backend && uv run pytest tests/test_api_player_sessions.py::test_player_session_resume_round_trip_is_player_safe tests/test_api_beta_feedback.py::test_tester_creates_own_feedback_and_admin_triages_without_leaks -q` first failed on unredacted camelCase sensitive keys, then passed with 2 tests after remediation; `cd backend && uv run pytest tests/test_api_player_sessions.py tests/test_api_beta_feedback.py -q` passed with 7 tests; focused backend ruff/mypy passed for `player_sessions/service.py`, `beta_feedback/service.py`, and their API tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.

### F-088 Remaining package-local JSON sanitizers miss camelCase sensitive keys

- Severity: High
- Affected boundary: private beta invite metadata, player privacy export/request JSON, and moderation report/review metadata persistence/response shaping.
- Evidence: `backend/packages/private_beta/src/noveland/private_beta/service.py`, `backend/packages/player_privacy/src/noveland/player_privacy/service.py`, and `backend/packages/moderation/src/noveland/moderation/service.py` still compare sensitive JSON keys using exact lower-case or snake_case-only checks. CamelCase/compact keys such as `rawPrompt`, `rawOutput`, `storageUri`, and `promptSnapshotId` can survive sanitization when values are otherwise safe-looking strings.
- Impact: member/admin routes can persist or return raw prompt/output labels, storage refs, prompt snapshot references, or similarly sensitive metadata in onboarding, privacy, and moderation workflows, violating the shared no-leak boundary even after F-087 fixed player sessions and beta feedback.
- Intended remediation: normalize JSON keys before sensitive-key comparison in private beta, player privacy, and moderation sanitizers; expand value marker matching for common camelCase/compact sensitive terms; preserve safe metadata fields.
- Status: Remediated in remaining package-local JSON sensitive-key normalization batch.
- Verification: `cd backend && uv run pytest tests/test_api_private_beta.py::test_admin_invite_lifecycle_redeem_and_profile_bootstrap_are_safe tests/test_api_player_privacy.py::test_player_privacy_export_is_player_scoped_and_redacted tests/test_api_moderation.py::test_reader_can_create_report_and_admin_can_review_without_leaks -q` first failed on unredacted camelCase sensitive keys, then passed with 3 tests after remediation; `cd backend && uv run pytest tests/test_api_private_beta.py tests/test_api_player_privacy.py tests/test_api_moderation.py -q` passed with 12 tests; focused backend ruff/mypy passed for `private_beta/service.py`, `player_privacy/service.py`, `moderation/service.py`, and their API tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.

### F-089 Event store payload sanitizer misses camelCase forbidden keys

- Severity: High
- Affected boundary: global `world_events.payload` persistence safety enforcement.
- Evidence: `backend/packages/events/src/noveland/events/sanitization.py` enforces F-074 by checking `key_text.strip().lower()` against snake_case forbidden keys. CamelCase/compact keys such as `rawPrompt`, `rawOutput`, `storageUri`, and `promptSnapshotId` are not matched when values are otherwise safe-looking strings.
- Impact: any world event producer can persist raw prompt/output labels, storage refs, prompt snapshot references, or similarly forbidden evidence into `world_events.payload`, bypassing the global event-store safety boundary that is meant to protect all current and future producers.
- Intended remediation: normalize event payload keys before forbidden-key comparison, expand forbidden value marker matching for common camelCase/compact sensitive terms, and keep safe event context fields.
- Status: Remediated in event-store payload key normalization batch.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_event_store_sanitizes_secret_reveal_event_payload -q` first failed on unredacted `rawPrompt` in `world_events.payload`, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_worlds.py::test_offscreen_resolution_sanitizes_persisted_world_event_payload tests/test_api_worlds.py::test_gm_proposal_resolution_sanitizes_persisted_world_event_payload tests/test_api_worlds.py::test_event_store_sanitizes_secret_reveal_event_payload tests/test_event_contracts.py -q` passed with 11 tests; focused backend ruff/mypy passed for `events/sanitization.py`, `test_api_worlds.py`, and `test_event_contracts.py`; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.

### F-090 Member media and presentation JSON sanitizers miss camelCase sensitive keys

- Severity: High
- Affected boundary: member-readable media metadata DTOs and member-readable conversation turn presentation JSON.
- Evidence: `backend/services/api/src/noveland/services/api/media.py` and `backend/services/api/src/noveland/services/api/conversation_presentations.py` filter forbidden member JSON keys with exact lower-case/snake_case checks. CamelCase/compact keys such as `rawPrompt`, `rawOutput`, `storageUri`, and `promptSnapshotId` can survive when values are otherwise safe-looking strings.
- Impact: ordinary world members can receive raw prompt/output labels, storage refs, prompt snapshot references, or provider/media-job evidence in media catalog/reference/lineage metadata or playback presentation JSON despite route-level storage/provenance redaction.
- Intended remediation: normalize member media metadata and member presentation JSON keys before forbidden-key comparison, expand value marker matching for common camelCase/compact sensitive terms, and preserve safe member-facing metadata/presentation fields.
- Status: Remediated in member media/presentation JSON sensitive-key normalization batch.
- Verification: `cd backend && uv run pytest tests/test_api_media.py::test_media_api_member_metadata_redaction_across_visible_records tests/test_api_conversation_presentations.py::test_conversation_presentation_api_renders_visual_speech_and_transcript -q` first failed on unredacted camelCase sensitive keys, then passed with 2 tests after remediation; `cd backend && uv run pytest tests/test_api_media.py tests/test_api_conversation_presentations.py -q` passed with 12 tests; focused backend ruff/mypy passed for `media.py`, `conversation_presentations.py`, and their API tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.

### F-091 Provider secret-key validators miss multiword camelCase variants

- Severity: High
- Affected boundary: provider integration config/default params, provider execution request JSON, provider budget metadata, package provider template validation/export, and multimodal diagnostics secret leak checks.
- Evidence: `backend/packages/providers/src/noveland/providers/secrets.py` normalizes sensitive keys with exact lower-case matching. Existing coverage rejects `api_key`/`authorization`, but read-only verification showed `clientSecret`, `bearerToken`, `privateKey`, and `secretKey` are accepted and preserved by `reject_sensitive_config()` / `sanitize_for_persistence()` despite equivalent snake_case keys being forbidden.
- Impact: platform/world admins or package metadata can persist raw provider secrets under common camelCase/mixed key names; downstream exports and diagnostics can miss or expose those fields instead of enforcing the auth_ref-only provider secret boundary.
- Intended remediation: centralize normalized provider sensitive-key detection, apply it to provider persistence redaction/rejection, package validation/export sanitization, budget unsafe JSON checks, and multimodal diagnostics, and add regression coverage for camelCase/compact secret-key forms.
- Status: Remediated in provider secret-key normalization batch.
- Verification: `cd backend && uv run pytest tests/test_provider_registry_service.py::test_registry_rejects_sensitive_provider_config_recursively tests/test_provider_registry_service.py::test_sanitizer_redacts_nested_sensitive_keys tests/test_api_package_contracts.py::test_package_contract_reports_registry_and_secret_issues tests/test_api_package_contracts.py::test_provider_config_export_is_sanitized_and_does_not_resolve_secret tests/test_provider_execution_service.py::test_budget_policy_rejects_camel_case_secret_metadata tests/test_multimodal_eval_service.py::test_multimodal_eval_detects_integrity_and_leak_failures -q` first failed with 6 failures on unblocked/unredacted camelCase secret keys, then passed with 6 tests after remediation; `cd backend && uv run pytest tests/test_narrative_quality_service.py::test_narrative_quality_dashboard_detects_blockers_and_sanitizes_evidence -q` passed with 1 test after switching provider health metadata coverage to `clientSecret`; `cd backend && uv run pytest tests/test_provider_registry_service.py tests/test_api_package_contracts.py tests/test_provider_execution_service.py tests/test_multimodal_eval_service.py tests/test_narrative_quality_service.py -q` passed with 79 tests; focused backend ruff/mypy passed for provider secrets, package contracts, multimodal eval, narrative quality, and their updated tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 569 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.

### F-092 Budget and diagnostics JSON miss camelCase storage/prompt keys

- Severity: High
- Affected boundary: provider budget policy `limits_json`/`metadata_json`, multimodal prompt snapshot leak diagnostics, and narrative quality dashboard evidence sanitization.
- Evidence: read-only verification showed `ProviderBudgetService._first_leaky_path()`, `MultimodalEvalService._json_contains_leaky_value()` / `_json_contains_forbidden_event_payload()`, and narrative quality `_is_leaky_key()` still compare storage/prompt/path keys with exact lower-case names. `storageUri`, `rawPrompt`, and `promptSnapshotId` are accepted or ignored while equivalent snake_case keys are rejected or flagged.
- Impact: operator/admin JSON can persist or surface storage references, prompt labels, and prompt snapshot evidence under common camelCase/compact key names; diagnostics can under-report dirty prompt snapshots and dashboards can return unsafe evidence keys.
- Intended remediation: normalize leaky storage/prompt/path key variants before provider budget rejection and diagnostic/dashboard leak checks, and add regression coverage for camelCase/compact key forms.
- Status: Remediated in budget/diagnostics leaky-key normalization batch.
- Verification: `cd backend && uv run pytest tests/test_provider_execution_service.py::test_budget_policy_rejects_camel_case_leaky_metadata tests/test_multimodal_eval_service.py::test_multimodal_eval_detects_camel_case_prompt_snapshot_leaks tests/test_narrative_quality_service.py::test_narrative_quality_dashboard_detects_camel_case_leaky_metadata -q` first failed with 3 failures on unblocked/unflagged camelCase leaky keys, then passed with 3 tests after remediation; `cd backend && uv run pytest tests/test_provider_execution_service.py tests/test_multimodal_eval_service.py tests/test_narrative_quality_service.py -q` passed with 72 tests; focused backend ruff/mypy passed for provider budget, multimodal eval, narrative quality, and their updated tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 572 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.

### F-093 Package and authoring validators miss camelCase storage/prompt keys

- Severity: High
- Affected boundary: world package manifest validation, authoring source metadata/config contracts, and asset generation policy/proposal contracts.
- Evidence: read-only verification showed `world_packaging.contracts._assert_safe_json()`, `authoring.contracts._assert_safe_json()`, and `asset_generation.contracts._assert_safe_json()` reject snake_case forbidden keys such as `storage_uri` and `raw_prompt`, but accept equivalent camelCase/compact keys including `storageUri`, `rawPrompt`, `promptSnapshotId`, and `filesystemPath`.
- Impact: import/export and authoring workflows can accept operational storage refs, prompt evidence, filesystem paths, bytes/base64 markers, or prompt snapshot references under common key variants, undermining package safety and authoring boundary checks.
- Intended remediation: normalize forbidden leaky key comparisons in package, authoring, and asset-generation contract validators and add regression coverage for camelCase/compact variants while preserving safe metadata.
- Status: Remediated in package/authoring leaky-key normalization batch.
- Verification: `cd backend && uv run pytest tests/test_api_world_packaging.py::test_world_package_import_rejects_forbidden_manifest_values tests/test_authoring_service.py::test_authoring_json_rejects_leaky_values tests/test_asset_generation_service.py::test_policy_rejects_leaky_json_and_preview_validates_worldline -q` first failed with 3 failures on accepted camelCase leaky keys, then passed with 3 tests after remediation; `cd backend && uv run pytest tests/test_api_world_packaging.py tests/test_authoring_service.py tests/test_asset_generation_service.py tests/test_api_asset_generation.py tests/test_authoring_regression_fixture.py -q` passed with 39 tests; focused backend ruff/mypy passed for world packaging, authoring, asset generation contracts, and their updated tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 572 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.

### F-094 Web invocation ledger redaction misses camelCase evidence keys

- Severity: High
- Affected boundary: Web admin invocation ledger evidence rendering for invocation JSON and prompt snapshot JSON.
- Evidence: `web/features/admin/invocation-ledger-admin.tsx` redacts evidence object keys using lower-case substring checks for snake_case markers such as `storage_uri`, `file_path`, and `raw_bytes`. It does not normalize key variants, so `storageUri`, `rawPrompt`, `promptSnapshotId`, or similar dirty backend evidence keys can render if the value is otherwise safe-looking text.
- Impact: authorized admin UI can display raw prompt labels, storage refs, prompt snapshot refs, or other internal evidence under common camelCase/compact keys despite the invocation-ledger browser contract requiring safe evidence fields and redaction where backend/API contracts require it.
- Intended remediation: normalize invocation ledger evidence keys before redaction, expand forbidden key markers for prompt/output/snapshot/storage/path/auth variants, and add Web regression coverage for camelCase/compact evidence keys.
- Status: Remediated in Web invocation ledger evidence key normalization batch.
- Verification: `cd web && npm run test -- features/admin/invocation-ledger-admin.test.tsx` first failed on rendered `storageUri` and `rawPrompt` evidence keys, then passed with 3 tests after remediation; `cd web && npm run test -- features/admin/invocation-ledger-admin.test.tsx lib/worlds/invocations.test.ts` passed with 6 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, `cd web && npm run check:next-env`, full `cd web && npm run test`, `cd web && npm run build`, and `cd web && npm run test:e2e` passed before commit. OpenSpec strict validations and `git diff --check` passed before commit.


### F-095 Web provider admin JSON panels expose dirty sensitive provider keys

- Severity: High
- Affected boundary: Web provider integration admin rendering for provider config JSON, default params JSON, capability JSON, and health metadata summaries.
- Evidence: `web/features/admin/provider-integration-admin.tsx` renders provider `config_json`, `default_params_json`, and capabilities directly through `JSON.stringify(...)`, and summarizes health metadata by raw key names. If legacy or dirty backend responses contain camelCase/compact sensitive keys such as `clientSecret`, `bearerToken`, `rawPrompt`, `storageUri`, or `promptSnapshotId`, the provider admin UI can display those key names and values despite the page contract saying resolved secrets are never displayed.
- Impact: an authorized admin browser can expose resolved provider secret material, raw prompt/storage evidence, or prompt snapshot references in editable Web JSON panels and metadata summaries, and a later save can echo dirty fields back through admin client helpers.
- Intended remediation: normalize provider admin JSON display keys before rendering, redact sensitive values, preserve safe provider configuration keys such as endpoint/model discovery paths and safe default params, and add Web regression coverage for camelCase/compact dirty provider evidence.
- Status: Remediated in Web provider admin JSON normalization batch.
- Verification: `cd web && npm run test -- features/admin/provider-integration-admin.test.tsx` first failed with 2 failures on rendered `clientSecret`, `rawPrompt`, `storageUri`, `bearerToken`, and `sk-live-secret` values in provider JSON panels, then passed with 5 tests after remediation; `cd web && npm run test -- features/admin/provider-integration-admin.test.tsx lib/worlds/provider-integrations.test.ts` passed with 10 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, `cd web && npm run check:next-env`, full `cd web && npm run test`, `cd web && npm run build`, and `cd web && npm run test:e2e` passed before commit. OpenSpec strict validations and `git diff --check` passed before commit.


### F-096 Web memory admin JSON panels expose dirty sensitive memory keys

- Severity: High
- Affected boundary: Web memory backend admin rendering for profile config JSON, safe secret refs, health details, and memory write/retrieval log summaries.
- Evidence: `web/features/admin/memory-backend-admin.tsx` renders profile config and `secret_refs` directly through `JSON.stringify(...)`, and renders a raw JSON `<pre>` containing health, logs, and jobs. If legacy or dirty backend responses contain camelCase/compact sensitive keys such as `clientSecret`, `bearerToken`, `rawPrompt`, `storageUri`, or `promptSnapshotId`, the memory admin UI can display those key names and raw values despite the memory backend secret-reference boundary.
- Impact: a platform admin browser can expose resolved memory provider secret material, raw prompt/storage evidence, or prompt snapshot references in editable Web JSON panels and diagnostic summaries, and a later save can echo dirty fields back through memory backend profile helpers.
- Intended remediation: normalize memory admin JSON display keys before rendering, redact sensitive string values, preserve safe memory config fields and safe `secret_refs` reference values, sanitize create/update payloads parsed from those panels, and add Web regression coverage for camelCase/compact dirty memory evidence.
- Status: Remediated in Web memory admin JSON normalization batch.
- Verification: `cd web && npm run test -- features/admin/memory-backend-admin.test.tsx` first failed on rendered `clientSecret`, `bearerToken`, `rawPrompt`, `storageUri`, `promptSnapshotId`, and `sk-live-secret` values in memory admin JSON panels and summaries, then passed with 1 test after remediation; `cd web && npm run test -- features/admin/memory-backend-admin.test.tsx lib/worlds/client.test.ts` passed with 36 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, `cd web && npm run check:next-env`, full `cd web && npm run test`, `cd web && npm run build`, and `cd web && npm run test:e2e` passed before commit. OpenSpec strict validations and `git diff --check` passed before commit.

### F-097 Web runtime admin diagnostics expose dirty sensitive text

- Severity: High
- Affected boundary: Web runtime admin rendering for runtime health notices, external tool policy text, scale readiness summaries, and runtime diagnostic rows.
- Evidence: `web/features/admin/runtime-admin.tsx` renders `runtimeHealth.reason`, `externalToolPolicy.operator_message`, `deny_reasons`, `audit_fields`, `scaleReadiness.sections[].summary`, blockers, recommendations, and diagnostic component/message strings directly. If dirty legacy API or SSE payloads contain `media://` storage refs, filesystem paths, local model paths, bearer tokens, `sk-` keys, raw prompt/output markers, prompt snapshot refs, bytes, or base64 markers, the runtime admin UI can display them despite backend diagnostic redaction and the no-leak admin evidence contracts.
- Impact: an authorized admin browser can expose resolved secrets, storage/path evidence, raw prompt/output labels, or prompt snapshot references through runtime diagnostics/readiness text, and SSE updates can reintroduce dirty diagnostic messages even if initial server loaders are clean.
- Intended remediation: add defensive runtime text sanitization before rendering runtime notices, compact lists, readiness summaries, and diagnostic rows; preserve safe operational strings such as policy modes, audit field names, iteration messages, readiness areas, and recommendations; add Web regression coverage for initial data and SSE diagnostic payloads.
- Status: Remediated in Web runtime admin diagnostics text normalization batch.
- Verification: `cd web && npm run test -- features/admin/runtime-admin.test.tsx` first failed against the unpatched component with dirty runtime strings visible in the failure DOM, then passed with 3 tests after remediation; `cd web && npm run test -- features/admin/runtime-admin.test.tsx lib/worlds/client.test.ts` passed with 38 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, `cd web && npm run check:next-env`, full `cd web && npm run test`, `cd web && npm run build`, and `cd web && npm run test:e2e` passed, with `next-env.d.ts` restored after e2e regenerated the dev route reference. OpenSpec strict validations and `git diff --check` passed before commit.

### F-098 Web dashboard JSON panels expose dirty sensitive config evidence

- Severity: High
- Affected boundary: Web world management dashboard rendering and submit handling for agent config, schedule rule config, provider profile capabilities, persona behavior policy, observation metadata, and narrative artifact metadata.
- Evidence: `web/features/dashboard/world-management-dashboard.tsx` renders selected agent config, schedule rule config, provider profile capabilities, and persona behavior policy through direct `JSON.stringify(...)`, and parses dashboard JSON form submissions with raw `jsonObject(...)`. Dirty legacy/API data or user-edited form values with `clientSecret`, `bearerToken`, `rawPrompt`, `storageUri`, `promptSnapshotId`, filesystem paths, bytes, or base64 markers can be displayed in editable dashboard panels and echoed back through update/create helpers.
- Impact: an authorized admin browser can expose resolved secrets, storage/path evidence, raw prompt/output labels, or prompt snapshot references in the general world dashboard, and later saves can resubmit the same dirty fields even when dedicated admin consoles defensively sanitize them.
- Intended remediation: add normalized dashboard JSON display and submit sanitization for dashboard-managed JSON objects, preserve safe dashboard config fields, and add Web regression coverage for dirty dashboard JSON panels.
- Status: Remediated in Web dashboard JSON normalization batch.
- Verification: `cd web && npm run test -- features/dashboard/world-management-dashboard.test.tsx` first failed against the unpatched component with dirty dashboard JSON visible in editable textareas, then passed with 7 tests after remediation; `cd web && npm run test -- features/dashboard/world-management-dashboard.test.tsx lib/worlds/client.test.ts` passed with 42 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed; full `cd web && npm run test` passed on rerun with 52 files and 189 tests after one unrelated `media-admin` timing miss passed in isolation; `cd web && npm run build` and `cd web && npm run test:e2e` passed, with `next-env.d.ts` restored after e2e regenerated the dev route reference. OpenSpec strict validations and `git diff --check` passed before commit.

### F-099 Web agent builder panels expose dirty sensitive agent evidence

- Severity: High
- Affected boundary: Web agent detail rendering and submit handling for agent character profile, agent config, relationship metadata, persona policy/config, observation metadata, run summary text, and run diagnostics.
- Evidence: `web/features/agents/agent-builder.tsx` renders agent `character_profile`, `config`, relationship `metadata`, persona `behavior_policy` and `policy_plugin_config`, and selected run diagnostics through direct `JSON.stringify(...)`, parses agent-builder JSON form submissions with raw `jsonObject(...)`, and renders run prompt/response summary text directly. Dirty legacy/API data or user-edited form values with `clientSecret`, `bearerToken`, `rawPrompt`, `storageUri`, `promptSnapshotId`, filesystem paths, bytes, or base64 markers can be displayed in editable/read-only agent builder panels and echoed back through update/create helpers.
- Impact: an authorized admin browser can expose resolved secrets, storage/path evidence, raw prompt/output labels, or prompt snapshot references in the agent builder, and later saves can resubmit the same dirty fields even when member APIs and dedicated admin consoles defensively sanitize them.
- Intended remediation: add normalized agent-builder JSON display and submit sanitization plus sensitive-looking run text sanitization; preserve safe characterization, relationship, persona, and operational fields; add Web regression coverage for dirty agent-builder panels.
- Status: Remediated in Web agent builder evidence normalization batch.
- Verification: `cd web && npm run test -- features/agents/agent-builder.test.tsx` first failed against the unpatched component with dirty agent builder JSON and run text visible, then passed with 2 tests after remediation; `cd web && npm run test -- features/agents/agent-builder.test.tsx lib/worlds/client.test.ts` passed with 37 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed; full `cd web && npm run test` passed with 52 files and 190 tests; `cd web && npm run build` passed; `cd web && npm run test:e2e` passed with 21 tests, with `next-env.d.ts` restored and `cd web && npm run check:next-env` passing afterward. OpenSpec strict validations and `git diff --check` passed after docs update.


### F-100 Web preset admin panels expose dirty sensitive preset evidence

- Severity: High
- Affected boundary: Web platform preset admin rendering and submit handling for preset behavior policy, calendar blueprint entries/metadata, and advanced config.
- Evidence: `web/features/admin/preset-admin.tsx` renders existing preset `behavior_policy`, `calendar_blueprint`, and `advanced_config` through direct `JSON.stringify(...)`, and parses create/update JSON form submissions with raw `jsonObject(...)` or `JSON.parse(...)`. Dirty legacy/API data or user-edited values with `clientSecret`, `bearerToken`, `rawPrompt`, `storageUri`, `promptSnapshotId`, filesystem paths, bytes, or base64 markers can be displayed in editable preset panels and echoed back through create/update helpers.
- Impact: an authorized platform admin browser can expose resolved secrets, storage/path evidence, raw prompt/output labels, or prompt snapshot references in reusable agent preset templates, and later saves can propagate dirty fields into future agent materialization or world composition flows.
- Intended remediation: add normalized preset JSON display and submit sanitization for behavior policy, calendar blueprint, and advanced config; preserve safe preset behavior, calendar, metadata, and operational fields; add Web regression coverage for dirty preset admin panels and submit payloads.
- Status: Remediated in Web preset admin JSON normalization batch.
- Verification: `cd web && npm run test -- features/admin/preset-admin.test.tsx` first failed against the unpatched component with dirty preset JSON visible in editable textareas, then passed with 4 tests after remediation; `cd web && npm run test -- features/admin/preset-admin.test.tsx lib/worlds/client.test.ts` passed with 39 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed; full `cd web && npm run test` passed with 52 files and 191 tests; `cd web && npm run build` passed; `cd web && npm run test:e2e` passed with 21 tests, with `next-env.d.ts` restored and `cd web && npm run check:next-env` passing afterward. OpenSpec strict validations and `git diff --check` passed after docs update.


### F-101 Web world overview panels expose dirty sensitive world evidence

- Severity: High
- Affected boundary: Web world overview rendering and submit handling for world memory/rules plugin config, world bible JSON, release profile policies/checklists/metadata, world composition rules config, and event payload summaries.
- Evidence: `web/features/worlds/world-overview.tsx` renders `memory_plugin_config`, `world_rules_plugin_config`, world bible JSON fields, release profile policy/checklist/metadata fields, composition `rules_config`, and event audit payload summaries through direct `JSON.stringify(...)`, and parses matching form submissions with raw `jsonObject(...)`, `jsonObjectArray(...)`, or `JSON.parse(...)`. Dirty legacy/API data or user-edited values with `clientSecret`, `bearerToken`, `rawPrompt`, `storageUri`, `promptSnapshotId`, filesystem paths, bytes, or base64 markers can be displayed in editable overview panels, compact event rows, and echoed back through update/validate/import helpers.
- Impact: an authorized admin browser can expose resolved secrets, storage/path evidence, raw prompt/output labels, or prompt snapshot references on the central world overview page, and later saves/import validations can propagate dirty fields into world configuration, continuity, release, or composition flows.
- Intended remediation: add normalized world-overview JSON display and submit sanitization for the affected world config, world bible, release profile, composition rules, and event payload surfaces; preserve safe world configuration, continuity, release policy, composition, and event audit fields; add Web regression coverage for dirty world-overview panels, event summaries, and submit payloads.
- Status: Remediated in Web world overview JSON normalization batch.
- Verification: `cd web && npm run test -- features/worlds/world-overview.test.tsx` first failed against the unpatched component with dirty world overview JSON/event payload visible, then passed with 5 tests after remediation; `cd web && npm run test -- features/worlds/world-overview.test.tsx lib/worlds/client.test.ts` passed with 40 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed; full `cd web && npm run test` passed with 52 files and 192 tests; `cd web && npm run build` passed; `cd web && npm run test:e2e` passed with 21 tests, with `next-env.d.ts` restored and `cd web && npm run check:next-env` passing afterward. OpenSpec strict validations and `git diff --check` passed after docs update.


### F-102 Web narrative surfaces expose dirty sensitive writer and artifact evidence

- Severity: High
- Affected boundary: Web conversation detail writer config rendering/submit handling and reader-facing narrative artifact metadata rendering.
- Evidence: `web/features/conversations/conversation-detail.tsx` renders `conversation.writer_config.writer_plugin_config` through direct `JSON.stringify(...)` and submits it with raw `jsonObject(...)`; `web/features/worlds/narrative-reader.tsx` renders reader-visible `artifact.metadata` through direct `JSON.stringify(...)`. Dirty legacy/API data or user-edited values with `clientSecret`, `bearerToken`, `rawPrompt`, `storageUri`, `promptSnapshotId`, filesystem paths, bytes, or base64 markers can be displayed in admin writer config panels, echoed back through writer config updates, and exposed to ordinary readers through published artifact metadata.
- Impact: an authorized admin browser can expose and resubmit narrative writer secrets or prompt/storage evidence, while published reader artifact pages can leak internal prompt/storage/provider evidence beyond admin-only surfaces.
- Intended remediation: add normalized narrative JSON display and submit sanitization for conversation writer config and reader artifact metadata; preserve safe writer options and safe reader metadata; add Web regression coverage for dirty conversation writer config and reader artifact metadata.
- Status: Remediated in Web narrative JSON normalization batch.
- Verification: `cd web && npm run test -- features/conversations/conversation-detail.test.tsx features/worlds/narrative-reader.test.tsx` first failed against the unpatched components with dirty writer config and reader metadata visible, then passed with 10 tests after remediation; `cd web && npm run test -- features/conversations/conversation-detail.test.tsx features/worlds/narrative-reader.test.tsx lib/worlds/client.test.ts` passed with 45 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed; full `cd web && npm run test` passed with 52 files and 194 tests; `cd web && npm run build` passed; an initial `cd web && npm run test:e2e` hit an unrelated agent-create navigation timeout after 11 tests passed, then the immediate rerun passed with 21 tests, with `next-env.d.ts` restored and `cd web && npm run check:next-env` passing afterward. OpenSpec strict validations and `git diff --check` passed after docs update.


### F-103 Web provider profile admin exposes dirty provider plugin and capability evidence

- Severity: High
- Affected boundary: Web platform provider profile admin rendering and submit handling for provider plugin config schema fields, raw plugin config JSON, and provider capabilities JSON.
- Evidence: `web/features/admin/provider-admin.tsx` parses create/update `plugin_config` and `capabilities` with raw `jsonObject(...)`, renders profile capabilities through direct `JSON.stringify(...)`, and delegates plugin config display to `web/features/plugins/plugin-config-fields.tsx`, which renders raw schema-derived values and raw JSON fallback through direct `String(...)`/`JSON.stringify(...)`. Dirty legacy/API data or user-edited values with `clientSecret`, `bearerToken`, `rawPrompt`, `storageUri`, `promptSnapshotId`, local model paths, filesystem paths, bytes, or base64 markers can be displayed in provider profile admin panels and echoed back through create/update helpers.
- Impact: an authorized platform admin browser can expose resolved provider secrets, prompt/storage/path evidence, or local model references in the legacy provider profile console and can resubmit dirty plugin/capability JSON despite the provider admin JSON normalization contract.
- Intended remediation: add normalized provider profile JSON display and submit sanitization for provider plugin config and capabilities; preserve safe provider plugin options and safe capability fields; add Web regression coverage for dirty provider profile plugin config/capabilities display and submit payloads.
- Status: Remediated in Web provider profile admin JSON normalization batch.
- Verification: `cd web && npm run test -- features/admin/provider-admin.test.tsx` first failed against the unpatched component with dirty provider plugin config and capabilities visible, then passed with 2 tests after remediation; `cd web && npm run test -- features/admin/provider-admin.test.tsx lib/worlds/client.test.ts` passed with 37 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed; full `cd web && npm run test` passed with 52 files and 195 tests; `cd web && npm run build` passed; `cd web && npm run test:e2e` passed with 21 tests, with `next-env.d.ts` restored and `cd web && npm run check:next-env` passing afterward. OpenSpec strict validations and `git diff --check` passed after docs update.


### F-104 Web visual resolver previews omit CSRF headers

- Severity: High
- Affected boundary: Web visual admin client helpers for sprite/background resolver preview POST requests.
- Evidence: `web/lib/worlds/visual.ts` calls `adminRequest(..., { method: "POST", body: input })` for `resolveSprite` and `resolveBackground` without `csrf: true`, while adjacent visual create/update/delete and compose-scene POST helpers require CSRF. Existing coverage in `web/lib/worlds/visual.test.ts` explicitly expected resolver previews to omit the `X-CSRF-Token` header.
- Impact: authenticated browser-side visual resolver POST routes are inconsistent with the double-submit CSRF boundary used by other admin POST/PATCH/PUT/DELETE actions, weakening defense-in-depth for admin-only visual preview endpoints and causing backend CSRF enforcement to fail once consistently applied.
- Intended remediation: require CSRF on visual resolver preview POST helpers, update regression coverage to assert resolver and compose-scene requests all carry the CSRF header, and keep encoded visual path/query behavior intact.
- Status: Remediated in Web visual resolver CSRF batch.
- Verification: `cd web && npm run test -- lib/worlds/visual.test.ts` first failed against the unpatched helpers with resolver preview requests missing `X-CSRF-Token`, then passed with 4 tests after remediation; `cd web && npm run test -- lib/worlds/visual.test.ts lib/admin/api-client.test.ts lib/worlds/proxy.test.ts` passed with 13 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed; full `cd web && npm run test` passed with 52 files and 195 tests; `cd web && npm run build` passed; `cd web && npm run test:e2e` passed with 21 tests, with `next-env.d.ts` restored and `cd web && npm run check:next-env` passing afterward. OpenSpec strict validations and `git diff --check` passed after docs update.


### F-105 Web agent memory search omits CSRF header

- Severity: High
- Affected boundary: Web world client helper for agent memory search POST requests.
- Evidence: `web/lib/worlds/client.ts` calls `worldRequest(..., { method: "POST", body: input })` for `searchAgentMemory` without `csrf: true`, while adjacent agent memory profile refresh/forget, persona validation/update, observation refresh/create, manual run, narrative publish/unpublish, and agent update/deactivate POST/PATCH/DELETE helpers require CSRF. Existing coverage in `web/lib/worlds/client.test.ts` checked the `memory/search` body and URL but did not assert the CSRF header.
- Impact: authenticated browser-side agent memory search POST routes are inconsistent with the double-submit CSRF boundary used by other world-scoped POST/PATCH/PUT/DELETE helpers, weakening defense-in-depth and risking backend CSRF enforcement failures for a request-body world-admin/member API.
- Intended remediation: require CSRF on the agent memory search POST helper, update regression coverage to assert the `memory/search` request carries `X-CSRF-Token`, and keep encoded world/agent path behavior intact.
- Status: Remediated in Web agent memory search CSRF batch.
- Verification: `cd web && npm run test -- lib/worlds/client.test.ts` first failed against the unpatched helper with `memory/search` missing `X-CSRF-Token`, then passed with 35 tests after remediation; `cd web && npm run test -- lib/worlds/client.test.ts lib/worlds/proxy.test.ts lib/admin/api-client.test.ts` passed with 44 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed; full `cd web && npm run test` passed with 52 files and 195 tests; `cd web && npm run build` passed; `cd web && npm run test:e2e` passed with 21 tests, with `next-env.d.ts` restored and `cd web && npm run check:next-env` passing afterward. OpenSpec strict validations and `git diff --check` passed after docs update.

### F-106 Web API client error detail can surface backend internals

- Severity: High
- Affected boundary: browser-side admin/world/media/private-beta/beta-feedback error notices and backend detail response handling.
- Evidence: `web/lib/admin/api-client.ts`, `web/lib/worlds/client.ts`, `web/lib/worlds/media.ts`, `web/lib/private-beta/client.ts`, and `web/lib/beta-feedback/client.ts` parse backend JSON `detail` / `detail.message` and throw client errors with that raw string. Workspace form handling and feature notices display those error messages to admins, members, players, or beta users. Dirty backend details containing `storageUri`, `media://`, `/tmp` or `/var` paths, `/models` local model paths, `rawPrompt`, `rawOutput`, `promptSnapshotId`, `clientSecret`, `Bearer ...`, `sk-*`, bytes, or base64-like evidence can therefore be surfaced in browser notices.
- Impact: backend failure details can cross the Web boundary and expose provider secrets, auth tokens, internal storage/object paths, local model paths, prompt evidence, or binary/base64 payload markers to UI users even when the API response body should remain an internal diagnostic.
- Intended remediation: centralize Web backend-error detail normalization, preserve safe business errors and safe publication gate summaries, fall back to route-specific generic errors for sensitive-looking details, and add regression coverage for admin, world, media, private-beta, and beta-feedback clients.
- Status: Remediated in Web backend error detail normalization batch.
- Verification: `cd web && npm run test -- lib/admin/api-client.test.ts lib/worlds/client.test.ts lib/worlds/media.test.ts lib/private-beta/client.test.ts lib/beta-feedback/client.test.ts` first failed with 5 failures against the unpatched clients because raw backend details were preserved, then passed with 53 tests after remediation; `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed; full `cd web && npm run test` passed with 52 files and 200 tests; `cd web && npm run build` passed with `next-env.d.ts` restored and checked; `cd web && npm run test:e2e` passed with 21 tests and `cd web && npm run check:next-env` passed afterward. OpenSpec strict validations and `git diff --check` passed after docs update.

### F-107 Web auth client error detail can surface backend internals

- Severity: High
- Affected boundary: browser-side auth/CSRF client error handling and downstream UI catches of `AuthClientError` as generic `Error` messages.
- Evidence: `web/lib/auth/client.ts` parses backend JSON `detail` and throws `AuthClientError` with that raw string for `/api/auth/csrf`, `/api/auth/login`, and `/api/auth/me`. Login form maps common 401/422 responses to fixed text, but CSRF failures reached through admin/world/private-beta/beta-feedback helpers can be caught by feature-level `messageForError` fallbacks that display `Error.message`. Dirty auth/CSRF backend details containing `storageUri`, `media://`, `/tmp` or `/var` paths, `/models` local model paths, `rawPrompt`, `rawOutput`, `promptSnapshotId`, `clientSecret`, `Bearer ...`, `sk-*`, bytes, or base64-like evidence can therefore surface in browser notices.
- Impact: auth and CSRF preparation failures can leak backend diagnostics, provider secrets, auth tokens, storage/object paths, local model paths, prompt evidence, or binary/base64 payload markers into UI notices despite the Web client error-detail normalization added for other clients.
- Intended remediation: apply the shared Web backend-error detail normalizer to auth client response parsing with each route-specific fallback message, preserve safe credential/business errors, and add regression coverage for dirty auth/CSRF backend details.
- Status: Remediated in Web auth error detail normalization batch.
- Verification: `cd web && npm run test -- lib/auth/client.test.ts` first failed with 1 failure against the unpatched auth client because raw CSRF backend detail was preserved, then passed with 7 tests after remediation; `cd web && npm run test -- lib/auth/client.test.ts lib/admin/api-client.test.ts lib/worlds/client.test.ts lib/worlds/media.test.ts lib/private-beta/client.test.ts lib/beta-feedback/client.test.ts` passed with 60 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed; full `cd web && npm run test` passed with 52 files and 201 tests; `cd web && npm run build` passed with `next-env.d.ts` restored and checked; `cd web && npm run test:e2e` passed with 21 tests and `cd web && npm run check:next-env` passed afterward. OpenSpec strict validations and `git diff --check` passed after docs update.

### F-108 Web server loaders can throw backend detail with internals

- Severity: High
- Affected boundary: server-side Web loaders and Next.js server error/log boundary for worlds and beta feedback data loading.
- Evidence: `web/lib/worlds/server.ts` and `web/lib/beta-feedback/server.ts` parse backend JSON `detail` and construct `WorldServerError` / `BetaFeedbackServerError` with that raw string. Most loader paths convert non-auth failures into fixed `loadError` strings, but `getWorldsIndexData()` rethrows directly and beta feedback/world loaders rethrow 401 errors. Dirty backend details containing `storageUri`, `media://`, `/tmp` or `/var` paths, `/models` local model paths, `rawPrompt`, `rawOutput`, `promptSnapshotId`, `clientSecret`, `Bearer ...`, `sk-*`, bytes, or base64-like evidence can therefore cross into server errors or logs.
- Impact: backend diagnostics, provider secrets, auth tokens, storage/object paths, local model paths, prompt evidence, or binary/base64 payload markers can be preserved in server-side Web error objects even when page-level UI should use generic load errors.
- Intended remediation: apply the shared Web backend-error detail normalizer to server loader error parsing for worlds and beta feedback, preserve fixed page load-error behavior, and add regression coverage for dirty worlds index and beta-feedback 401 backend details.
- Status: Remediated in Web server loader error detail normalization batch.
- Verification: `cd web && npm run test -- lib/worlds/server.test.ts lib/beta-feedback/server.test.ts` first failed with 2 failures against unpatched server loaders because raw backend details were preserved in thrown server errors, then passed with 5 tests after remediation; `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed; full `cd web && npm run test` passed with 52 files and 203 tests; `cd web && npm run build` passed with `next-env.d.ts` restored and checked; `cd web && npm run test:e2e` passed with 21 tests and `cd web && npm run check:next-env` passed afterward. OpenSpec strict validations and `git diff --check` passed after docs update.

### F-109 Web API proxies relay backend JSON error bodies with internals

- Severity: High
- Affected boundary: same-origin Web API proxy network responses for auth, platform admin, world, runtime, and private-beta routes.
- Evidence: `web/lib/auth/proxy.ts` central `buildProxyResponse()` copies safe headers but relays every non-204 backend response body with `await backendResponse.arrayBuffer()`. It is used by auth, generic API, world, runtime, and private-beta proxies. Even after F-106/F-108 normalized UI-visible errors, dirty backend JSON error bodies containing `detail`, `detail.message`, `storageUri`, `media://`, filesystem paths, local model paths, `rawPrompt`, `rawOutput`, `promptSnapshotId`, `clientSecret`, `Bearer ...`, `sk-*`, bytes, or base64-like evidence still reach browser clients in the proxied network response.
- Impact: browser clients and users with devtools access can receive provider secrets, auth tokens, internal storage/object paths, local model paths, prompt evidence, or binary/base64 payload markers in same-origin proxy error responses even when UI code displays a generic message.
- Intended remediation: sanitize non-2xx JSON proxy error bodies centrally in `buildProxyResponse()` before relaying them, preserve successful JSON and binary/no-content responses, preserve auth `Set-Cookie` relay semantics, and add regression coverage for dirty proxied JSON error bodies.
- Status: Remediated in Web proxy JSON error body normalization batch.
- Verification: `cd web && npm run test -- lib/auth/proxy.test.ts` first failed against unpatched `buildProxyResponse()` because raw backend JSON detail was relayed, then passed with 6 tests after remediation; `cd web && npm run test -- lib/auth/proxy.test.ts lib/api-proxy.test.ts lib/worlds/proxy.test.ts lib/runtime/proxy.test.ts lib/private-beta/proxy.test.ts lib/realtime/proxy.test.ts` passed with 6 files and 19 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed; full `cd web && npm run test` passed with 52 files and 205 tests; `cd web && npm run build` passed with `next-env.d.ts` restored and checked; `cd web && npm run test:e2e` passed with 21 tests and `cd web && npm run check:next-env` passed afterward. OpenSpec strict validations and `git diff --check` passed after docs update.

### F-110 Platform admin player-record management routes use world-admin-only role checks

- Severity: Medium
- Affected boundary: backend player journal, in-world notification, and player intervention management semantics for platform admins without direct world membership.
- Evidence: `backend/services/api/src/noveland/services/api/worlds.py` computes management visibility as `context.is_platform_admin or context.role == AuthRole.WORLD_ADMIN.value`, but `list_player_journal()`, `list_notifications()`, `list_interventions()`, and `create_intervention()` use `context.role == AuthRole.WORLD_ADMIN.value` or `!=` checks for cross-user access and all-user listing. `require_world_member()` returns `role=None` for platform admins, so platform admins receive admin-shaped records only for their own user id, cannot list all notifications/interventions, and receive 403 when creating interventions for a world member.
- Impact: platform operators can be denied player-record management workflows that world admins can perform, creating inconsistent incident/support behavior for v1.1 RC player resume, feedback, and intervention operations.
- Intended remediation: centralize the manage-world predicate for these player-record routes, use it for cross-user checks and all-user queries, preserve member-only restrictions and member-safe DTO shaping, and add regression coverage for platform-admin cross-user journal/notification/intervention management.
- Status: Remediated in platform-admin player-record management batch.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_platform_admin_manages_player_records_without_world_membership -q` first failed with a 403 on platform-admin cross-user player journal access, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_worlds.py::test_knowledge_player_guardrail_apis_and_acceptance_gap_fixes tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope tests/test_api_permission_matrix.py -q` passed with 5 tests; focused `cd backend && uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` and `cd backend && uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 573 tests and 8 skipped. OpenSpec strict validations and `git diff --check` passed after docs update.

### F-111 Agent memory search/delete validate worldline after backend boundary

- Severity: Medium
- Affected boundary: backend worldline isolation and memory backend/provider execution boundary.
- Evidence: `backend/packages/memory/src/noveland/memory/service.py` validates explicit `worldline_id` before `list_memories()` reaches the backend, but `search()` calls `self._backend_for_scope(request.world_id).search(request)` before `self._worldline_id(request.world_id, request.worldline_id)`, and `delete_scope()` calls `backend.delete_scope(scope)` before resolving the requested worldline for local scrubbing. For external memory backends this lets invalid or cross-world `worldline_id` values reach the backend call path before local world ownership validation, and can then surface as an unhandled validation error after the backend returns.
- Impact: invalid or cross-world memory scopes can cross the memory backend/provider boundary before the API rejects them, weakening the worldline isolation contract and creating inconsistent error behavior for agent memory search/forget flows.
- Intended remediation: resolve and validate memory worldline scope before backend search/delete calls, pass the resolved worldline into backend requests/scopes, preserve valid primary-worldline compatibility behavior, and add regression coverage proving invalid worldlines do not trigger backend search/delete calls.
- Status: Remediated in agent-memory worldline validation batch.
- Verification: `cd backend && uv run pytest tests/test_memory_backend.py::test_memory_service_rejects_invalid_worldline_before_backend_search_or_delete -q` first failed with `backend.search_calls == 1`, proving invalid cross-world worldline search reached the backend spy before validation, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_worlds.py::test_world_admin_manages_agent_memory tests/test_memory_backend.py::test_memory_service_rejects_invalid_worldline_before_backend_search_or_delete -q` passed with 2 tests; `cd backend && uv run pytest tests/test_memory_backend.py -q` passed with 17 tests; focused `cd backend && uv run ruff check packages/memory/src/noveland/memory/service.py tests/test_memory_backend.py services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` and `cd backend && uv run mypy packages/memory/src/noveland/memory/service.py tests/test_memory_backend.py services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 574 tests and 8 skipped. OpenSpec strict validations and `git diff --check` passed after docs update.

### F-112 Agent memory read routes mishandle invalid worldline scope

- Severity: Medium
- Affected boundary: backend worldline isolation and agent memory API error semantics.
- Evidence: CLI reproduction after F-111 showed cross-world `worldline_id` on `GET /worlds/{world_id}/agents/{agent_id}/memory` returns `200 []` because `MemoryService.list_memories()` catches `MemoryValidationError`, while cross-world `worldline_id` on `GET /memory/profile-snapshot` and `POST /memory/profile-snapshot/refresh` raises an unhandled `MemoryValidationError`. Search and forget already return 422 after F-111.
- Impact: invalid or cross-world memory read/profile scopes can be mistaken for empty valid data or become server errors, weakening worldline isolation observability and creating inconsistent operator behavior across adjacent agent memory routes.
- Intended remediation: resolve and validate memory worldline scope before backend list calls, let validation errors propagate to the API layer, map list/profile/refresh validation failures to 422 responses, preserve valid primary/fork behavior, and add regression coverage for all agent memory worldline routes.
- Status: Remediated in agent-memory read-route worldline validation batch.
- Verification: `cd backend && uv run pytest tests/test_memory_backend.py::test_memory_service_rejects_invalid_worldline_before_backend_search_or_delete tests/test_api_worlds.py::test_world_admin_manages_agent_memory -q` first failed with `DID NOT RAISE MemoryValidationError` for invalid list scope and an unhandled `MemoryValidationError` on profile-snapshot, then passed with 2 tests after remediation; `cd backend && uv run pytest tests/test_memory_backend.py -q` passed with 17 tests; focused `cd backend && uv run ruff check packages/memory/src/noveland/memory/service.py tests/test_memory_backend.py services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` and matching mypy command passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 574 tests and 8 skipped. OpenSpec strict validations and `git diff --check` passed after docs update.

### F-113 Player privacy request list accepts cross-world worldline as empty scope

- Severity: Medium
- Affected boundary: backend player privacy worldline isolation and member/admin privacy request list semantics.
- Evidence: CLI reproduction showed `GET /worlds/{world_id}/player/privacy/export?worldline_id={other_worldline_id}` returns 404 through `PlayerPrivacyService._resolve_worldline_id()`, but adjacent `GET /worlds/{world_id}/player/privacy/requests?worldline_id={other_worldline_id}` returns `200 []` because `PlayerPrivacyService.list_requests()` filters by the supplied UUID without validating that it belongs to the requested world.
- Impact: invalid or cross-world player privacy request scopes are silently treated as empty valid data, creating inconsistent privacy workflow behavior and weakening worldline isolation observability for member/admin request lists.
- Intended remediation: validate and resolve explicit `worldline_id` in `PlayerPrivacyService.list_requests()` before applying the filter, preserve existing export/delete/review behavior, and add API regression coverage that cross-world privacy request list queries are rejected like privacy export queries.
- Status: Remediated in player-privacy request-list worldline validation batch.
- Verification: `cd backend && uv run pytest tests/test_api_player_privacy.py::test_player_privacy_rejects_cross_worldline_requests -q` first failed because cross-world privacy request list returned `200`, then failed with an unhandled `PlayerPrivacyNotFoundError` after service-level validation was added, and finally passed with 1 test after API error mapping; `cd backend && uv run pytest tests/test_api_player_privacy.py -q` passed with 3 tests; focused `cd backend && uv run ruff check packages/player_privacy/src/noveland/player_privacy/service.py services/api/src/noveland/services/api/player_privacy.py tests/test_api_player_privacy.py` and matching mypy command passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 574 tests and 8 skipped. OpenSpec strict validations and `git diff --check` passed after docs update.

### F-114 Reader media list accepts cross-world worldline as empty scope

- Severity: Medium
- Affected boundary: backend reader media worldline isolation and member-readable media list semantics.
- Evidence: Read-only audit of `backend/packages/reader_delivery/src/noveland/reader_delivery/service.py` showed `list_media()` filters directly on `MediaAsset.worldline_id == worldline_id` without validating the worldline belongs to the requested world. Existing reader media tests cover wrong-world assets and same-world wrong-worldline detail/download requests, but not list queries with a worldline UUID from another world.
- Impact: invalid or cross-world reader media list scopes can be silently treated as empty valid data, weakening worldline isolation observability and creating inconsistent behavior with reader media detail/download routes.
- Intended remediation: validate explicit reader media worldline scopes before list/detail/download filtering, map invalid scopes to the existing reader media 404 response, preserve valid list/detail/download behavior, and add regression coverage for cross-world worldline list rejection.
- Status: Remediated in reader-media worldline validation batch.
- Verification: `cd backend && uv run pytest tests/test_api_reader_media.py::test_reader_media_rejects_cross_world_and_cross_worldline_requests -q` first failed before remediation because cross-world reader media list returned `200`, then passed with 1 test after service/API validation; `cd backend && uv run pytest tests/test_api_reader_media.py -q` passed with 5 tests; focused `cd backend && uv run ruff check packages/reader_delivery/src/noveland/reader_delivery/service.py services/api/src/noveland/services/api/reader_media.py tests/test_api_reader_media.py` and matching mypy command passed after ruff fixed import ordering. Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 574 tests and 8 skipped. OpenSpec strict validations and `git diff --check` passed after docs update.


### F-115 Speech list routes surface invalid worldline as unhandled service error

- Severity: Medium
- Affected boundary: backend speech admin API worldline isolation and handled error semantics.
- Evidence: Temporary CLI reproduction using the existing `backend/tests/test_api_speech.py` in-memory fixtures showed cross-world `worldline_id` queries against `GET /worlds/{world_id}/speech/voice-profiles` and `GET /worlds/{world_id}/agents/{agent_id}/voice-profiles` raise uncaught `SpeechValidationError`, while `GET /worlds/{world_id}/speech/transcripts` raises uncaught `SpeechNotFoundError`.
- Impact: invalid or cross-world speech list scopes can become server errors instead of explicit client errors, weakening worldline isolation observability and creating inconsistent behavior with speech create/update operations that already map service validation failures.
- Intended remediation: catch speech service worldline validation/not-found failures in speech list API routes, map invalid explicit worldline scopes to existing handled client errors, preserve valid list behavior and platform-admin visibility filtering, and add regression coverage for cross-world voice profile, agent binding, and transcript list requests.
- Status: Remediated in speech list worldline validation batch.
- Verification: Temporary CLI reproduction first showed cross-world speech list scopes raising uncaught `SpeechValidationError` for voice profile and agent binding lists and uncaught `SpeechNotFoundError` for transcript lists; `cd backend && uv run pytest tests/test_api_speech.py::test_speech_lists_reject_cross_worldline_requests -q` first failed with the uncaught `SpeechValidationError`, then passed with 1 test after API error mapping; `cd backend && uv run pytest tests/test_api_speech.py -q` passed with 2 tests; focused `cd backend && uv run ruff check services/api/src/noveland/services/api/speech.py tests/test_api_speech.py` and matching mypy command passed. Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 575 tests and 8 skipped. OpenSpec strict validations and `git diff --check` passed after docs update.


### F-116 Visual generation model asset list surfaces invalid worldline as unhandled service error

- Severity: Medium
- Affected boundary: backend visual generation admin API worldline isolation and handled error semantics.
- Evidence: Temporary CLI reproduction using the existing `backend/tests/test_api_visual_generation.py` in-memory fixtures showed `GET /worlds/{world_id}/visual-generation/model-assets?worldline_id={other_worldline_id}` raises uncaught `VisualGenerationValidationError`, while the same route with a valid same-worldline `worldline_id` returns model assets normally.
- Impact: invalid or cross-world visual generation model-asset list scopes can become server errors instead of explicit client errors, weakening worldline isolation observability and creating inconsistent behavior with adjacent visual generation list routes that already map validation failures.
- Intended remediation: catch visual generation service worldline validation failures in the model asset list API route, map invalid explicit worldline scopes to existing handled client errors, preserve valid model asset list behavior and platform-admin visibility filtering, and add regression coverage for cross-world model asset list requests.
- Status: Remediated in visual-generation model-asset worldline validation batch.
- Verification: Temporary CLI reproduction first showed cross-world visual generation model-asset list scope raising uncaught `VisualGenerationValidationError`; `cd backend && uv run pytest tests/test_api_visual_generation.py::test_visual_generation_model_assets_reject_cross_worldline_requests -q` first failed with the uncaught `VisualGenerationValidationError`, then passed with 1 test after API error mapping; `cd backend && uv run pytest tests/test_api_visual_generation.py -q` passed with 5 tests; focused `cd backend && uv run ruff check services/api/src/noveland/services/api/visual_generation.py tests/test_api_visual_generation.py` and matching mypy command passed. Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 576 tests and 8 skipped. OpenSpec strict validations and `git diff --check` passed after docs update.


### F-117 Media asset detail surfaces invalid worldline as unhandled service error

- Severity: Medium
- Affected boundary: backend media member/admin API worldline isolation and handled error semantics.
- Evidence: Temporary CLI reproduction using the existing `backend/tests/test_api_media.py` in-memory fixtures showed `GET /worlds/{world_id}/media/assets/{asset_id}?worldline_id={other_worldline_id}` raises uncaught `MediaValidationError`, while the same route with a valid same-worldline `worldline_id` returns the asset normally.
- Impact: invalid or cross-world media asset detail scopes can become server errors instead of explicit client errors, weakening worldline isolation observability and creating inconsistent behavior with adjacent media asset list/search routes that already map validation failures.
- Intended remediation: catch media service worldline validation failures in the media asset detail API route, map invalid explicit worldline scopes to existing handled client errors, preserve valid detail behavior and member/admin response shaping, and add regression coverage for cross-world media asset detail requests.
- Status: Remediated in media asset detail worldline validation batch.
- Verification: Temporary CLI reproduction first showed cross-world media asset detail scope raising uncaught `MediaValidationError`; `cd backend && uv run pytest tests/test_api_media.py::test_media_asset_detail_rejects_cross_worldline_requests -q` first failed with the uncaught `MediaValidationError`, then passed with 1 test after API error mapping; `cd backend && uv run pytest tests/test_api_media.py -q` passed with 10 tests; focused `cd backend && uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py` and matching mypy command passed. Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 577 tests and 8 skipped. OpenSpec strict validations and `git diff --check` passed after docs update.


### F-118 Observability readiness routes surface invalid worldline as unhandled service error

- Severity: Medium
- Affected boundary: backend platform-admin observability readiness API worldline isolation and handled error semantics.
- Evidence: Temporary CLI reproduction using the existing `backend/tests/test_production_readiness_gate.py` in-memory fixtures showed `GET /observability/readiness/self-use-mvp?world_id={world_id}&worldline_id={other_worldline_id}` raises uncaught `ValueError` from `worldline_or_404()`, while the same route with a valid same-worldline `worldline_id` returns a readiness report normally. The adjacent private-beta setup, private-beta, and release-candidate readiness routes call the same service-level worldline resolution pattern.
- Impact: invalid or cross-world readiness scopes can become server errors instead of explicit client errors, weakening worldline isolation observability for platform-admin RC checks and creating inconsistent behavior with adjacent admin APIs that already map invalid worldline scopes.
- Intended remediation: catch readiness service worldline validation failures in the self-use, private-beta setup, private-beta, and release-candidate API routes, map invalid explicit worldline scopes to handled client errors, preserve valid readiness aggregation behavior, and add endpoint regression coverage for cross-world readiness requests.
- Status: Remediated in observability readiness worldline validation batch.
- Verification: Temporary CLI reproduction first showed cross-world self-use readiness scope raising uncaught `ValueError`; `cd backend && uv run pytest tests/test_production_readiness_gate.py::test_readiness_endpoints_reject_cross_worldline_requests -q` first failed with the uncaught `ValueError`, then passed with 1 test after API error mapping; `cd backend && uv run pytest tests/test_production_readiness_gate.py -q` passed with 28 tests; focused `cd backend && uv run ruff check services/api/src/noveland/services/api/observability.py tests/test_production_readiness_gate.py` and matching mypy command passed after adding a test-local type annotation. Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 578 tests and 8 skipped. OpenSpec strict validations and `git diff --check` passed after docs update.

### F-119 Player resume treats cross-worldline presentation media as ready

- Severity: Medium
- Affected boundary: backend player session recovery, worldline isolation, and player-safe media fallback semantics.
- Evidence: Temporary CLI reproduction using `backend/tests/test_api_player_sessions.py` fixtures showed a presentation in the active player session worldline can point `composite_scene_asset_id` at an `available`/`player_visible` media asset from a sibling worldline, and `POST /worlds/{world_id}/player-sessions/resume` still returns `recovery_status=ready` with `open_reader_playback`.
- Impact: player resume can advertise playback as ready even when the referenced presentation media is outside the session worldline and will not be reader-deliverable for that player context, producing an unsafe normal-use recovery state and weakening media/worldline consistency checks.
- Intended remediation: validate presentation media assets against the player session world and worldline during recovery-state calculation, treat missing, hidden, deleted, cross-world, or cross-worldline media as `missing_media`, preserve failed-media detection for in-scope assets, and add regression coverage for cross-worldline presentation media pointers.
- Status: Remediated in player-session media worldline recovery batch.
- Verification: `cd backend && uv run pytest tests/test_api_player_sessions.py::test_player_session_validates_references_and_safe_fallbacks -q` first failed because cross-worldline presentation media returned `recovery_status=ready`, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_player_sessions.py -q` passed with 3 tests; focused backend ruff/mypy passed for player session service and tests. Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 578 tests and 8 skipped. OpenSpec strict validations and `git diff --check` passed after docs update.

### F-120 Player resume treats private presentation media as ready

- Severity: Medium
- Affected boundary: backend player session recovery, media visibility enforcement, and player-safe playback semantics.
- Evidence: Temporary CLI reproduction using `backend/tests/test_api_player_sessions.py` fixtures showed a presentation in the active player session worldline can point `composite_scene_asset_id` at an `available` media asset with `visibility=private`, and `POST /worlds/{world_id}/player-sessions/resume` still returns `recovery_status=ready` with `open_reader_playback`.
- Impact: player resume can advertise playback as ready for media that Reader Media Delivery will not serve to members/players, causing unsafe normal-use recovery state and weakening player/admin media visibility separation.
- Intended remediation: restrict player resume media readiness to player/member/reader deliverable visibilities, treat private/admin-only/developer-only/hidden/deleted media as `missing_media`, preserve failed-media detection for in-scope deliverable media, and add regression coverage for private/admin-only presentation media pointers.
- Status: Remediated in player-session media visibility recovery batch.
- Verification: `cd backend && uv run pytest tests/test_api_player_sessions.py::test_player_session_private_and_admin_only_media_are_missing_media -q` first failed because private presentation media returned `recovery_status=ready`, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_player_sessions.py::test_player_session_private_and_admin_only_media_are_missing_media tests/test_api_player_sessions.py::test_player_session_validates_references_and_safe_fallbacks -q` passed with 2 tests; `cd backend && uv run pytest tests/test_api_player_sessions.py -q` passed with 4 tests; focused backend ruff/mypy passed for player session service and tests. Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 579 tests and 8 skipped. OpenSpec strict validations and `git diff --check` passed after docs update.


### F-121 Web dashboard renders runtime/provider sensitive status text

- Severity: Medium
- Affected boundary: Web dashboard rendering of platform-admin runtime and provider operational evidence.
- Evidence: Read-only audit showed `web/features/dashboard/world-management-dashboard.tsx` sanitizes dashboard JSON panels but directly renders `runtimeControl.last_error`, runtime/world diagnostic `message`/`component`/`event_type`, and provider profile `last_test_error`. These fields can contain provider errors, storage URI/path evidence, raw prompt/output markers, prompt snapshot identifiers, tokens, or base64-like payload fragments that adjacent runtime admin surfaces already redact before rendering.
- Impact: platform-admin dashboard views can expose sensitive runtime/provider evidence in browser-rendered text, violating the Web redaction contract even when JSON panels are safe.
- Intended remediation: reuse the existing dashboard sensitive-text detection for runtime/provider status text, preserve safe labels and status values, and add Web regression coverage for the affected dashboard text fields.
- Status: Remediated in Web dashboard runtime/provider status text redaction batch.
- Verification: `cd web && npm run test -- features/dashboard/world-management-dashboard.test.tsx` first failed because runtime/provider sensitive status text rendered into the document, then passed with 8 tests after remediation; `cd web && npm run typecheck -- --pretty false` passed; `cd web && npm run lint -- features/dashboard/world-management-dashboard.tsx features/dashboard/world-management-dashboard.test.tsx` passed via the project lint script; full `cd web && npm run test` passed with 52 test files and 206 tests. OpenSpec strict validations and `git diff --check` passed before docs update.
