# Active Session Handoff

- Date: 2026-06-12T12:12:39+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-081 are remediated on this branch; latest batch is F-081 member agent run source evidence redaction.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-081 batch: 1bb0380 fix(web): encode dashboard world query.
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

- Reconfirmed current state before F-081: branch `feature/audit-and-hardening-post-v1-1-rc`, worktree clean at `1bb0380`, local and remote synchronized, active OpenSpec change valid, and Postgres/NATS healthy.
- Continued read-only Web/backend audit over route handlers, same-origin proxies, CSRF-bearing client helpers, server loaders, member/reader/player response shaping, reader media delivery, beta feedback, player privacy, and conversation APIs.
- Recorded/remediated F-081: member-readable agent runtime run list responses exposed source calendar entry, source schedule rule, and created event IDs despite hiding prompt text, response text, provider refs, and diagnostics.
- Updated architecture-contracts OpenSpec before implementation.
- Redacted `source_calendar_entry_id`, `source_schedule_rule_id`, and `created_event_id` from non-admin `_agent_run_response()` output while preserving admin source evidence.
- Extended backend API coverage for admin-retained source refs and member-null source refs.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_worlds.py::test_agent_runs_and_narrative_artifacts_api -q` passed with 1 test.
- `cd backend && uv run pytest tests/test_api_worlds.py::test_agent_runs_and_narrative_artifacts_api tests/test_api_worlds.py::test_agent_run_apis_filter_by_worldline -q` passed with 2 tests.
- Focused `uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- Focused `uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

## Remaining Work

1. Continue Web/e2e audit for remaining local query navigation, route handlers, proxy method exposure, response shaping, role boundary, evidence redaction, and client-side rendering sinks.
2. Continue backend audits for remaining reader/member/player DTO exposure boundaries, especially source evidence and non-event persistence outside the recently remediated run/presentation/media paths.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless explicitly requested.

## Finding F-081

- Agent run source calendar/schedule/event IDs are operator/runtime execution evidence and should not be exposed through ordinary member run list responses.
- The remediation returns `null` for those source refs to ordinary members while preserving safe run identity/status/timing and retaining full admin diagnostics.
- Residual risk: continue auditing other member-readable status/list APIs for source IDs or correlation evidence that survived earlier metadata/prompt redaction passes.
