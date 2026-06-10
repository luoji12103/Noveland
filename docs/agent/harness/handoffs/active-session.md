# Active Session Handoff

- Date: 2026-06-10T01:05:10+00:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-049 are remediated on this branch. No push performed.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-049 batch: 5b28e20 fix(web): encode agent narrative api path segments.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services: Noveland Postgres is healthy on 55432->5432; Noveland NATS is healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started for this batch; project Playwright e2e used its own test server.
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

- Reconfirmed realtime git/OpenSpec/service/test-entry status from the server before editing.
- Continued the Web/e2e security audit after F-048.
- Recorded and remediated F-049: browser-side membership list/upsert/delete, member candidate search, and world diagnostics helpers embedded decoded world and user identifiers directly into same-origin API paths.
- Added an architecture-contracts OpenSpec delta requiring membership/candidate/diagnostics Web clients to preserve same-origin route templates with encoded dynamic segments and encoded query filters.
- Encoded path segments in the scoped helper group in `web/lib/worlds/client.ts`: membership list/upsert/delete, member candidate search, and world diagnostics.
- Added focused Web worlds client tests proving reserved characters stay inside representative same-origin path segments and query values.
- Restored `web/next-env.d.ts` after Playwright/Next dev regenerated it to `.next/dev/types/routes.d.ts`.

## Verification This Batch

- `cd web && npm run test -- lib/worlds/client.test.ts`: 34 passed.
- `cd web && npm run typecheck`: passed.
- `cd web && npm run lint`: passed.
- `cd web && npm run test`: 45 files and 157 tests passed. Existing React act warnings appeared in runtime-admin test output, but the suite passed.
- `cd web && npm run build`: passed.
- `cd web && npm run test:e2e`: 21 passed.
- `cd web && npm run check:next-env`: failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import.

## Remaining Work

1. Continue Web/e2e security audit outside `web/lib/worlds/client.ts`, especially other client/proxy modules and Next route handlers for CSRF forwarding, method exposure, response header behavior, role boundary, evidence redaction, and client-side data leaks.
2. Audit Web rendering and project Playwright/e2e coverage for XSS-prone sinks, admin/player/member boundary gaps, and normal-use product flow drift without browser/computer-use plugins.
3. Continue product normal-use and spec/history drift audit after Web client/proxy path-boundary review.

## Finding F-049

- Browser-side Web membership/candidate/diagnostics API URL construction appended decoded world and user identifiers directly to same-origin API paths.
- The remediation encodes dynamic world and user path segments for the scoped helper group, while preserving filters as query data.
- Residual risk: `web/lib/worlds/client.ts` raw world path construction is cleared, but other Web client/proxy modules and Next route handlers still need separate evidence-based review before remediation.
