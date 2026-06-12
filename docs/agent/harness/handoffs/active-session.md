# Active Session Handoff

- Date: 2026-06-12T08:25:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-073 are remediated on this branch; latest batch is F-073 GM proposal payload persistence redaction.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-073 batch: e2cf6b9 fix(worlds): sanitize offscreen event payloads.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services at F-073 batch start: Noveland Postgres was healthy on 55432->5432; Noveland NATS was healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started for this batch.
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

- Reconfirmed current state before F-073: branch `feature/audit-and-hardening-post-v1-1-rc`, worktree clean, local ahead 1 at `e2cf6b9`, active OpenSpec change valid, and Postgres/NATS healthy.
- Continued backend forbidden-evidence audit across world event persistence surfaces after F-072.
- Recorded/remediated F-073: GM proposal resolution copied arbitrary `GMEventProposal.proposed_payload` into `WorldEventAppend(payload=...)`, allowing dirty proposal payloads from admin input, macro planning, or provider-backed planning evidence to persist forbidden evidence in `world_events.payload`.
- Added an architecture-contracts OpenSpec scenario requiring resolved GM proposal world event payloads to omit storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, and base64-like values while preserving safe proposal identity and event context.
- Moved the F-072 offscreen event sanitizer into `backend/packages/worlds/src/noveland/worlds/sanitization.py` as `sanitize_world_event_payload()`.
- Updated `backend/packages/worlds/src/noveland/worlds/autonomous.py` and `backend/packages/worlds/src/noveland/worlds/gm.py` to use the shared sanitizer before event payload persistence.
- Added regression coverage that first reproduced `storage_uri` persistence in GM proposal `WorldEventModel.payload`, then asserts safe beat/context/proposal fields remain while forbidden markers are removed.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_worlds.py::test_gm_proposal_resolution_sanitizes_persisted_world_event_payload -q` first failed on unredacted `storage_uri` persisted in `WorldEventModel.payload`, then passed with 1 test after remediation.
- `cd backend && uv run pytest tests/test_api_worlds.py::test_offscreen_resolution_sanitizes_persisted_world_event_payload tests/test_api_worlds.py::test_gm_proposal_resolution_sanitizes_persisted_world_event_payload -q` passed with 2 tests.
- `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 40 tests.
- `cd backend && uv run ruff check packages/worlds/src/noveland/worlds/sanitization.py packages/worlds/src/noveland/worlds/autonomous.py packages/worlds/src/noveland/worlds/gm.py tests/test_api_worlds.py` passed.
- `cd backend && uv run mypy packages/worlds/src/noveland/worlds/sanitization.py packages/worlds/src/noveland/worlds/autonomous.py packages/worlds/src/noveland/worlds/gm.py tests/test_api_worlds.py` passed.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 566 passed and 8 skipped.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

## Remaining Work

1. Commit the completed F-073 batch after final diff/status review; do not push unless explicitly requested.
2. Continue backend forbidden-evidence audits for remaining world event producers, especially secret reveal/consequence metadata and other historical dirty event payload paths.
3. Continue Web/e2e security audit on remaining Next route handlers, proxy modules, method exposure, response shaping, role boundary, evidence redaction, and client-side leaks.
4. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.

## Finding F-073

- GM proposal resolution persisted arbitrary proposed payload JSON directly into world events.
- The remediation sanitizes the merged proposal event payload at the domain persistence boundary, so unsafe data is omitted even for historical dirty proposal rows while safe fields such as beat, numeric context, nested safe strings, safe list items, proposal ID, and safe proposal title remain.
- Residual risk: this focused batch protects GM proposal and offscreen resolution payload persistence; continue auditing other event producers for comparable persistence-time boundaries.
