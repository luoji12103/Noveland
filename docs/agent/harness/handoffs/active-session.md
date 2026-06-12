# Active Session Handoff

- Date: 2026-06-12T10:43:36+00:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-104 are remediated on this branch; latest batch is F-104 Web visual resolver CSRF hardening.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-104 batch: ed1aab4 fix(web-providers): sanitize profile admin json.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server status was rechecked before the batch: branch matched origin at ed1aab4 with a clean worktree; OpenSpec change was active and specs strict validation passed with 76 specs; Noveland Postgres and NATS were healthy.
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

- Continued Web/e2e security audit after F-103, focusing on route/client CSRF consistency for visual admin POST helpers.
- Recorded/remediated F-104: Web visual `resolveSprite` and `resolveBackground` resolver preview POST helpers omitted `csrf: true`, unlike adjacent visual admin mutations and compose-scene.
- Updated architecture-contracts OpenSpec before implementation.
- Added CSRF to visual sprite/background resolver preview POST helpers.
- Updated visual client regression coverage to assert resolver preview and compose-scene POST requests all carry `X-CSRF-Token`.

## Verification This Batch

- `cd web && npm run test -- lib/worlds/visual.test.ts` first failed against the unpatched helpers with missing resolver CSRF headers, then passed with 4 tests after remediation.
- `cd web && npm run test -- lib/worlds/visual.test.ts lib/admin/api-client.test.ts lib/worlds/proxy.test.ts` passed with 13 tests.
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

## Finding F-104

- Web visual resolver preview POST helpers must use the same double-submit CSRF boundary as other visual admin POST/PATCH/PUT/DELETE actions.
- The remediation adds `csrf: true` to `resolveSprite` and `resolveBackground` and updates regression coverage so resolver and compose-scene requests all carry `X-CSRF-Token`.
- Residual risk: continue remaining Web route-handler, proxy, client rendering, response-shaping, product-flow, and spec-history drift audits.
