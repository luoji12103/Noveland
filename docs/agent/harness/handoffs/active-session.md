# Active Session Handoff

- Date: 2026-06-09T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-024 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Baseline before branch: main and origin/main at 1ffbf8a7876a5ddc10789db2339cf2efba125c76, commit docs(openspec): archive v1.1 normal use release candidate.
- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-024 batch: ad6bbf2 fix(security): redact member world bible evidence.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services: Noveland Postgres and NATS containers are healthy on overridden ports. No authoritative Noveland API, Web, or runtime process was observed during this batch.
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

- Reconfirmed server state after F-023: branch feature/audit-and-hardening-post-v1-1-rc, HEAD ad6bbf2 before this batch, clean worktree, active OpenSpec change in progress, Postgres/NATS healthy.
- Audited member-readable worlds.py agent presence DTOs and confirmed scheduled_movement and last_event_id exposure to ordinary world members.
- Recorded F-024: member-readable agent presence responses exposed future/offscreen movement plans and last event linkage.
- Added an architecture-contracts OpenSpec delta requiring member agent presence responses to omit scheduled_movement and last_event_id while preserving safe current scene, visibility, encounter eligibility, identity, worldline, and timing fields.
- Added role-aware response shaping. World admins retain presence scheduled movement and last event linkage; ordinary members receive scheduled_movement={} and last_event_id=None.
- Expanded location graph and agent presence API regression coverage to compare admin-preserved scheduling evidence against member-redacted payloads.

## Verification This Batch

- uv run pytest tests/test_api_worlds.py::test_location_graph_and_agent_presence_enforce_world_scope: 1 passed.
- uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py: passed.
- uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- openspec validate --specs --strict: 76 passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with remaining non-realtime member DTOs, residual source/evidence refs, worldline isolation checks, and forbidden-data paths.
2. Later audit Web/e2e route handlers and client rendering for CSRF, XSS, auth forwarding, role boundaries, and client-side leaks.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-024

- Member-readable agent presence REST responses exposed scheduled movement plans and last event linkage.
- The remediation makes this response role-aware, preserving scheduling internals for admins while returning scheduled_movement={} and last_event_id=None to ordinary members.
- Residual risk: remaining source/evidence refs in other member-readable DTOs, Web proxies/rendering, and broader worldline isolation still need dedicated review.
