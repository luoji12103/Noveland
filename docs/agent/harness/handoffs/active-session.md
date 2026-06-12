# Active Session Handoff

- Date: 2026-06-13T16:30:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-123 are remediated on this branch; latest batch is F-123 Web event-stream setup error redaction.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-123 batch: 96c113e fix(proxy): sanitize structured json errors.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server status was rechecked before this continuation: branch matched origin at 96c113e, worktree started clean for F-123 after F-122 push, active OpenSpec strict validation passed, specs strict validation passed with 76 specs, and Noveland Postgres/NATS were healthy.
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

- Continued Web realtime proxy security audit after F-122 from a clean pushed branch.
- Identified F-123: event-stream proxies treated every backend response as a stream, so non-2xx JSON setup errors bypassed shared proxy error redaction.
- Added an architecture-contracts scenario requiring runtime/world/conversation stream setup JSON errors to use sanitized non-stream proxy responses.
- Added a focused Vitest regression for `application/problem+json` stream setup errors with sensitive nested fields and backend `Set-Cookie` headers.
- Changed `proxyEventStream()` to route non-2xx backend responses through `buildProxyResponse()` and preserve `buildStreamingProxyResponse()` for successful streams.

## Verification This Batch

- `cd web && npm run test -- lib/realtime/proxy.test.ts` first failed because non-2xx stream setup errors retained stream headers and bypassed sanitized proxy handling, then passed with 4 tests after remediation.
- `cd web && npm run typecheck -- --pretty false` passed.
- `cd web && npm run lint -- lib/realtime/proxy.ts lib/realtime/proxy.test.ts` passed via the project lint script.
- Full `cd web && npm run test` passed with 52 test files and 208 tests.

## Remaining Work

1. Continue Web/e2e audit for remaining stream client assumptions, server-side loader response DTOs, client-side text sinks, playback empty states when media descriptors are absent, route handlers, and role boundaries.
2. Continue backend audits for remaining observability filters, invocation-adjacent filters, media object/reference subroutes, and member/player DTOs.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Push after successful commits unless the user changes that instruction.

## Finding F-123

- Web event-stream proxies should not relay non-2xx JSON setup errors as streams or bypass sensitive error redaction.
- The remediation keeps successful `text/event-stream` behavior unchanged and reuses the existing sanitized proxy response path for failed setup responses.
- Residual risk: continue auditing client assumptions when an EventSource receives sanitized non-stream errors and remaining Web text sinks.
