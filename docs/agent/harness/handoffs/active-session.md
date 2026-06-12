# Active Session Handoff

- Date: 2026-06-13T01:07:11+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-126 are remediated on this branch; latest batch is F-126 Web live command error notice redaction.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-126 batch: 743d25a fix(realtime): redact member turn text.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server status was rechecked before this continuation: branch matched origin at 743d25a, worktree started clean for F-126 after F-125 push, active OpenSpec strict validation passed, specs strict validation passed with 76 specs, and Noveland Postgres/NATS were healthy.
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

- Continued Web realtime/client-side security audit after F-125 from a clean pushed branch.
- Identified F-126: conversation detail live WebSocket `error` messages rendered `payload.message` directly into user-visible notices, bypassing shared backend-error detail normalization.
- Added an architecture-contracts scenario requiring Web live command error notices to normalize sensitive-looking text.
- Added focused component coverage proving sensitive live errors fall back to a fixed notice while safe business errors remain visible.
- Changed conversation detail live-error handling to call `normalizeBackendErrorDetail()` before rendering live command error notices.

## Verification This Batch

- `cd web && npm run test -- features/conversations/conversation-detail.test.tsx` first failed because the sensitive live WebSocket error message rendered in the notice, then passed with 6 tests after remediation.
- `cd web && npm run typecheck -- --pretty false` passed.
- `cd web && npm run lint -- features/conversations/conversation-detail.tsx features/conversations/conversation-detail.test.tsx` passed via the project lint script.
- Full `cd web && npm run test` passed with 52 test files and 209 tests.
- `cd web && npm run build` passed.
- `cd web && npm run check:next-env` passed.

## Remaining Work

1. Continue Web/e2e audit for remaining client-side text sinks, EventSource failure assumptions, reader/player media empty states, route handlers, and role boundaries.
2. Continue backend/Web realtime audits for close reason safety, live command error payloads, and remaining member/admin DTO boundaries.
3. Continue backend audits for remaining observability filters, invocation-adjacent filters, media object/reference subroutes, and member/player DTOs.
4. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
5. Push after successful commits unless the user changes that instruction.

## Finding F-126

- Web live command error notices should enforce the same sensitive backend-detail normalization as HTTP client errors.
- The remediation replaces sensitive-looking live error messages with `Live conversation command failed.` while preserving safe messages such as `Forbidden`.
- Residual risk: continue auditing EventSource failure handling and other direct client-side notice/text sinks.
