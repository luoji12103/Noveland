# Active Session Handoff

- Date: 2026-06-13T04:15:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-133 are remediated on this branch; latest batch is F-133 member agent calendar text redaction hardening.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before the F-133 commit: d0bbc344fd771566bafaced9714e029fac6857f9.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server status was rechecked before this continuation: branch was `feature/audit-and-hardening-post-v1-1-rc` at d0bbc34, local branch was ahead of upstream by 1 local commit, worktree started clean, active OpenSpec change was in progress, specs strict validation passed with 76 specs, change strict validation passed, and Noveland Postgres/NATS were healthy.
- Only .env.example was observed in the repo; do not read or expose real secrets.

## Guardrails

- Current user instruction: use SSH/CLI only; avoid browser/computer-use plugins and other non-CLI tooling that may interrupt the session.
- Current goal instruction says do not push unless the user explicitly asks; commit locally after verified remediation and leave branch unpushed.
- Do not bypass OpenSpec; add or update spec deltas before behavior-changing fixes.
- Keep real-provider tests opt-in only; do not set NOVELAND_RUN_REAL_PROVIDER_TESTS=1 without explicit user authorization.
- Preserve provider execution through ProviderExecutionService, quota-before-adapter execution, secret redaction, invocation ledger boundaries, media boundaries, worldline isolation, and reader/member/player DTO safety.
- Do not expose resolved secrets, disallowed auth refs, storage URIs, filesystem/object paths, local model paths, raw prompts, raw outputs, prompt snapshot internals, invite tokens, bytes, or base64.
- Do not broaden worlds.py into a catch-all router.
- For UI/e2e use project Playwright/e2e only.

## Completed This Batch

- Reconfirmed realtime server state from `/root/code/Noveland`: branch `feature/audit-and-hardening-post-v1-1-rc`, HEAD `d0bbc34`, local branch ahead of upstream by 1, worktree clean, OpenSpec active change valid, specs strict validation passed with 76 specs, and Postgres/NATS healthy.
- Continued backend member-readable DTO audit after F-132.
- Identified F-133: member-readable agent calendar entries redacted metadata but returned admin-authored `title`, `description`, and `recurrence_rule` unchanged, allowing raw prompt/storage/path/secret-like markers in calendar text to reach ordinary members.
- Added an architecture-contracts OpenSpec scenario requiring sensitive-looking calendar text to be blanked for members while safe calendar text remains visible and admin routes retain full text.
- Changed `_calendar_entry_response()` so non-admin member responses use existing `_sanitize_public_text()` for title, description, and recurrence rule while preserving metadata redaction and admin visibility.
- Extended `test_world_admin_manages_calendar_entries_and_schedule_rules` to cover sensitive member calendar text redaction and safe calendar title preservation.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_worlds.py::test_world_admin_manages_calendar_entries_and_schedule_rules -q` first failed because member calendar title text containing `raw_prompt` rendered unchanged.
- The same focused test passed after remediation.
- `cd backend && uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- `cd backend && uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 42 tests.
- full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 587 tests and 8 skipped; `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict` with 76 specs, and `git diff --check` passed.

## Remaining Work

1. Continue backend member/player DTO audits for other public text fields with sensitive-looking content.
2. Continue Web/e2e audit for route handlers, client-side text sinks, EventSource failure assumptions, and role boundaries.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless the user explicitly asks; keep local branch clean after commits.

## Finding F-133

- Member agent calendar responses should preserve safe schedule text but must not echo admin/operator evidence markers embedded in calendar title, description, or recurrence rule text.
- The remediation applies the existing public sensitive-text blanking helper to non-admin calendar text fields and leaves admin responses unchanged.
- Residual risk: continue auditing other member-readable public text fields that intentionally preserve safe prose but may still need sensitive-looking text blanking.
