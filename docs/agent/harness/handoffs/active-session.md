# Active Session Handoff

- Date: 2026-06-09T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-031 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-031 batch: 9564df5 fix(security): encode realtime stream proxy paths.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services: Noveland Postgres and NATS containers are healthy on overridden ports. No authoritative Noveland API/Web/runtime process was started for this batch.
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

- Continued the Web API proxy audit after F-030.
- Recorded F-031: memory backend jobs/logs route handlers embedded the request query in the backend path argument before `proxyRuntimeRequest` appended the same query again.
- Added an architecture-contracts OpenSpec delta requiring shared runtime proxy query parameters to be appended exactly once.
- Removed route-local query concatenation from `web/app/api/memory-backend-profiles/[profileId]/jobs/route.ts` and `web/app/api/memory-backend-profiles/[profileId]/logs/route.ts`.
- Added focused runtime proxy route-handler tests for jobs/logs routes proving query parameters are forwarded exactly once and encoded profile IDs remain path segments.

## Verification This Batch

- `cd web && npm run test -- lib/runtime/proxy.test.ts`: 2 passed.
- `cd web && npm run lint`: passed.
- `cd web && npm run typecheck`: passed.
- `cd web && npm run test`: 43 files and 138 tests passed. Existing React act warnings appeared in runtime-admin test output, but the suite passed.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`: passed.
- `openspec validate --specs --strict`: 76 passed.
- `git diff --check`: passed before commit.

## Remaining Work

1. Continue Web/e2e security audit for remaining Next route handlers, CSRF forwarding, method exposure, response header behavior, client-side data leaks, and XSS-prone rendering sinks.
2. Audit project Playwright/e2e coverage for security and boundary gaps without browser/computer-use plugins.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-031

- Web memory backend jobs/logs proxies appended the same query string twice through route-local concatenation plus shared runtime proxy behavior.
- The remediation lets the shared runtime proxy append `request.nextUrl.search` once while route handlers pass only fixed paths and encoded dynamic segments.
- Residual risk: other Web route handlers, frontend rendering, client helper URL construction, and e2e coverage still need dedicated review.
