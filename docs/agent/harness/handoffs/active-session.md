# Active Session Handoff

- Date: 2026-06-09T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-032 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-032 batch: da2bab5 fix(web): avoid duplicate memory proxy queries.
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

- Continued the Web/e2e security audit after F-031.
- Recorded F-032: browser-side conversation live WebSocket URLs embedded decoded `worldId` and `conversationId` values directly into backend paths.
- Added an architecture-contracts OpenSpec delta requiring browser-initiated realtime backend URLs to use fixed path templates and encoded dynamic segments.
- Encoded world and conversation identifiers in `web/lib/realtime.ts` before opening conversation live-control sockets.
- Added focused realtime helper tests proving reserved characters stay inside identifier path segments.

## Verification This Batch

- `cd web && npm run test -- lib/realtime.test.ts`: 2 passed.
- `cd web && npm run lint`: passed.
- `cd web && npm run typecheck`: passed.
- `cd web && npm run test`: 44 files and 140 tests passed. Existing React act warnings appeared in runtime-admin test output, but the suite passed.
- `cd web && npm run build`: passed.
- `cd web && npm run check:next-env`: passed.
- `cd web && npm run test:e2e`: attempted full suite; 15 passed, 1 failed (`reader scene view renders galgame-style safe media`), and 5 were skipped after the failure.
- `cd web && npx playwright test tests/e2e/auth.spec.ts --grep "reader scene view renders galgame-style safe media"`: passed on focused rerun.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`: passed.
- `openspec validate --specs --strict`: 76 passed.
- `git diff --check`: passed before commit.

## Remaining Work

1. Continue Web/e2e security audit for remaining Next route handlers, CSRF forwarding, method exposure, response header behavior, client-side data leaks, and XSS-prone rendering sinks.
2. Audit project Playwright/e2e coverage for security and boundary gaps without browser/computer-use plugins.
3. Investigate full-suite e2e order/state pollution around the reader scene-view safe-media test, which passed on focused rerun after the full suite failed.
4. Later audit product normal-use flows and spec/history drift.

## Finding F-032

- Browser-side conversation live socket URL construction appended decoded world/conversation identifiers directly to a backend WebSocket path.
- The remediation encodes both dynamic segments before creating the `WebSocket`, preserving route boundaries for live-control commands.
- Residual risk: other Web route handlers, frontend rendering, client helper URL construction, and e2e coverage still need dedicated review.
