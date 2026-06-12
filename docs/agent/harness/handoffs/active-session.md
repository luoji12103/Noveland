# Active Session Handoff

- Date: 2026-06-12T11:27:07+00:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-107 are remediated on this branch; latest batch is F-107 Web auth error detail normalization.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-107 batch: cf69e0f fix(web-errors): sanitize backend error details.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server status was rechecked before this continuation: branch matched origin at cf69e0f after F-106, worktree started clean/synced for F-107, OpenSpec specs strict validation passed with 76 specs, and Noveland Postgres/NATS were healthy.
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

- Continued Web/e2e security audit after F-106, focusing on auth and CSRF error-response leakage into UI-visible client errors.
- Recorded/remediated F-107: Web auth client parsing preserved backend JSON `detail` as `AuthClientError.message`, allowing dirty CSRF/auth backend details to surface through generic feature notice fallbacks.
- Updated architecture-contracts OpenSpec before implementation to include auth clients in backend-error detail normalization.
- Applied shared `normalizeBackendErrorDetail` to auth response parsing with route-specific fallback messages for CSRF, login, and current-subject requests.
- Added regression coverage for dirty auth/CSRF backend detail while preserving safe failed-login status handling.

## Verification This Batch

- `cd web && npm run test -- lib/auth/client.test.ts` first failed with 1 failure against the unpatched auth client, then passed with 7 tests after remediation.
- `cd web && npm run test -- lib/auth/client.test.ts lib/admin/api-client.test.ts lib/worlds/client.test.ts lib/worlds/media.test.ts lib/private-beta/client.test.ts lib/beta-feedback/client.test.ts` passed with 60 tests.
- `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed.
- Full `cd web && npm run test` passed with 52 files and 201 tests; existing RuntimeAdmin React `act(...)` warnings remained warnings, not failures.
- `cd web && npm run build` passed with `next-env.d.ts` restored and checked.
- `cd web && npm run test:e2e` passed with 21 tests, with `next-env.d.ts` restored and `cd web && npm run check:next-env` passing afterward.
- OpenSpec strict validations and `git diff --check` passed after docs update.

## Remaining Work

1. Continue Web/e2e audit for remaining route handlers, server-side loader error handling, proxy method exposure, response shaping, role boundary, client-side rendering sinks, and local query construction.
2. Continue backend audits for remaining reader/member/player DTO exposure boundaries and sanitizer normalization drift, especially Web/server route response shaping, worlds public JSON helpers, and product normal-use paths.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Push after successful commits unless the user changes that instruction.

## Finding F-107

- Web auth client error-detail parsing must normalize backend `detail` before constructing `AuthClientError` because CSRF/auth failures can be displayed by generic feature notice fallbacks.
- The remediation applies `normalizeBackendErrorDetail` to auth `parseJsonResponse` using the existing route-specific fallback messages, so sensitive-looking details fall back to safe auth text while safe failed-login behavior remains intact.
- Residual risk: continue remaining Web route-handler, server-loader, proxy, client rendering, response-shaping, product-flow, and spec-history drift audits.
