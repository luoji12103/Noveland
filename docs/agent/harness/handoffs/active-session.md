# Active Session Handoff

- Date: 2026-06-08T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-020 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Baseline before branch: main and origin/main at 1ffbf8a7876a5ddc10789db2339cf2efba125c76, commit docs(openspec): archive v1.1 normal use release candidate.
- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-020 batch: 6ebc5da fix(security): redact member player evidence refs.
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

- Reconfirmed server state after F-019: branch feature/audit-and-hardening-post-v1-1-rc, HEAD 6ebc5da before this batch, clean worktree, active OpenSpec change in progress, Postgres/NATS healthy.
- Audited member-readable worlds.py agent relationship and agent calendar DTOs after F-019.
- Recorded F-020: member-readable relationship and calendar list responses exposed arbitrary metadata to ordinary world members.
- Added an architecture-contracts OpenSpec delta requiring member relationship/calendar list responses to omit metadata while preserving safe relationship score/identity and calendar title/time/status fields.
- Added role-aware response shaping. World admins retain relationship/calendar metadata; ordinary members receive metadata={}.
- Expanded relationship graph and calendar/schedule regression coverage to compare admin-preserved metadata against member-redacted payloads.

## Verification This Batch

- uv run pytest tests/test_api_worlds.py::test_agent_relationship_graph_enforces_world_scope_and_updates_edges tests/test_api_worlds.py::test_world_admin_manages_calendar_entries_and_schedule_rules: 2 passed.
- uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py: passed.
- uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- openspec validate --specs --strict: 76 passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with remaining non-realtime member DTOs, residual source/evidence refs, worldline isolation checks, and forbidden-data paths.
2. Later audit Web/e2e route handlers and client rendering for CSRF, XSS, auth forwarding, role boundaries, and client-side leaks.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-020

- Member-readable agent relationship and agent calendar list REST responses exposed arbitrary relationship/scheduling metadata.
- The remediation makes these list responses role-aware, preserving metadata for admins while returning metadata={} to ordinary members.
- Residual risk: remaining source/evidence refs in member-readable DTOs, Web proxies/rendering, and broader worldline isolation still need dedicated review.
