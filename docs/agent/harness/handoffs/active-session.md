# Active Session Handoff

- Date: 2026-06-12T12:45:50+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-083 are remediated on this branch; latest batch is F-083 member agent catalog source preset provenance redaction.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-083 batch: b245086 fix(worlds): redact member replay source refs.
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

- Reconfirmed current state before F-083: branch `feature/audit-and-hardening-post-v1-1-rc`, worktree clean at `b245086`, local and remote aligned, active OpenSpec change valid, and Postgres/NATS healthy.
- Continued backend member/player/reader DTO boundary audit over member-readable agent catalog provenance after F-082.
- Recorded/remediated F-083: member-readable `GET /worlds/{world_id}/agents` responses exposed `source_preset_id` and `source_preset_version` despite preset provenance being operator/admin-managed evidence.
- Updated architecture-contracts OpenSpec before implementation.
- Changed `_agent_response()` so source preset provenance follows `include_admin_fields`: admins retain source preset ID/version, ordinary members receive `null`.
- Extended preset materialization API coverage for admin-retained and member-hidden source preset refs.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_worlds.py::test_create_agent_from_preset_materializes_persona_calendar_and_provider_mapping -q` first failed on unredacted `source_preset_id`, then passed with 1 test after remediation.
- `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests.
- Focused `uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- Focused `uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

## Remaining Work

1. Continue Web/e2e audit for remaining local query navigation, route handlers, proxy method exposure, response shaping, role boundary, evidence redaction, and client-side rendering sinks.
2. Continue backend audits for remaining reader/member/player DTO exposure boundaries, especially source evidence and non-event persistence outside the recently remediated run/replay/presentation/media/agent catalog paths.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless explicitly requested.

## Finding F-083

- Agent source preset IDs and source preset versions are operator/admin provenance for platform-managed agent presets and should not be exposed through ordinary member agent catalog responses.
- The remediation returns `null` for those source preset refs to ordinary members while preserving safe public agent identity, display name, kind, and sanitized characterization fields; admins retain source preset provenance for diagnostics and preset update workflows.
- Residual risk: continue auditing other member-readable status/catalog APIs for source IDs, internal provenance, or correlation evidence that survived earlier metadata/prompt redaction passes.
