# Active Session Handoff

- Date: 2026-06-12T19:55:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-058 are remediated on this branch.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-058 commit: 23d9e5e fix(web): constrain reader media download urls.
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
- Continued Web route/proxy response-shaping audit and recorded/remediated F-058: backend reader media nosniff was dropped by Web proxy responses, and backend admin media byte downloads lacked nosniff.
- Added an architecture-contracts OpenSpec scenario requiring Web proxies to preserve safe media/byte response metadata while still stripping cookie mutation headers outside auth routes.
- Added `X-Content-Type-Options: nosniff` to backend admin media byte downloads.
- Added a safe Web proxy response-header allowlist for content type, content disposition, content length, and nosniff while preserving existing no-store cache policy and Set-Cookie stripping.
- Added backend media and Web world proxy regression coverage.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_media.py::test_media_api_upload_download_objects_and_restricted_visibility`: 1 test passed.
- `cd web && npm run test -- lib/worlds/proxy.test.ts`: 1 file and 4 tests passed.
- `cd backend && uv run pytest tests/test_api_media.py tests/test_api_reader_media.py`: 14 tests passed.
- `cd web && npm run test -- lib/auth/proxy.test.ts lib/worlds/proxy.test.ts lib/runtime/proxy.test.ts lib/private-beta/proxy.test.ts lib/api-proxy.test.ts`: 5 files and 13 tests passed.
- `cd backend && uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py`: passed.
- `cd backend && uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py`: passed.
- `cd backend && uv run pytest`: 563 passed, 8 skipped.
- `cd web && npm run lint`: passed.
- `cd web && npm run typecheck`: passed.
- `cd web && npm run test`: 51 files and 178 tests passed, with existing runtime-admin React act warnings.
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

## Finding F-058

- Reader media downloads set nosniff at the backend boundary but the Web same-origin proxy dropped it; admin media downloads did not set nosniff.
- The remediation adds nosniff to backend admin media byte downloads and preserves safe byte-response headers through Web proxies while continuing to strip backend Set-Cookie outside auth.
- Residual risk: remaining Web route handlers/proxies and client-rendering surfaces still need separate evidence-based review before remediation.
