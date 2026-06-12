# Active Session Handoff

- Date: 2026-06-12T10:51:39+00:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-105 are remediated on this branch; latest batch is F-105 Web agent memory search CSRF hardening.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-105 batch: 25704b1 fix(web-visual): require csrf for resolver previews.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server status was rechecked before this continuation: branch matched origin at ed1aab4 before F-104 and was clean/synced again after F-104; OpenSpec specs strict validation passed with 76 specs; Noveland Postgres and NATS were healthy.
- Only .env.example was observed in the repo; do not read or expose real secrets.

## Guardrails

- Current user instruction: use SSH/CLI only; avoid browser/computer-use plugins and other non-CLI tooling that may interrupt the session.
- User explicitly requested every commit be pushed; push after successful commits unless the user changes that instruction.
- Do not bypass OpenSpec; add or update spec deltas before behavior-changing fixes.
- Keep real-provider tests opt-in only; do not set NOVELAND_RUN_REAL_PROVIDER_TESTS=1 without explicit user authorization.
- Preserve provider execution through ProviderExecutionService, quota-before-adapter execution, secret redaction, invocation ledger boundaries, media boundaries, worldline isolation, and reader/member/player DTO safety.
- Do not expose resolved secrets, disallowed auth refs, storage URIs, filesystem/object paths, local model paths, raw prompts, raw outputs, prompt snapshot internals, invite tokens, bytes, or base64.
- Do not broaden worlds.py into a catch-all router.
- For UI/e2e use project Playwright/e2e only.

## Completed This Batch

- Continued Web/e2e security audit after F-104, focusing on remaining POST helpers without CSRF.
- Recorded/remediated F-105: Web `searchAgentMemory` issued a world-scoped request-body POST without `csrf: true`, unlike adjacent agent memory/persona/observation/run/narrative mutation helpers.
- Updated architecture-contracts OpenSpec before implementation.
- Added CSRF to the agent memory search POST helper.
- Updated world client regression coverage to assert `memory/search` carries `X-CSRF-Token` while retaining URL and body assertions.

## Verification This Batch

- `cd web && npm run test -- lib/worlds/client.test.ts` first failed against the unpatched helper with a missing memory-search CSRF header, then passed with 35 tests after remediation.
- `cd web && npm run test -- lib/worlds/client.test.ts lib/worlds/proxy.test.ts lib/admin/api-client.test.ts` passed with 44 tests.
- `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed.
- Full `cd web && npm run test` passed with 52 files and 195 tests; existing RuntimeAdmin React `act(...)` warnings remained warnings, not failures.
- `cd web && npm run build` passed with `next-env.d.ts` restored and checked.
- `cd web && npm run test:e2e` passed with 21 tests, with `next-env.d.ts` restored and `cd web && npm run check:next-env` passing afterward.
- OpenSpec strict validations and `git diff --check` passed after docs update.

## Remaining Work

1. Continue Web/e2e audit for remaining route handlers, proxy method exposure, response shaping, role boundary, client-side rendering sinks, and local query construction.
2. Continue backend audits for remaining reader/member/player DTO exposure boundaries and sanitizer normalization drift, especially Web/server route response shaping, worlds public JSON helpers, and product normal-use paths.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Push after successful commits unless the user changes that instruction.

## Finding F-105

- Web agent memory search POST helpers must use the same double-submit CSRF boundary as adjacent world-scoped request-body POST helpers.
- The remediation adds `csrf: true` to `searchAgentMemory` and updates regression coverage so `memory/search` forwards `X-CSRF-Token`.
- Residual risk: continue remaining Web route-handler, proxy, client rendering, response-shaping, product-flow, and spec-history drift audits.
