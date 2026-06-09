# Active Session Handoff

- Date: 2026-06-09T11:20:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-041 are remediated and targeted checks passed on this branch. F-041 is ready to commit. No push performed.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-041 batch: d54c41e fix(web): encode server loader api path segments.
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

- Continued the Web/e2e security audit after F-040.
- Recorded F-041: browser-side Web core world API helpers embedded decoded world and nested identifiers directly into same-origin API paths.
- Added an architecture-contracts OpenSpec delta requiring Web core world API clients to preserve same-origin route templates with encoded dynamic segments and encoded query filters.
- Encoded path segments in the scoped core world helper group in `web/lib/worlds/client.ts`: world CRUD/composition/bible, worldlines, GM agendas/proposals/macro/drafts, resolution rules/dry-run, player actors/session resume/player choices.
- Added focused Web worlds client tests proving reserved characters stay inside representative same-origin path segments and query values.
- Restored `web/next-env.d.ts` after Playwright/Next dev regenerated it to `.next/dev/types/routes.d.ts`.

## Verification This Batch

- `cd web && npm run test -- lib/worlds/client.test.ts`: 26 passed.
- `cd web && npm run typecheck`: passed.
- `cd web && npm run lint`: passed.
- `cd web && npm run test`: 45 files and 149 tests passed. Existing React act warnings appeared in runtime-admin test output, but the suite passed.
- `cd web && npm run build`: passed.
- `cd web && npm run test:e2e`: 21 passed.
- `cd web && npm run check:next-env`: failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`: passed.
- `openspec validate --changes --strict`: 1 passed.
- `openspec validate --specs --strict`: 76 passed.
- `git diff --check`: passed.

## Remaining Work

1. Continue Web/e2e security audit for remaining `web/lib/worlds/client.ts` helper path construction outside this scoped core batch, Next route handlers, CSRF forwarding, method exposure, response header behavior, client-side data leaks, XSS-prone rendering sinks, and admin/player/member boundary leaks.
2. Audit project Playwright/e2e stability and boundary coverage without browser/computer-use plugins.
3. Continue product normal-use flows and spec/history drift audits after the remaining Web/e2e security pass.

## Finding F-041

- Browser-side Web core world API URL construction appended decoded world, worldline, agenda, proposal, resolution rule, and user identifiers directly to same-origin API paths and filters.
- The remediation encodes dynamic segments for the scoped core helper group, while preserving filters as query data.
- Residual risk: remaining `web/lib/worlds/client.ts` helper groups outside this core world scope and Next route handlers still need separate evidence-based review before remediation.
