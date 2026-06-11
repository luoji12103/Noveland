# Active Session Handoff

- Date: 2026-06-12T03:55:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-056 are remediated on this branch.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-056 commit: 9a71684 fix(auth): require csrf for login.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services: Noveland Postgres is healthy on 55432->5432; Noveland NATS is healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started for this batch.
- Only .env.example was observed in the repo; do not read or expose real secrets.

## Guardrails

- Current user instruction: use SSH/CLI only; avoid browser/computer-use plugins and other non-CLI tooling that may interrupt the session.
- Current user instruction: after each completed commit, push it to the configured remote; do not commit or push unfinished work.
- Do not bypass OpenSpec; add or update spec deltas before behavior-changing fixes.
- Keep real-provider tests opt-in only; do not set NOVELAND_RUN_REAL_PROVIDER_TESTS=1 without explicit user authorization.
- Preserve provider execution through ProviderExecutionService, quota-before-adapter execution, secret redaction, invocation ledger boundaries, media boundaries, worldline isolation, and reader/member/player DTO safety.
- Do not expose resolved secrets, disallowed auth refs, storage URIs, filesystem/object paths, local model paths, raw prompts, raw outputs, prompt snapshot internals, invite tokens, bytes, or base64.
- Do not broaden worlds.py into a catch-all router.
- For UI/e2e use project Playwright/e2e only.

## Completed This Batch

- Reconfirmed realtime git/OpenSpec/service/test-entry status from the server before editing.
- Continued backend/Web security audit after F-055 across Next routes, low-privilege DTOs, CSRF coverage, realtime streams, provider/runtime profiles, and memory backend secret boundaries.
- Recorded and remediated F-056: memory backend profile config and `secret_refs` could persist raw secret material and then return it through platform runtime APIs/Web admin form state.
- Added an architecture-contracts OpenSpec delta requiring memory backend profile config to reject raw secret material and keep `secret_refs` as runtime secret lookup references.
- Added memory service validation for sensitive config keys, raw-secret-looking config values, non-empty single secret reference names, and raw-secret-looking `secret_refs` values.
- Added memory service and runtime API regression coverage for rejecting direct `api_key` config and raw secret refs while preserving safe reference names.

## Verification This Batch

- `cd backend && uv run pytest tests/test_memory_backend.py::test_memory_backend_profile_rejects_raw_secret_material tests/test_api_runtime.py::test_memory_backend_profile_api_rejects_raw_secret_material`: 2 passed.
- `cd backend && uv run pytest tests/test_memory_backend.py tests/test_api_runtime.py`: 26 passed.
- `cd backend && uv run ruff check .`: passed.
- `cd backend && uv run mypy .`: passed.
- `cd backend && uv run pytest`: 563 passed, 8 skipped.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`: passed.
- `openspec validate --changes --strict`: passed with 1 passed.
- `openspec validate --specs --strict`: passed with 76 specs.
- `git diff --check`: passed.

## Remaining Work

1. Continue Web/e2e security audit on remaining Next route handlers and proxy modules for method exposure, response shaping beyond cookies, role boundary, evidence redaction, and client-side data leaks.
2. Audit Web rendering and project Playwright/e2e coverage for XSS-prone sinks, admin/player/member boundary gaps, and normal-use product flow drift without browser/computer-use plugins.
3. Continue product normal-use and spec/history drift audit after Web route/proxy review.

## Finding F-056

- Memory backend profile config accepted direct secret-bearing keys/values and `secret_refs` accepted obvious raw secret values before persistence.
- The remediation rejects raw secret material at the memory service boundary before database writes while preserving safe reference names used for `NOVELAND_MEMORY_BACKEND_SECRETS_JSON` lookup.
- Residual risk: remaining Web admin/client helper sharp edges, response error shaping, and client-rendering sinks still need separate evidence-based review before remediation.
