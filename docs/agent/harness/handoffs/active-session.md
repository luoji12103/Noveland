# Active Session Handoff

- Date: 2026-06-12T02:20:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-054 are remediated on this branch.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-054 batch: 1a31a2d fix(web): encode local app route links.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services: Noveland Postgres is healthy on 55432->5432; Noveland NATS is healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started for this batch; project Playwright e2e used its own test server.
- Only .env.example was observed in the repo; do not read or expose real secrets.

## Guardrails

- Current user instruction: use SSH/CLI only; avoid browser/computer-use plugins and other non-CLI tooling that may interrupt the session.
- Current user instruction: after each completed commit, push it to the configured remote; do not commit or push unfinished work.
- Do not bypass OpenSpec; add or update spec deltas before behavior-changing fixes.
- Keep real-provider tests opt-in only; do not set NOVELAND_RUN_REAL_PROVIDER_TESTS=1 without explicit user authorization.
- Preserve provider execution through ProviderExecutionService, quota-before-adapter execution, secret redaction, invocation ledger boundaries, media boundaries, worldline isolation, and reader/member/player DTO safety.
- Do not expose resolved secrets, disallowed auth refs, storage URIs, filesystem/object paths, local model paths, raw prompts, raw outputs, prompt snapshot internals, invite tokens, bytes, or base64.
- Do not broaden worlds.py into a catch-all router.
- For UI/e2e use project Playwright/e2e only.

## Completed This Batch

- Reconfirmed realtime git/OpenSpec/service/test-entry status from the server before editing.
- Continued the Web/e2e security audit on Next route/proxy response header behavior after F-053.
- Recorded and remediated F-054: the shared Web proxy response helper relayed backend `Set-Cookie` headers for non-auth proxies as well as auth routes.
- Added an architecture-contracts OpenSpec delta requiring non-auth Web proxies to omit backend cookie mutation headers while preserving auth cookie flows.
- Made `Set-Cookie` relay opt-in on `buildProxyResponse()`, explicitly enabled it in `proxyAuthRequest()`, and left API/world/runtime/private-beta proxies on the default strip behavior.
- Added focused proxy regression coverage for auth relay preservation and non-auth generic API, world, runtime, and private beta cookie stripping.
- Restored `web/next-env.d.ts` after Playwright/Next dev regenerated it to `.next/dev/types/routes.d.ts`.

## Verification This Batch

- `cd web && npm run test -- lib/auth/proxy.test.ts lib/worlds/proxy.test.ts lib/runtime/proxy.test.ts lib/private-beta/proxy.test.ts lib/api-proxy.test.ts`: 5 files and 12 tests passed.
- `cd web && npm run typecheck`: passed.
- `cd web && npm run lint`: passed.
- `cd web && npm run test`: 51 files and 175 tests passed. Existing React act warnings appeared in runtime-admin test output, but the suite passed.
- `cd web && npm run build`: passed.
- `cd web && npm run test:e2e`: 21 passed.
- `cd web && npm run check:next-env`: failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`: passed.
- `openspec validate --changes --strict`: passed with 1 passed.
- `openspec validate --specs --strict`: passed with 76 specs.
- `git diff --check`: passed.

## Remaining Work

1. Continue Web/e2e security audit on remaining Next route handlers and proxy modules for method exposure, response shaping beyond cookies, role boundary, evidence redaction, and client-side data leaks.
2. Audit Web rendering and project Playwright/e2e coverage for XSS-prone sinks, admin/player/member boundary gaps, and normal-use product flow drift without browser/computer-use plugins.
3. Continue product normal-use and spec/history drift audit after Web route/proxy review.

## Finding F-054

- Non-auth Web proxies reused an auth-oriented response helper that unconditionally relayed backend `Set-Cookie` headers.
- The remediation preserves cookie mutation relay for auth flows only and strips backend cookie mutation headers from generic API, world, runtime, and private beta proxies.
- Residual risk: remaining Next route handler method exposure, response shaping beyond cookies, and client-rendering sinks still need separate evidence-based review before remediation.
