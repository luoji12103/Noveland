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
