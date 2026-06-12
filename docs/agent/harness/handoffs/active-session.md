# Active Session Handoff

- Date: 2026-06-12T13:01:03+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-084 are remediated on this branch; latest batch is F-084 member latest snapshot source evidence redaction.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-084 batch: 94c2b51 fix(worlds): redact member agent preset provenance.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services at batch start: Noveland Postgres was healthy on 55432->5432; Noveland NATS was healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started outside project test/e2e commands.
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

- Reconfirmed current state before F-084 from the previous clean commit `94c2b51`, with the active OpenSpec change valid and Postgres/NATS healthy from the current session preflight.
- Continued backend member/player/reader DTO boundary audit over member-readable replay/snapshot source evidence after F-083.
- Recorded/remediated F-084: member-readable `GET /worlds/{world_id}/snapshots/latest` responses exposed `created_by_event_id` despite event audit and snapshot integrity routes being admin-only.
- Updated architecture-contracts OpenSpec before implementation.
- Made `WorldSnapshotResponse.created_by_event_id` nullable and changed `_snapshot_response()` so ordinary members receive `null`; admins retain the created-by event ref for replay diagnostics.
- Extended replay/snapshot API coverage for admin-retained and member-hidden snapshot created-by event refs.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_worlds.py::test_replay_and_snapshot_api_reads_state_and_creates_snapshot -q` first failed on unredacted `created_by_event_id`, then passed with 1 test after remediation.
- `cd backend && uv run pytest tests/test_api_worlds.py::test_replay_and_snapshot_api_reads_state_and_creates_snapshot tests/test_api_worlds.py::test_world_event_audit_requires_admin_and_filters_events -q` passed with 2 tests.
- `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests.
- Focused `uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- Focused `uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

## Remaining Work

1. Continue Web/e2e audit for remaining local query navigation, route handlers, proxy method exposure, response shaping, role boundary, evidence redaction, and client-side rendering sinks.
2. Continue backend audits for remaining reader/member/player DTO exposure boundaries, especially source evidence and non-event persistence outside the recently remediated run/replay/snapshot/presentation/media/agent catalog paths.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless explicitly requested.

## Finding F-084

- Snapshot `created_by_event_id` is operator replay/event evidence and should not be exposed through ordinary member latest snapshot responses.
- The remediation returns `null` for that created-by event ref to ordinary members while preserving safe snapshot identity, worldline, event sequence coverage, schema version, status, and creation time; admins retain the ref for replay diagnostics.
- Residual risk: continue auditing other member-readable status/catalog APIs for source IDs, internal provenance, or correlation evidence that survived earlier metadata/prompt redaction passes.
