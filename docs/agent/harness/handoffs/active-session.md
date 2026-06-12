# Active Session Handoff

- Date: 2026-06-12T14:20:17+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-089 are remediated on this branch; latest batch is F-089 event-store payload key normalization.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-089 batch: 8049dc4 fix(metadata): normalize remaining sensitive json keys.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services at batch start: Noveland Postgres and Noveland NATS were healthy. No authoritative Noveland API/Web/runtime process was started outside project test/e2e commands.
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

- Continued backend sanitizer normalization audit after F-088 and prioritized the global `world_events.payload` persistence boundary.
- Recorded/remediated F-089: event-store payload sanitizer missed camelCase/compact forbidden keys such as `rawPrompt`, `rawOutput`, `storageUri`, and `promptSnapshotId`.
- Updated architecture-contracts OpenSpec before implementation.
- Changed `sanitize_world_event_payload()` key filtering to normalize forbidden keys before comparison, while keeping safe domain event context fields such as `secret_id` and `secret_key`.
- Extended world event payload regression coverage so unsafe key variants fail before remediation and persisted payloads retain safe event context after remediation.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_worlds.py::test_event_store_sanitizes_secret_reveal_event_payload -q` first failed on unredacted `rawPrompt` in `world_events.payload`, then passed with 1 test after remediation.
- `cd backend && uv run pytest tests/test_api_worlds.py::test_offscreen_resolution_sanitizes_persisted_world_event_payload tests/test_api_worlds.py::test_gm_proposal_resolution_sanitizes_persisted_world_event_payload tests/test_api_worlds.py::test_event_store_sanitizes_secret_reveal_event_payload tests/test_event_contracts.py -q` passed with 11 tests.
- Focused `uv run ruff check packages/events/src/noveland/events/sanitization.py tests/test_api_worlds.py tests/test_event_contracts.py` passed.
- Focused `uv run mypy packages/events/src/noveland/events/sanitization.py tests/test_api_worlds.py tests/test_event_contracts.py` passed.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

## Remaining Work

1. Continue Web/e2e audit for remaining local query navigation, route handlers, proxy method exposure, response shaping, role boundary, evidence redaction, and client-side rendering sinks.
2. Continue backend audits for remaining reader/member/player DTO exposure boundaries and sanitizer normalization drift, especially `multimodal_eval`, `package_contracts`, provider budget/secret helpers, media metadata, presentation JSON, and worlds public JSON helpers.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless explicitly requested.

## Finding F-089

- The global event-store payload sanitizer must treat snake_case, camelCase, compact, and mixed-punctuation forbidden keys as equivalent without deleting safe domain context fields.
- The remediation removes forbidden key variants before persistence/readback while preserving safe event identity fields.
- Residual risk: continue auditing other package-local metadata sanitizers and member DTO redaction helpers for normalization drift and inconsistent forbidden-value markers.
