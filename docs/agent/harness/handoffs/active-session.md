# Active Session Handoff

- Date: 2026-06-12T08:20:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-066 are remediated on this branch; latest batch is F-066 speech TTS/STT safe response shaping.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-066 batch: 8307adf fix(observability): redact diagnostic text values.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services at F-066 batch start: Noveland Postgres was healthy on 55432->5432; Noveland NATS was healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started for this batch.
- Only .env.example was observed in the repo; do not read or expose real secrets.

## Guardrails

- Current user instruction: use SSH/CLI only; avoid browser/computer-use plugins and other non-CLI tooling that may interrupt the session.
- Current goal instruction: do not push unless explicitly requested.
- Do not bypass OpenSpec; add or update spec deltas before behavior-changing fixes.
- Keep real-provider tests opt-in only; do not set NOVELAND_RUN_REAL_PROVIDER_TESTS=1 without explicit user authorization.
- Preserve provider execution through ProviderExecutionService, quota-before-adapter execution, secret redaction, invocation ledger boundaries, media boundaries, worldline isolation, and reader/member/player DTO safety.
- Do not expose resolved secrets, disallowed auth refs, storage URIs, filesystem/object paths, local model paths, raw prompts, raw outputs, prompt snapshot internals, invite tokens, bytes, or base64.
- Do not broaden worlds.py into a catch-all router.
- For UI/e2e use project Playwright/e2e only.

## Completed This Batch

- Reconfirmed realtime server state: branch `feature/audit-and-hardening-post-v1-1-rc`, clean worktree at start, local branch ahead of origin by F-065 only, active OpenSpec change valid, Postgres/NATS healthy.
- Continued backend forbidden-evidence audit across speech APIs. Speech management routes are world-admin scoped and provider calls go through `ProviderExecutionService`; voice profile worldline media reference validation from F-063 remains in place.
- Recorded/remediated F-066: speech TTS/STT test action responses returned raw `MediaAssetRecord`/`MediaObjectRecord`/`InvocationRecordView` DTOs, exposing `media://` storage URIs and raw invocation text in the immediate speech admin response.
- Added a speech-admin-console OpenSpec scenario requiring speech test responses to omit storage locators, raw provider request/output payloads, resolved secrets, bytes, and base64 while preserving safe operator follow-up IDs and metadata.
- Added speech-specific safe API response DTOs for TTS/STT results and shaped responses at the API layer without changing speech service persistence, provider execution, media storage, or invocation ledger records.
- Expanded the speech API test to assert TTS/STT responses do not contain `storage_uri`, `media://`, job request/result/config fields, or raw invocation payload fields.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_speech.py -q` passed with 1 test.
- `cd backend && uv run pytest tests/test_api_speech.py tests/test_speech_service.py tests/test_voice_profiles.py -q` passed with 11 tests.
- `cd backend && uv run ruff check services/api/src/noveland/services/api/speech.py tests/test_api_speech.py` passed.
- `cd backend && uv run mypy services/api/src/noveland/services/api/speech.py tests/test_api_speech.py` passed.
- OpenSpec strict validations and `git diff --check` passed after documentation updates.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 564 passed and 8 skipped.

## Remaining Work

1. Commit the completed F-066 batch after final status review; do not push unless explicitly requested.
2. Continue backend forbidden-evidence audits for privacy export contents, remaining player/member DTOs, and worldline isolation edge cases.
3. Continue Web/e2e security audit on remaining Next route handlers, proxy modules, method exposure, response shaping, role boundary, evidence redaction, and client-side leaks.

## Finding F-066

- Speech TTS/STT API responses exposed internal media storage URIs and raw invocation payload fields.
- The remediation shapes speech action responses through safe DTOs that omit storage locators, media job internals, and raw invocation payload fields while preserving safe IDs/status/MIME/checksum/transcript/invocation follow-up fields.
- Residual risk: dedicated admin media and invocation ledger routes still intentionally expose deeper operator evidence according to their own access/redaction contracts; continue auditing lower-privilege and product-facing surfaces.
