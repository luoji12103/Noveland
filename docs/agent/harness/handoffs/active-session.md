# Active Session Handoff

- Date: 2026-06-12T20:06:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-059 are remediated on this branch.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-059 commit: bedd88c fix(media): preserve response safety headers.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services at batch start: Noveland Postgres was healthy on 55432->5432; Noveland NATS was healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started outside project Web build/e2e commands.
- Only .env.example was observed in the repo; do not read or expose real secrets.

## Guardrails

- Current user instruction: use SSH/CLI only; avoid browser/computer-use plugins and other non-CLI tooling that may interrupt the session.
- Current user instruction: after each completed commit, push it to the configured remote; do not commit or push unfinished work.
- Do not bypass OpenSpec; add or update spec deltas before behavior-changing fixes.
- Keep real-provider tests opt-in only; do not set NOVELAND_RUN_REAL_PROVIDER_TESTS=1 without explicit user authorization.
- Preserve provider execution through ProviderExecutionService, quota-before-adapter execution, secret redaction, invocation ledger boundaries, media boundaries, worldline isolation, and reader/member/player DTO safety.
- Do not expose resolved secrets, disallowed auth refs, storage URIs, filesystem/object paths, local model paths, raw prompts, raw outputs, prompt snapshot internals, invite tokens, bytes, or base64.
- Do not broaden worlds.py into a catch-all router.
- For UI/e2e use project Playwright/e2e only.

## Completed This Batch

- Reconfirmed realtime git/OpenSpec/service status from the server before editing.
- Continued Web proxy request-body audit and recorded/remediated F-059: media uploads and other non-GET proxied requests were text-decoded before backend forwarding.
- Added an architecture-contracts OpenSpec scenario requiring Web proxies to preserve original request body bytes for JSON, multipart, and arbitrary byte payloads.
- Changed auth, generic API, worlds, runtime, and private-beta proxy helpers to forward non-GET request bodies as raw `ArrayBuffer` bytes and keep empty bodies absent.
- Added focused world proxy coverage for binary upload byte preservation and updated JSON body assertions for raw-byte forwarding.

## Verification This Batch

- `cd web && npm run test -- lib/worlds/proxy.test.ts lib/auth/proxy.test.ts lib/runtime/proxy.test.ts lib/private-beta/proxy.test.ts lib/api-proxy.test.ts`: 5 files and 14 tests passed.
- `cd web && npm run lint`: passed.
- `cd web && npm run typecheck`: passed.
- `cd web && npm run test`: 51 files and 179 tests passed, with existing runtime-admin React act warnings.
- `cd web && npm run build`: passed.
- `cd web && npm run test:e2e`: 21 tests passed.
- `cd web && npm run check:next-env`: initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`: passed.
- `openspec validate --changes --strict`: passed with 1 passed.
- `openspec validate --specs --strict`: passed with 76 specs.
- `git diff --check`: passed.

## Remaining Work

1. Continue Web/e2e security audit on remaining Next route handlers and proxy modules for method exposure, response shaping beyond cookies, role boundary, evidence redaction, and client-side data leaks.
2. Audit Web rendering and project Playwright/e2e coverage for XSS-prone sinks, admin/player/member boundary gaps, and normal-use product flow drift without browser/computer-use plugins.
3. Continue product normal-use and spec/history drift audit after Web route/proxy review.

## Finding F-059

- Web same-origin proxies text-decoded non-GET request bodies before forwarding, which could corrupt multipart or arbitrary binary payloads such as media uploads.
- The remediation forwards non-GET bodies as raw bytes and leaves empty bodies absent while preserving existing headers, CSRF/cookie forwarding, Set-Cookie stripping, and response safety header behavior.
- Residual risk: remaining Web route handlers/proxies and client-rendering surfaces still need separate evidence-based review before remediation.
