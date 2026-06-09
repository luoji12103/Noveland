# Active Session Handoff

- Date: 2026-06-09T11:40:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-042 are remediated and targeted checks passed on this branch. F-042 is ready to commit. No push performed.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-042 batch: cc6d3f9 fix(web): encode core world api path segments.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services: Noveland Postgres and NATS containers are healthy on overridden ports. No authoritative Noveland API/Web/runtime process was started for this batch; project Playwright e2e used its own test server.
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

- Continued the Web/e2e security audit after F-041.
- Recorded F-042: browser-side Web clock, replay, snapshot, event audit, scene, and location-edge helpers embedded decoded world and nested identifiers directly into same-origin API paths.
- Added an architecture-contracts OpenSpec delta requiring these Web clients to preserve same-origin route templates with encoded dynamic segments and encoded query filters.
- Encoded path segments in the scoped helper group in `web/lib/worlds/client.ts`: clock controls/transitions, replay state, snapshots, snapshot integrity, world event audit, scenes, and location edges.
- Added focused Web worlds client tests proving reserved characters stay inside representative same-origin path segments and query values.
- Restored `web/next-env.d.ts` after Playwright/Next dev regenerated it to `.next/dev/types/routes.d.ts`.

## Verification This Batch

- `cd web && npm run test -- lib/worlds/client.test.ts`: 27 passed.
- `cd web && npm run typecheck`: passed.
- `cd web && npm run lint`: passed.
- `cd web && npm run test`: 45 files and 150 tests passed. Existing React act warnings appeared in runtime-admin test output, but the suite passed.
- `cd web && npm run build`: passed.
- `cd web && npm run test:e2e`: 21 passed.
- `cd web && npm run check:next-env`: failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`: passed.
- `openspec validate --changes --strict`: 1 passed.
- `openspec validate --specs --strict`: 76 passed.
- `git diff --check`: passed.

## Remaining Work

1. Continue Web/e2e security audit for remaining `web/lib/worlds/client.ts` helper path construction outside this scoped clock/replay/scene batch, especially organization/agent/calendar/schedule and later living-world helper groups, plus Next route handlers, CSRF forwarding, method exposure, response header behavior, client-side data leaks, XSS-prone rendering sinks, and admin/player/member boundary leaks.
2. Audit project Playwright/e2e stability and boundary coverage without browser/computer-use plugins.
3. Continue product normal-use flows and spec/history drift audits after the remaining Web/e2e security pass.

## Finding F-042

- Browser-side Web clock/replay/scene API URL construction appended decoded world, scene, and location-edge identifiers directly to same-origin API paths and filters.
- The remediation encodes dynamic segments for the scoped helper group, while preserving filters as query data.
- Residual risk: remaining `web/lib/worlds/client.ts` helper groups outside this scope and Next route handlers still need separate evidence-based review before remediation.
