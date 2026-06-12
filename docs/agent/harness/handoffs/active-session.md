# Active Session Handoff

- Date: 2026-06-12T11:25:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-078 are remediated on this branch; latest batch is F-078 member-safe conversation presentation GET response shaping.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-078 batch: cbd7cde fix(media): redact member catalog provenance.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services at batch start: Noveland Postgres was healthy on 55432->5432; Noveland NATS was healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started for this batch.
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

- Reconfirmed current state before F-078: branch `feature/audit-and-hardening-post-v1-1-rc`, worktree clean, local/remote aligned at `cbd7cde`, active OpenSpec change valid, and Postgres/NATS healthy.
- Continued backend playback/presentation audit and recorded F-078: Web playback expects safe presentation DTOs, but backend presentation GET was world-admin-only and canonical presentation records can contain internal authoring/provenance refs.
- Updated the architecture-contracts OpenSpec scenario for member-safe presentation GET before implementation.
- Changed only the presentation GET route to member-readable while preserving admin-only PUT/PATCH/render-visual/render-speech/transcribe-audio.
- Added non-admin presentation response shaping: ordinary members keep playback-safe speaker, emotion, render state, record IDs, timestamps, and media asset IDs, while `sprite_set_id`, `sprite_variant_id`, `voice_profile_id`, `transcript_id`, and forbidden `presentation_json` provenance are removed.
- Updated permission and security regression matrices so presentation GET is no longer treated as admin-only, but presentation mutation/render routes remain denied to ordinary members.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_conversation_presentations.py -q` passed with 2 tests.
- `cd backend && uv run pytest tests/test_api_permission_matrix.py tests/test_security_regression_suite.py tests/test_api_conversation_presentations.py -q` passed with 9 tests.
- Focused `cd backend && uv run ruff check ...` and `cd backend && uv run mypy ...` passed for `conversation_presentations.py`, `test_api_conversation_presentations.py`, `test_api_permission_matrix.py`, and `test_security_regression_suite.py`.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 567 passed and 8 skipped.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

## Remaining Work

1. Continue backend audits for reader/player playback DTO media visibility edge cases, non-event persistence, and remaining reader/member/player exposure boundaries.
2. Continue Web/e2e security audit on remaining Next route handlers, proxy modules, method exposure, response shaping, role boundary, evidence redaction, and client-side leaks.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless explicitly requested.

## Finding F-078

- Ordinary members need presentation GET for playback, but mutation/rendering remains admin-owned authoring behavior.
- The remediation keeps member playback unblocked without exposing authoring refs, transcript refs, provider/model invocation/media job provenance, storage paths, raw prompt/output markers, bytes, or base64 evidence in `presentation_json`.
- Residual risk: continue auditing whether safe presentation media asset IDs should also be filtered against reader-media visibility before Web playback receives them.
