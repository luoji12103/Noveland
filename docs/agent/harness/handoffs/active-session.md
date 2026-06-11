# Active Session Handoff

- Date: 2026-06-12T05:36:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-063 are remediated on this branch; latest batch is F-063 speech voice profile reference-asset isolation.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-063 batch: edeace5 fix(reader): scope media downloads by worldline.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services at F-063 batch start: Noveland Postgres was healthy on 55432->5432; Noveland NATS was healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started for this batch.
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

- Continued backend worldline isolation audit after F-062.
- Reviewed provider smoke/fallback/test invocation paths, observability readiness/report paths, and visual generation reference validation; no confirmed defect was recorded in those slices.
- Recorded/remediated F-063: world-level voice profiles could reference fork-scoped audio assets because `reference_asset_id` validation skipped exact worldline matching when `worldline_id` was null.
- Added an architecture-contracts OpenSpec scenario requiring world-level voice profiles to reject worldline-scoped media references while preserving scoped same-worldline audio validation.
- Updated `VoiceProfileService._validate_reference_asset()` so world-level profiles may remain provider/default profiles without media references, but cannot promote fork media into world-level voice references.
- Added a focused voice profile service regression for the world-level reference rejection.

## Verification This Batch

- `cd backend && uv run pytest tests/test_voice_profiles.py` passed with 4 tests; `cd backend && uv run pytest tests/test_speech_service.py tests/test_api_speech.py tests/test_voice_profiles.py` passed with 11 tests; focused backend ruff/mypy passed; full `cd backend && uv run pytest` passed with 564 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.
- Web gates were not rerun for F-063; the previous F-062 batch had full Web unit/build/e2e gates passing.

## Remaining Work

1. Commit the completed F-063 batch after final status review; do not push unless explicitly requested.
2. Continue backend worldline isolation and forbidden-evidence audits for remaining memory, player session, beta feedback, moderation, observability, speech/API output, and product/spec drift surfaces.
3. Continue Web/e2e security audit on remaining Next route handlers, proxy modules, method exposure, response shaping, role boundary, evidence redaction, and client-side leaks.

## Finding F-063

- Backend world-level voice profiles accepted `reference_asset_id` values pointing at worldline-scoped audio media assets.
- The remediation rejects reference media for world-level profiles and keeps exact same-worldline audio validation for scoped profiles.
- Residual risk: continue reviewing speech API response shaping and downstream TTS/STT execution evidence for forbidden prompt, storage, raw output, bytes, base64, and cross-worldline references before closing tasks 2.2/2.4.
