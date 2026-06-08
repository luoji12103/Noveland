# Active Session Handoff

- Date: 2026-06-09T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-033 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-033 batch: a5b3041 fix(web): encode live socket path segments.
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

- Continued the Web/e2e security audit after F-032.
- Recorded F-033: browser-side conversation same-origin API helper URLs embedded decoded `worldId` and `conversationId` values directly into frontend API paths.
- Added an architecture-contracts OpenSpec delta requiring browser-side same-origin API clients to use fixed route templates and encoded dynamic segments.
- Encoded world and conversation identifiers for scoped conversation collection/detail, participants, turns, narrative, diagnostics, seed, advance, start, pause, resume, and stop helper paths in `web/lib/worlds/client.ts`.
- Added focused Web client helper tests proving reserved characters stay inside identifier path segments across representative read and state-changing conversation helpers.

## Verification This Batch

- `cd web && npm run test -- lib/worlds/client.test.ts`: 25 passed.
- `cd web && npm run lint`: passed.
- `cd web && npm run typecheck`: passed.
- `cd web && npm run test`: 44 files and 141 tests passed. Existing React act warnings appeared in runtime-admin test output, but the suite passed.
- `cd web && npm run build`: passed.
- `cd web && npm run check:next-env`: passed.
- `cd web && npm run test:e2e`: 21 passed.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`: passed.
- `openspec validate --specs --strict`: 76 passed.
- `git diff --check`: passed before commit.

## Remaining Work

1. Continue Web/e2e security audit for remaining Next route handlers, CSRF forwarding, method exposure, response header behavior, client-side data leaks, XSS-prone rendering sinks, and other client helper path construction outside this scoped conversation API batch.
2. Audit project Playwright/e2e coverage for security and boundary gaps without browser/computer-use plugins.
3. Continue product normal-use flows and spec/history drift audits after the remaining Web/e2e security pass.

## Finding F-033

- Browser-side conversation same-origin API URL construction appended decoded world/conversation identifiers directly to frontend API paths.
- The remediation encodes both dynamic segments for scoped conversation collection/detail, participants, turns, narrative, diagnostics, seed, advance, start, pause, resume, and stop helper paths.
- Residual risk: other Web client helpers and Next route handlers still contain many dynamic path constructions that need separate evidence-based review before broad remediation.
