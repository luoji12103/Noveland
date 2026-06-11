# Active Session Handoff

- Date: 2026-06-12T20:15:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-060 are remediated on this branch; F-060 is not committed yet at this handoff update.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-060 commit: 411b76f fix(web): preserve proxied request body bytes.
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
- Continued Web route/client audit and recorded/remediated F-060: browser-side EventSource subscriptions for world and conversation streams built same-origin API paths from decoded world/conversation identifiers.
- Added an architecture-contracts OpenSpec scenario requiring Web EventSource subscriptions to encode dynamic route segments before appending them to frontend API paths.
- Added `worldEventStreamPath()` and `conversationEventStreamPath()` in `web/lib/realtime.ts` and updated world overview, narrative workspace, narrative reader, and conversation detail components to use them.
- Added focused helper/component regression coverage for reserved world and conversation identifiers in EventSource paths.

## Verification This Batch

- `cd web && npm run test -- lib/realtime.test.ts features/conversations/conversation-detail.test.tsx features/worlds/world-overview.test.tsx features/worlds/narrative-workspace.test.tsx features/worlds/narrative-reader.test.tsx` passed with 5 files and 18 tests; `cd web && npm run lint` passed; `cd web && npm run typecheck` passed; full `cd web && npm run test` passed with 51 files and 184 tests, with existing RuntimeAdmin React act warnings; `cd web && npm run build` passed; `cd web && npm run test:e2e -- --grep publication blockers` passed after one initial full-suite transient miss on that test; rerun full `cd web && npm run test:e2e` passed with 21 tests; `cd web && npm run check:next-env` passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs.
- `git diff --check` passed.

## Remaining Work

1. Continue Web/e2e security audit on remaining Next route handlers and proxy modules for method exposure, response shaping beyond cookies, role boundary, evidence redaction, and client-side leaks.
2. Audit Web rendering and project Playwright/e2e coverage for XSS-prone sinks, admin/player/member boundary gaps, and normal-use product flow drift without browser/computer-use plugins.
3. Continue product normal-use and spec/history drift audit after Web route/proxy review.

## Finding F-060

- Web world/conversation EventSource subscription paths were built from decoded identifiers before the browser requested the same-origin Next API stream route.
- The remediation centralizes same-origin stream path construction in realtime helper functions that encode world and conversation identifiers, then routes world overview, narrative workspace, narrative reader, and conversation detail subscriptions through those helpers.
- Residual risk: remaining Web route handlers/proxies and client-rendering surfaces still need separate evidence-based review before closing the Web/e2e audit tasks.
