# Active Session Handoff

- Date: 2026-06-12T02:05:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-053 are remediated on this branch.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-053 batch: 469eee8 fix(web): encode server loader backend paths.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services: Noveland Postgres is healthy on 55432->5432; Noveland NATS is healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started for this batch; project Playwright e2e used its own test server.
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

- Reconfirmed realtime git/OpenSpec/service/test-entry status from the server before editing.
- Continued the Web/e2e security audit on browser-side local app route construction after F-052.
- Recorded and remediated F-053: Web UI links embedded decoded world, agent, conversation, narrative artifact, resume conversation, and imported world identifiers directly into local `/worlds/...` app routes.
- Added an architecture-contracts OpenSpec delta requiring Web UI local app route links to preserve route boundaries with encoded dynamic segments.
- Encoded existing local app route links and browser navigation paths in worlds index, agent list, conversation list, workspace shell, player interactions, world overview, conversation playback, conversation scene view, and narrative reader components.
- Added reserved-character component regression coverage for the affected link and redirect surfaces, including new coverage for worlds index and conversation list.
- Restored `web/next-env.d.ts` after Playwright/Next dev regenerated it to `.next/dev/types/routes.d.ts`.

## Verification This Batch

- `cd web && npm run test -- features/agents/agent-list.test.tsx features/conversations/conversation-list.test.tsx features/workspace/workspace-shell.test.tsx features/worlds/worlds-index.test.tsx features/worlds/player-interactions.test.tsx features/worlds/conversation-playback.test.tsx features/worlds/conversation-scene-view.test.tsx features/worlds/narrative-reader.test.tsx features/worlds/world-overview.test.tsx`: 9 files and 25 tests passed.
- Focused source scan for raw local `/worlds/` route interpolation patterns in `web/features`, `web/components`, and `web/app`: no matches.
- `cd web && npm run typecheck`: passed.
- `cd web && npm run lint`: passed.
- `cd web && npm run test`: 49 files and 169 tests passed. Existing React act warnings appeared in runtime-admin test output, but the suite passed.
- `cd web && npm run build`: passed.
- `cd web && npm run test:e2e`: 21 passed.
- `cd web && npm run check:next-env`: failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`: passed.
- `openspec validate --changes --strict`: passed with 1 passed.
- `openspec validate --specs --strict`: passed with 76 specs.
- `git diff --check`: passed.

## Remaining Work

1. Continue Web/e2e security audit on remaining Next route handlers and proxy modules for CSRF forwarding, method exposure, response header behavior, role boundary, evidence redaction, and client-side data leaks.
2. Audit Web rendering and project Playwright/e2e coverage for XSS-prone sinks, admin/player/member boundary gaps, and normal-use product flow drift without browser/computer-use plugins.
3. Continue product normal-use and spec/history drift audit after Web route/proxy review.

## Finding F-053

- Browser-side Web UI local app route links appended decoded world and nested identifiers directly to `/worlds/...` paths.
- The remediation encodes dynamic identifier path segments for the scoped component group while preserving existing media download helper behavior.
- Residual risk: Next route handlers/proxy modules still need separate evidence-based review for CSRF forwarding, method exposure, response shaping, and forbidden-data leaks before remediation.
