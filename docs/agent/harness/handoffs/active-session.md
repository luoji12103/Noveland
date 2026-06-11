# Active Session Handoff

- Date: 2026-06-12T19:31:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-057 are remediated on this branch.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-057 commit: 822f41c fix(memory): reject raw backend secrets.
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
- Continued Web rendering audit and recorded/remediated F-057: reader media descriptor `download_url` conversion accepted arbitrary same-origin `/worlds/...` or `/api/worlds/...` paths before image/audio rendering.
- Added an architecture-contracts OpenSpec scenario requiring Web reader media rendering to accept only exact UUID reader-media object download routes and reject query, fragment, extra path, non-reader route, and non-backend scheme values.
- Tightened `readerMediaObjectDownloadPath()` to normalize backend reader media URLs to `/api/...`, return `null` for rejected descriptor URLs, and keep playback/scene components on their existing missing-media fallback path.
- Updated media helper and playback/scene component tests to use backend-contract UUID download URLs and assert rejected descriptor URL shapes.

## Verification This Batch

- `cd web && npm run test -- lib/worlds/media.test.ts features/worlds/conversation-playback.test.tsx features/worlds/conversation-scene-view.test.tsx`: 3 files and 13 tests passed.
- `cd web && npm run lint`: passed.
- `cd web && npm run typecheck`: passed.
- `cd web && npm run test`: 51 files and 177 tests passed, with existing runtime-admin React act warnings.
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

## Finding F-057

- Reader playback/scene media conversion accepted broad `/worlds/...` and `/api/worlds/...` descriptor URLs before rendering them as image/audio sources.
- The remediation accepts only exact UUID reader-media object download routes and rejects non-backend schemes, query strings, fragments, extra path segments, alternate world routes, and non-UUID paths.
- Residual risk: remaining Web route handlers/proxies and client-rendering surfaces still need separate evidence-based review before remediation.
