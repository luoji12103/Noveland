# Active Session Handoff

- Date: 2026-06-08T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-007 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Baseline before branch: main and origin/main at 1ffbf8a7876a5ddc10789db2339cf2efba125c76, commit docs(openspec): archive v1.1 normal use release candidate.
- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-007 batch: b7abd9b fix(security): sanitize member media metadata.
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

- Reconfirmed realtime server state after F-006: branch feature/audit-and-hardening-post-v1-1-rc, HEAD b7abd9b before this batch, clean worktree, active OpenSpec change in progress, Postgres/NATS healthy.
- Audited non-media member-readable realtime streams after F-006.
- Recorded F-007: world/conversation realtime streams were member-authenticated but serialized admin diagnostics, agent run prompt/response text and diagnostics, hidden/unpublished narrative artifacts, and conversation policy/writer internals.
- Added an architecture-contracts OpenSpec delta requiring member realtime world/conversation streams to omit raw prompts/outputs, admin diagnostics, hidden artifacts, provider refs, storage refs, bytes, and base64 evidence.
- Added role-aware realtime stream shaping. Admin stream consumers keep operator details; ordinary members receive safe clock, reader-visible published narrative artifacts, safe conversation/turn updates, and no diagnostic/run internals.
- Applied the same member-safe shaping to conversation live WebSocket snapshots.

## Verification This Batch

- uv run pytest tests/test_api_realtime.py: 6 passed.
- uv run ruff check services/api/src/noveland/services/api/realtime.py tests/test_api_realtime.py: passed.
- uv run mypy services/api/src/noveland/services/api/realtime.py tests/test_api_realtime.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- openspec validate --specs --strict: 76 passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with non-realtime reader/player DTOs, worldline isolation checks, and remaining forbidden-data paths.
2. Later audit Web/e2e route handlers and client rendering for CSRF, XSS, auth forwarding, role boundaries, and client-side leaks.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-007

- Member-readable realtime world/conversation streams exposed admin diagnostics, agent run prompt/response text, run diagnostics, hidden/unpublished narrative artifacts, and conversation policy/writer internals.
- The remediation makes realtime payload shaping role-aware, preserving operator detail for admins while restricting ordinary members to safe clock, published reader-visible artifacts, safe conversation/turn updates, and no diagnostic/run internals.
- Residual risk: non-realtime reader/player DTOs, Web proxies/rendering, and broader worldline isolation still need dedicated review.
