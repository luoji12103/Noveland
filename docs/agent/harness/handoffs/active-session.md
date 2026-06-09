# Active Session Handoff

- Date: 2026-06-09T09:29:08+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-038 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-038 batch: f9cda9a fix(web): encode media api path segments.
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

- Continued the Web/e2e security audit after F-037.
- Recorded F-038: browser-side invocation ledger same-origin API helper URLs embedded decoded world, invocation, and tag identifiers directly into frontend API paths.
- Added an architecture-contracts OpenSpec delta requiring browser-side invocation ledger API clients to preserve fixed same-origin route templates and encoded dynamic segments.
- Encoded dynamic invocation ledger identifiers for collection/detail, prompt snapshot, tags, tag deletion, and redaction helper paths in `web/lib/worlds/invocations.ts`.
- Added focused Web invocation ledger helper tests proving reserved characters stay inside identifier path segments across representative read and state-changing invocation helpers.

## Verification This Batch

- `cd web && npm run test -- lib/worlds/invocations.test.ts`: 3 passed.
- `cd web && npm run lint`: passed.
- `cd web && npm run typecheck`: passed.
- `cd web && npm run test`: 44 files and 146 tests passed. Existing React act warnings appeared in runtime-admin test output, but the suite passed.
- `cd web && npm run build`: passed.
- `cd web && npm run test:e2e`: 21 passed.
- `cd web && npm run check:next-env`: initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`: passed.
- `openspec validate --changes --strict`: 1 passed.
- `openspec validate --specs --strict`: 76 passed.
- `git diff --check`: passed before commit.

## Remaining Work

1. Continue Web/e2e security audit for remaining Next route handlers, CSRF forwarding, method exposure, response header behavior, client-side data leaks, XSS-prone rendering sinks, and other client helper path construction outside this scoped invocation-ledger API batch.
2. Audit project Playwright/e2e stability and boundary coverage without browser/computer-use plugins.
3. Continue product normal-use flows and spec/history drift audits after the remaining Web/e2e security pass.

## Finding F-038

- Browser-side invocation ledger same-origin API URL construction appended decoded world/invocation/tag identifiers directly to frontend API paths.
- The remediation encodes dynamic segments for invocation collection/detail, prompt snapshot, tags, tag deletion, and redaction helper paths, while preserving filters as query data.
- Residual risk: other Web client helpers, diagnostics helpers, server-side Web data loaders, and Next route handlers still contain dynamic path constructions that need separate evidence-based review before broad remediation.
