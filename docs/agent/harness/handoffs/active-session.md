# Active Session Handoff

- Date: 2026-06-12T12:32:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-082 are remediated on this branch; latest batch is F-082 member replay state source evidence redaction.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-082 batch: d6d749d fix(worlds): redact member agent run source refs.
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

- Reconfirmed current state before F-082: branch `feature/audit-and-hardening-post-v1-1-rc`, worktree clean at `d6d749d`, local ahead 1, active OpenSpec change valid, and Postgres/NATS healthy.
- Continued backend member/player/reader boundary audit over replay/snapshot state, event evidence, clock audit visibility, reader media delivery, player privacy, beta feedback, and conversation response shaping.
- Recorded/remediated F-082: member-readable replay state responses exposed `clock.last_event_id` and `clock.last_event_sequence` despite event audit and clock transition audit being admin-only.
- Updated architecture-contracts OpenSpec before implementation.
- Added `_replay_state_response()` to redact replay clock source event refs for ordinary members while preserving admin replay diagnostics.
- Extended replay/snapshot API coverage for member-hidden and admin-retained clock source refs.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_worlds.py::test_replay_and_snapshot_api_reads_state_and_creates_snapshot -q` passed with 1 test.
- `cd backend && uv run pytest tests/test_api_worlds.py::test_replay_and_snapshot_api_reads_state_and_creates_snapshot tests/test_api_worlds.py::test_world_event_audit_requires_admin_and_filters_events -q` passed with 2 tests.
- Focused `uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- Focused `uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

## Remaining Work

1. Continue Web/e2e audit for remaining local query navigation, route handlers, proxy method exposure, response shaping, role boundary, evidence redaction, and client-side rendering sinks.
2. Continue backend audits for remaining reader/member/player DTO exposure boundaries, especially source evidence and non-event persistence outside the recently remediated run/replay/presentation/media paths.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless explicitly requested.

## Finding F-082

- Replay clock source event IDs and source event sequence are operator/runtime replay evidence and should not be exposed through ordinary member replay state responses.
- The remediation returns `null` for those clock source refs to ordinary members while preserving safe reconstructed clock state, aggregate counts, worldline, and source sequence; admins retain the refs for diagnostics.
- Residual risk: continue auditing other member-readable status APIs for source IDs or correlation evidence that survived earlier metadata/prompt redaction passes.
