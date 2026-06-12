# Active Session Handoff

- Date: 2026-06-13T16:24:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-122 are remediated on this branch; latest batch is F-122 Web proxy structured JSON error redaction.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-122 batch: 9d2da26 fix(dashboard): redact runtime status text.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server status was rechecked before this continuation: branch matched origin at 9d2da26, worktree started clean for F-122 after F-121 push, active OpenSpec strict validation passed, specs strict validation passed with 76 specs, and Noveland Postgres/NATS were healthy.
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

- Continued Web proxy security audit after F-121 from a clean pushed branch.
- Identified F-122: `buildProxyResponse()` only sanitized non-2xx `application/json` proxy error bodies, while structured JSON media types such as `application/problem+json` bypassed sensitive body cleanup.
- Extended the architecture-contracts proxy error scenario to require `application/json` and `application/*+json` redaction behavior.
- Added a focused Vitest regression covering `application/problem+json`, sensitive nested `detail` values, and stale content-length removal after sanitization.
- Changed proxy error content-type classification to strip parameters and accept exact `application/json` or media types ending in `+json`.

## Verification This Batch

- `cd web && npm run test -- lib/auth/proxy.test.ts` first failed because `application/problem+json` retained the original sensitive body and content length, then passed with 7 tests after remediation.
- `cd web && npm run typecheck -- --pretty false` passed.
- `cd web && npm run lint -- lib/auth/proxy.ts lib/auth/proxy.test.ts` passed via the project lint script.
- Full `cd web && npm run test` passed with 52 test files and 207 tests.

## Remaining Work

1. Continue Web/e2e audit for remaining proxy content-type edges, streaming redaction assumptions, server-side loader response DTOs, client-side text sinks, playback empty states when media descriptors are absent, route handlers, and role boundaries.
2. Continue backend audits for remaining observability filters, invocation-adjacent filters, media object/reference subroutes, and member/player DTOs.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Push after successful commits unless the user changes that instruction.

## Finding F-122

- Web proxy error redaction should cover structured JSON error content types, not only exact `application/json`.
- The remediation preserves safe JSON, binary/no-content, streaming, and auth cookie relay behavior while routing `+json` error bodies through the existing sanitizer.
- Residual risk: continue auditing event-stream assumptions and remaining Web text sinks.
