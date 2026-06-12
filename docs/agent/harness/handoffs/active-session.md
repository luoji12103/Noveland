# Active Session Handoff

- Date: 2026-06-12T11:59:21+00:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-109 are remediated on this branch; latest batch is F-109 Web proxy JSON error body normalization.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-109 batch: d79694b fix(web-server): sanitize loader error details.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server status was rechecked before this continuation: branch matched origin at d79694b after F-108, worktree contained only the in-progress F-109 files, and prior OpenSpec specs strict validation passed with 76 specs.
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

- Continued Web/e2e security audit after F-108, focusing on same-origin Web proxy response bodies that reach browser network clients.
- Recorded/remediated F-109: central Web API proxy responses could relay non-2xx backend JSON error bodies containing sensitive backend internals even after UI-visible error text normalization.
- Updated architecture-contracts OpenSpec before implementation to require Web API proxies normalize backend JSON error bodies while preserving successful JSON, binary/no-content responses, streaming, and explicit auth cookie relay behavior.
- Routed `buildProxyResponse()` through centralized non-2xx JSON error-body sanitization using shared backend-error detail detection and normalization.
- Preserved successful JSON and binary responses, 204 bodies, streaming proxy responses, and explicit auth `Set-Cookie` relay behavior; stale `content-length` is dropped only when a response body is sanitized.
- Added regression coverage for dirty proxied JSON `detail` payloads carrying raw prompt, bearer token, storage URI, and media URI markers, plus safe JSON errors that must retain their original body and `content-length`.

## Verification This Batch

- `cd web && npm run test -- lib/auth/proxy.test.ts` first failed against unpatched `buildProxyResponse()` because raw backend JSON detail was relayed, then passed with 6 tests after remediation.
- `cd web && npm run test -- lib/auth/proxy.test.ts lib/api-proxy.test.ts lib/worlds/proxy.test.ts lib/runtime/proxy.test.ts lib/private-beta/proxy.test.ts lib/realtime/proxy.test.ts` passed with 6 files and 19 tests.
- `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed.
- Full `cd web && npm run test` passed with 52 files and 205 tests; existing RuntimeAdmin React `act(...)` warnings remained warnings, not failures.
- `cd web && npm run build` passed with `next-env.d.ts` restored and checked.
- `cd web && npm run test:e2e` passed with 21 tests, with `next-env.d.ts` restored and `cd web && npm run check:next-env` passing afterward.
- OpenSpec strict validations and `git diff --check` passed after docs update.

## Remaining Work

1. Continue Web/e2e audit for remaining route handlers, proxy method exposure, server-side loader response DTOs, role boundary, client-side rendering sinks, and local query construction.
2. Continue backend audits for remaining reader/member/player DTO exposure boundaries and sanitizer normalization drift, especially Web/server route response shaping, worlds public JSON helpers, and product normal-use paths.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Push after successful commits unless the user changes that instruction.

## Finding F-109

- Web same-origin proxies must normalize non-2xx backend JSON error bodies before relaying them to browser clients, because devtools/network consumers can observe those bodies even when UI messages are generic.
- The remediation sanitizes sensitive-looking keys and values through `buildProxyResponse()` for JSON error responses, preserving safe review status fields and existing success/binary/no-content/streaming/cookie behavior.
- Residual risk: continue remaining Web route-handler, proxy method exposure, server-loader response DTO, client rendering, product-flow, and spec-history drift audits.
