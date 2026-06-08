# Active Session Handoff

- Date: 2026-06-08T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-019 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Baseline before branch: main and origin/main at 1ffbf8a7876a5ddc10789db2339cf2efba125c76, commit docs(openspec): archive v1.1 normal use release candidate.
- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-019 batch: ccd4413 fix(security): redact member dashboard hidden counts.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services: Noveland Postgres and NATS containers are healthy on overridden ports. Other uvicorn/next processes exist on the host, but they were not treated as authoritative Noveland project services for this audit.
- Only .env.example was observed in the repo; do not read or expose real secrets.

## Guardrails

- Do not push unless explicitly requested.
- Do not bypass OpenSpec; add or update spec deltas before behavior-changing fixes.
- Keep real-provider tests opt-in only; do not set NOVELAND_RUN_REAL_PROVIDER_TESTS=1 without explicit user authorization.
- Preserve provider execution through ProviderExecutionService, quota-before-adapter execution, secret redaction, invocation ledger boundaries, media boundaries, worldline isolation, and reader/member/player DTO safety.
- Do not expose resolved secrets, disallowed auth refs, storage URIs, filesystem/object paths, local model paths, raw prompts, raw outputs, prompt snapshot internals, invite tokens, bytes, or base64.
- Do not broaden worlds.py into a catch-all router.
- Do not use browser/computer-use plugins. For UI/e2e use project Playwright/e2e only; use impeccable before any Web UI implementation.

## Completed This Batch

- Reconfirmed server state after F-018: branch feature/audit-and-hardening-post-v1-1-rc, HEAD ccd4413 before this batch, clean worktree, active OpenSpec change in progress, Postgres/NATS healthy.
- Audited member-readable worlds.py player journal, in-world notification, and player intervention DTOs after F-018.
- Recorded F-019: member-readable journal, notification, and intervention responses exposed source evidence refs, intervention prompt text, choice/event linkage, and arbitrary metadata to ordinary world members.
- Added an architecture-contracts OpenSpec delta requiring member journal/notification/intervention responses to omit operator-only internals while preserving safe user-facing fields.
- Added role-aware response shaping. World admins retain source refs, prompt text, choice/event linkage, and metadata; ordinary members receive redacted source refs, prompt text, choice/event linkage, and metadata.
- Expanded guardrail and player interaction regression coverage to compare admin-preserved fields against member-redacted payloads.

## Verification This Batch

- uv run pytest tests/test_api_worlds.py::test_knowledge_player_guardrail_apis_and_acceptance_gap_fixes: 1 passed.
- uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope: 1 passed.
- uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py: passed.
- uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- openspec validate --specs --strict: 76 passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with remaining non-realtime member DTOs, especially agent relationship metadata, calendar metadata, residual source/evidence refs, worldline isolation checks, and forbidden-data paths.
2. Later audit Web/e2e route handlers and client rendering for CSRF, XSS, auth forwarding, role boundaries, and client-side leaks.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-019

- Member-readable player journal, in-world notification, and player intervention REST responses exposed source evidence refs, intervention prompt text, choice/event linkage, and arbitrary metadata.
- The remediation makes these responses role-aware, preserving operator fields for admins while returning redacted source refs, prompt text, choice/event linkage, and metadata to ordinary members.
- Residual risk: agent relationship metadata, calendar metadata, remaining source/evidence refs in member-readable DTOs, Web proxies/rendering, and broader worldline isolation still need dedicated review.
