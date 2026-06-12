# Active Session Handoff

- Date: 2026-06-12T08:25:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-074 are remediated on this branch; latest batch is F-074 event store payload safety enforcement.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-074 batch: 52920d1 fix(worlds): sanitize gm proposal event payloads.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services at F-074 batch start: Noveland Postgres was healthy on 55432->5432; Noveland NATS was healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started for this batch.
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

- Reconfirmed current state before F-074: branch `feature/audit-and-hardening-post-v1-1-rc`, worktree clean, local ahead 2 at `52920d1`, active OpenSpec change valid, and Postgres/NATS healthy.
- Continued backend forbidden-evidence audit across world event persistence surfaces after F-073.
- Recorded/remediated F-074: `WorldEventStore.append_event()` persisted `event_input.payload` directly, so producers missed by F-072/F-073 could still write forbidden evidence to `world_events.payload`.
- Added an architecture-contracts OpenSpec scenario requiring event-store-level payload safety regardless of producer.
- Added `backend/packages/events/src/noveland/events/sanitization.py` and enforced `sanitize_world_event_payload()` inside `backend/packages/events/src/noveland/events/event_store.py` before `WorldEventModel` persistence.
- Removed the temporary `backend/packages/worlds/src/noveland/worlds/sanitization.py` helper and removed producer-level sanitizer calls from offscreen and GM proposal paths, leaving the event store as final enforcement.
- Added regression coverage that first reproduced `storage_uri` persistence through secret reveal event payloads, then asserts safe secret/consequence fields remain while forbidden markers are removed.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_worlds.py::test_event_store_sanitizes_secret_reveal_event_payload -q` first failed on unredacted `storage_uri` persisted in `WorldEventModel.payload`, then passed after remediation.
- `cd backend && uv run pytest tests/test_api_worlds.py::test_offscreen_resolution_sanitizes_persisted_world_event_payload tests/test_api_worlds.py::test_gm_proposal_resolution_sanitizes_persisted_world_event_payload tests/test_api_worlds.py::test_event_store_sanitizes_secret_reveal_event_payload -q` passed with 3 tests.
- `cd backend && uv run pytest tests/test_api_worlds.py tests/test_event_contracts.py -q` passed with 49 tests.
- `cd backend && uv run ruff check packages/events/src/noveland/events/sanitization.py packages/events/src/noveland/events/event_store.py packages/worlds/src/noveland/worlds/autonomous.py packages/worlds/src/noveland/worlds/gm.py tests/test_api_worlds.py tests/test_event_contracts.py` passed.
- `cd backend && uv run mypy packages/events/src/noveland/events/sanitization.py packages/events/src/noveland/events/event_store.py packages/worlds/src/noveland/worlds/autonomous.py packages/worlds/src/noveland/worlds/gm.py tests/test_api_worlds.py tests/test_event_contracts.py` passed.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 567 passed and 8 skipped.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

## Remaining Work

1. Commit the completed F-074 batch after final diff/status review; do not push unless explicitly requested.
2. Continue backend audits for non-event persistence and remaining reader/member/player exposure boundaries.
3. Continue Web/e2e security audit on remaining Next route handlers, proxy modules, method exposure, response shaping, role boundary, evidence redaction, and client-side leaks.
4. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.

## Finding F-074

- Event payload safety was enforced only by selected producers rather than by `WorldEventStore` itself.
- The remediation sanitizes every event payload at the storage boundary, including snapshot event payload refs and historical/future producers that pass arbitrary nested JSON into `append_event()`.
- Residual risk: this focused batch protects `world_events.payload`; continue auditing non-event persistence tables, response DTOs, Web proxies, and product flows for comparable forbidden-evidence exposure.
