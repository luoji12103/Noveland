# Active Session Handoff

- Date: 2026-06-12T11:45:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-079 are remediated on this branch; latest batch is F-079 member presentation media visibility filtering.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-079 batch: 72736e9 fix(conversations): expose safe member presentations.
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

- Reconfirmed current state before F-079: branch `feature/audit-and-hardening-post-v1-1-rc`, worktree clean, local ahead 1 at `72736e9`, active OpenSpec change valid, and Postgres/NATS healthy.
- Continued the F-078 residual-risk audit and recorded F-079: member-safe presentation GET still preserved `background_asset_id`, `composite_scene_asset_id`, and `tts_media_asset_id` even when those assets were world-admin/private/hidden, suppressed, unreferenced, or otherwise not reader-deliverable.
- Updated the architecture-contracts OpenSpec presentation scenario before implementation.
- Reused `ReaderMediaDeliveryService.get_media()` in non-admin presentation response shaping so ordinary member DTOs keep media asset IDs only when the same asset is reader-deliverable for the presentation worldline.
- Preserved full presentation media IDs for world/platform admins; PUT/PATCH/render-visual/render-speech/transcribe-audio remain admin-only.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_conversation_presentations.py -q` passed with 3 tests.
- `cd backend && uv run pytest tests/test_api_permission_matrix.py tests/test_security_regression_suite.py tests/test_api_conversation_presentations.py -q` passed with 10 tests.
- Focused `cd backend && uv run ruff check ...` and `cd backend && uv run mypy ...` passed for `conversation_presentations.py` and `test_api_conversation_presentations.py`.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

## Remaining Work

1. Continue Web/e2e security audit on remaining Next route handlers, proxy modules, method exposure, response shaping, role boundary, evidence redaction, and client-side leaks.
2. Continue backend audits for non-event persistence and remaining reader/member/player exposure boundaries outside presentation/media playback.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless explicitly requested.

## Finding F-079

- Member presentation GET should align with Reader Media Delivery: media IDs are safe in playback DTOs only when the asset can also be described/delivered on that worldline.
- The remediation removes admin-only/private/hidden/non-deliverable media ID side channels from member presentation DTOs while preserving admin diagnostics and authoring behavior.
- Residual risk: continue Web playback and scene-view audits for route-handler/proxy leaks and client rendering assumptions.
