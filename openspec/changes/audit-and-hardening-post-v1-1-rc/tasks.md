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

- [ ] 4.1 Audit Next route handlers and API proxies for CSRF, auth forwarding, role boundary, evidence redaction, and client-side leaks.
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
