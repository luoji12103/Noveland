# Active Session Handoff

- Date: 2026-06-12T08:25:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-071 are remediated on this branch; latest batch is F-071 player choice preview effect redaction.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-071 batch: 8fe7d50 fix(worlds): redact player notification text.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services at F-071 batch start: Noveland Postgres was healthy on 55432->5432; Noveland NATS was healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started for this batch.
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

- Reconfirmed current state after F-070: branch `feature/audit-and-hardening-post-v1-1-rc`, worktree clean, local and origin synchronized at 8fe7d50, active OpenSpec change valid, Postgres/NATS healthy.
- Continued backend forbidden-evidence audit across Web route/client helpers, player sessions, private beta, beta feedback, media, moderation, conversations, and remaining worlds.py member/player DTOs.
- Recorded/remediated F-071: member-readable `POST /worlds/{world_id}/player-choices/preview` hid diagnostics for non-admins but returned arbitrary `relationship_updates`, `faction_updates`, and `offscreen_events` effect JSON verbatim from request payloads.
- Added an architecture-contracts OpenSpec scenario requiring member player choice preview effect metadata to omit forbidden keys/values while retaining safe public consequence preview fields.
- Added `_sanitize_public_json_list()` and applied it to non-admin player choice preview relationship, faction, and offscreen effect lists; admin preview responses remain unchanged.
- Expanded player interaction API coverage to first reproduce the member preview `raw_prompt` leak, then assert member preview effect JSON omits `storage_uri`, `media://`, `raw_prompt`, `raw_output`, and `/root/` while admin preview retains full effect metadata and diagnostics.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope -q` first failed on the unredacted member preview `raw_prompt`, then passed with 1 test after remediation.
- `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 38 tests.
- `cd backend && uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- `cd backend && uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 564 passed and 8 skipped.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed after harness updates.

## Remaining Work

1. Commit the completed F-071 batch after final diff/status review; do not push unless explicitly requested.
2. Continue backend forbidden-evidence audits for remaining member/player DTOs, player privacy export contents, provider/quota/worldline isolation edge cases, and historical dirty content paths.
3. Continue Web/e2e security audit on remaining Next route handlers, proxy modules, method exposure, response shaping, role boundary, evidence redaction, and client-side leaks.
4. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.

## Finding F-071

- Member player choice preview responses exposed arbitrary effect JSON to ordinary world members even though diagnostics were already hidden.
- The remediation applies the shared public JSON sanitizer to non-admin preview relationship update, faction update, and offscreen event lists while preserving safe fields and admin review detail.
- Residual risk: this focused batch covered player choice preview effect JSON only; continue auditing other preview/dry-run endpoints for historical or request-copied forbidden evidence.
