# Active Session Handoff

- Date: 2026-06-09T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-030 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-030 batch: e5dfc3d fix(security): redact member conversation turn evidence.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services: Noveland Postgres and NATS containers are healthy on overridden ports. Process scan showed unrelated uvicorn/Next/Playwright-style processes, but no authoritative Noveland API/Web/runtime process was confirmed for this batch.
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

- Reconfirmed server state: branch feature/audit-and-hardening-post-v1-1-rc, HEAD e5dfc3d before this batch, clean worktree, active OpenSpec change in progress, OpenSpec strict validation passing, Postgres/NATS healthy.
- Used the security-best-practices guidance for Next.js, React/frontend, and FastAPI review focus.
- Audited Web Next route handlers and same-origin proxy helpers for route-boundary handling.
- Recorded F-030: world and conversation realtime stream route handlers forwarded decoded dynamic route params into backend paths without encoding.
- Added an architecture-contracts OpenSpec delta requiring Web API proxies to preserve backend route boundaries with fixed templates and encoded dynamic segments.
- Encoded dynamic `worldId` and `conversationId` segments in the world and conversation SSE proxy route handlers.
- Expanded realtime proxy tests to prove decoded identifiers containing `/` are forwarded as `%2F` inside backend path segments while preserving query strings.

## Verification This Batch

- `cd web && npm run test -- lib/realtime/proxy.test.ts`: 3 passed.
- `cd web && npm run lint`: passed.
- `cd web && npm run typecheck`: passed.
- `cd web && npm run test`: 42 files and 136 tests passed. Existing React act warnings appeared in runtime-admin test output, but the suite passed.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`: passed.
- `openspec validate --specs --strict`: 76 passed.
- `git diff --check`: passed before commit.

## Remaining Work

1. Continue Web/e2e security audit for remaining Next route handlers, CSRF forwarding, method exposure, response header behavior, client-side data leaks, and XSS-prone rendering sinks.
2. Audit project Playwright/e2e coverage for security and boundary gaps without browser/computer-use plugins.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-030

- Web world and conversation realtime stream proxies inserted decoded route parameters directly into backend paths.
- The remediation encodes dynamic stream path segments before proxying while preserving the query string.
- Residual risk: other Web route handlers, frontend rendering, client helper URL construction, and e2e coverage still need dedicated review.
