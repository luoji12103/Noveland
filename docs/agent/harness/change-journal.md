# Change Journal

## Post-v1.1 RC Audit and Hardening Web proxy request body preservation entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web same-origin proxy request body byte-preservation remediation for F-059.
- Finding: F-059 found `web/lib/worlds/media.ts` sending media uploads as `FormData` to `/api/worlds/{world_id}/media/assets/upload` while `web/lib/worlds/proxy.ts` decoded every non-GET request body with `request.text()` before forwarding it. The same text-decoding pattern existed in auth, generic API, runtime, and private-beta proxy helpers.
- Summary: Added an architecture-contracts OpenSpec scenario for Web proxy request body byte preservation, changed auth, generic API, worlds, runtime, and private-beta proxy helpers to forward non-GET request bodies as raw `ArrayBuffer` bytes, and kept empty request bodies absent when forwarding to the backend.
- Files changed: `web/lib/auth/proxy.ts`, `web/lib/api-proxy.ts`, `web/lib/worlds/proxy.ts`, `web/lib/runtime/proxy.ts`, `web/lib/private-beta/proxy.ts`, `web/lib/worlds/proxy.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Updated world proxy JSON-body assertions to decode the forwarded `ArrayBuffer`, and added binary upload coverage proving non-UTF-8 bytes survive proxy forwarding unchanged while existing cookie, CSRF, query, Set-Cookie stripping, and safe response-header coverage still passes.
- Verification: `cd web && npm run test -- lib/worlds/proxy.test.ts lib/auth/proxy.test.ts lib/runtime/proxy.test.ts lib/private-beta/proxy.test.ts lib/api-proxy.test.ts` passed with 5 files and 14 tests; `cd web && npm run lint` passed; `cd web && npm run typecheck` passed; full `cd web && npm run test` passed with 51 files and 179 tests, with existing runtime-admin React act warnings; `cd web && npm run build` passed; `cd web && npm run test:e2e` passed with 21 tests; `cd web && npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import. `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue Web/e2e audit on remaining route handler method exposure, proxy response/request edge cases, role-boundary rendering, client-side leaks, and product normal-use drift. Current user instruction remains SSH/CLI-only, and completed commits should be pushed immediately while incomplete work remains uncommitted.

## Post-v1.1 RC Audit and Hardening media response safety header boundary entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend media byte download response and Web proxy safe response-header preservation remediation for F-058.
- Finding: F-058 found reader media downloads setting `X-Content-Type-Options: nosniff` at the backend boundary while `web/lib/auth/proxy.ts` `buildProxyResponse()` dropped that header through same-origin Web API proxies. Admin media downloads in `backend/services/api/src/noveland/services/api/media.py` also returned raw media bytes without a nosniff header.
- Summary: Added an architecture-contracts OpenSpec scenario for Web proxy media response safety headers, added nosniff to backend admin media byte downloads, and changed `buildProxyResponse()` to preserve a small safe response-header allowlist (`content-type`, `content-disposition`, `content-length`, and `x-content-type-options`) while continuing to strip backend `Set-Cookie` unless auth proxy calls explicitly opt in.
- Files changed: `backend/services/api/src/noveland/services/api/media.py`, `backend/tests/test_api_media.py`, `web/lib/auth/proxy.ts`, `web/lib/worlds/proxy.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Expanded media API download coverage to assert admin media downloads set nosniff for normal and platform-admin hidden-object downloads; added world proxy coverage proving media safety headers are preserved while backend `Set-Cookie` remains stripped.
- Verification: `cd backend && uv run pytest tests/test_api_media.py::test_media_api_upload_download_objects_and_restricted_visibility` passed with 1 test; `cd web && npm run test -- lib/worlds/proxy.test.ts` passed with 1 file and 4 tests; `cd backend && uv run pytest tests/test_api_media.py tests/test_api_reader_media.py` passed with 14 tests; `cd web && npm run test -- lib/auth/proxy.test.ts lib/worlds/proxy.test.ts lib/runtime/proxy.test.ts lib/private-beta/proxy.test.ts lib/api-proxy.test.ts` passed with 5 files and 13 tests; `cd backend && uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py` passed; `cd backend && uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py` passed; `cd backend && uv run pytest` passed with 563 tests and 8 skipped; `cd web && npm run lint` passed; `cd web && npm run typecheck` passed; full `cd web && npm run test` passed with 51 files and 178 tests, with existing runtime-admin React act warnings; `cd web && npm run build` passed; `cd web && npm run test:e2e` passed with 21 tests; `cd web && npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import. `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue Web/e2e audit on remaining route handler method exposure, proxy response shaping beyond the safe allowlist, role-boundary rendering, client-side leaks, and product normal-use drift. Current user instruction remains SSH/CLI-only, and completed commits should be pushed immediately while incomplete work remains uncommitted.

## Post-v1.1 RC Audit and Hardening Web reader media download route boundary entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Browser-side Web reader playback and scene media descriptor download URL boundary remediation for F-057.
- Finding: F-057 found `web/lib/worlds/media.ts` accepting any descriptor `download_url` beginning with `/api/worlds/` or `/worlds/` and returning it for `<audio src>` or CSS `url(...)` rendering in `web/features/worlds/conversation-playback.tsx` and `web/features/worlds/conversation-scene-view.tsx`, while the backend reader media service emits only `/worlds/{world_uuid}/reader/media/objects/{object_uuid}/download` paths.
- Summary: Added an architecture-contracts OpenSpec scenario for reader media rendering path boundaries, tightened `readerMediaObjectDownloadPath()` to accept only exact UUID reader-media object download routes and return `null` for non-backend schemes, query strings, fragments, extra path segments, alternate world routes, or non-UUID test paths, and updated playback/scene fixtures to use backend-contract UUID media URLs.
- Files changed: `web/lib/worlds/media.ts`, `web/lib/worlds/media.test.ts`, `web/features/worlds/conversation-playback.test.tsx`, `web/features/worlds/conversation-scene-view.test.tsx`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Expanded media helper coverage for accepted `/worlds/.../reader/media/objects/.../download` and `/api/worlds/.../reader/media/objects/.../download` UUID paths plus rejected `media://`, query, extra-path, non-reader media, and non-UUID descriptor URLs; updated playback and scene component tests to assert rendered safe media uses backend-contract UUID download paths.
- Verification: `cd web && npm run test -- lib/worlds/media.test.ts features/worlds/conversation-playback.test.tsx features/worlds/conversation-scene-view.test.tsx` passed with 3 files and 13 tests; `cd web && npm run lint` passed; `cd web && npm run typecheck` passed; full `cd web && npm run test` passed with 51 files and 177 tests, with existing runtime-admin React act warnings; `cd web && npm run build` passed; `cd web && npm run test:e2e` passed with 21 tests; `cd web && npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue Web/e2e audit on remaining Next route handlers, proxy method/response shaping, admin/player/member boundary rendering, and product normal-use drift. Current user instruction remains SSH/CLI-only, and completed commits should be pushed immediately while incomplete work remains uncommitted.

## Post-v1.1 RC Audit and Hardening Memory backend profile secret-reference boundary entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend memory backend profile config and secret-reference persistence boundary remediation for F-056.
- Finding: F-056 found `MemoryBackendProfileService` persisting `vector_store_config`, `llm_config`, `embedder_config`, `reranker_config`, and `secret_refs` directly from API requests while runtime APIs returned those fields and Web admin rendered `secret_refs` back into form state. The mem0 backend treats `secret_refs` as lookup keys into `NOVELAND_MEMORY_BACKEND_SECRETS_JSON`, but no validation prevented direct `api_key` config or obvious raw secret values from being stored and returned.
- Summary: Added an architecture-contracts OpenSpec scenario for memory backend profile secret-reference boundaries, added service-layer validation that rejects sensitive config keys and raw-secret-looking config values, validates `secret_refs` as non-empty single reference names, and preserves safe reference lookup behavior.
- Files changed: `backend/packages/memory/src/noveland/memory/service.py`, `backend/tests/test_memory_backend.py`, `backend/tests/test_api_runtime.py`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added memory service and runtime API regressions proving direct secret config and raw secret refs are rejected while safe reference names persist and are returned without echoing rejected secret material.
- Verification: `cd backend && uv run pytest tests/test_memory_backend.py::test_memory_backend_profile_rejects_raw_secret_material tests/test_api_runtime.py::test_memory_backend_profile_api_rejects_raw_secret_material` passed with 2 tests; `cd backend && uv run pytest tests/test_memory_backend.py tests/test_api_runtime.py` passed with 26 tests; `cd backend && uv run ruff check .` passed; `cd backend && uv run mypy .` passed; `cd backend && uv run pytest` passed with 563 passed and 8 skipped; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue Web/e2e audit on remaining Next route handler method exposure, response shaping, role boundary, evidence redaction, and client-side rendering sinks. Current user instruction remains SSH/CLI-only, and completed commits should be pushed immediately while incomplete work remains uncommitted.

## Post-v1.1 RC Audit and Hardening Auth login CSRF boundary entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend auth login session-cookie creation and Web auth client login CSRF request construction for F-055.
- Finding: F-055 found backend `/auth/login` creating `noveland_session` and `noveland_csrf` cookies without requiring double-submit CSRF, while the Web login client did not send `X-CSRF-Token` even though the login form had pre-fetched a CSRF cookie.
- Summary: Added an architecture-contracts OpenSpec scenario for CSRF-protected login, required `require_csrf(request)` before backend login session creation, moved Web login CSRF acquisition into `web/lib/auth/client.ts`, and kept logout CSRF behavior intact.
- Files changed: `backend/services/api/src/noveland/services/api/auth.py`, `backend/tests/test_api_auth.py`, `backend/tests/test_api_auth_integration.py`, `web/lib/auth/client.ts`, `web/lib/auth/client.test.ts`, `web/features/auth/login-form.tsx`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added backend regression coverage proving login rejects missing CSRF before setting session cookies, updated backend auth/integration login helpers to send explicit double-submit CSRF headers, and expanded Web auth client coverage for CSRF fetch/header behavior, existing-cookie reuse, failed login, logout CSRF, and exact cookie reads.
- Verification: `cd backend && uv run pytest tests/test_api_auth.py` passed with 7 tests; `cd backend && uv run pytest tests/test_api_auth_integration.py` skipped 3 integration tests because `NOVELAND_TEST_DATABASE_URL` was not set; `cd backend && uv run ruff check .` passed; `cd backend && uv run mypy .` passed; `cd backend && uv run pytest` passed with 561 passed and 8 skipped; `cd web && npm run test -- lib/auth/client.test.ts features/auth/login-form.test.tsx` passed with 2 files and 9 tests; `cd web && npm run typecheck` passed; `cd web && npm run lint` passed; full `cd web && npm run test` passed with 51 files and 177 tests, with existing runtime-admin React act warnings; `cd web && npm run build` passed; `cd web && npm run test:e2e` passed with 21 passed; `cd web && npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue Web/e2e audit on remaining Next route handler method exposure, response shaping, role boundary, evidence redaction, and client-side rendering sinks. Current user instruction remains SSH/CLI-only, and completed commits should be pushed immediately while incomplete work remains uncommitted.

## Post-v1.1 RC Audit and Hardening Web non-auth proxy Set-Cookie boundary entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web same-origin non-auth proxy response cookie-mutation boundary remediation for F-054.
- Finding: F-054 found the shared `buildProxyResponse()` helper in `web/lib/auth/proxy.ts` unconditionally forwarding backend `Set-Cookie` headers while non-auth proxy helpers in `web/lib/api-proxy.ts`, `web/lib/worlds/proxy.ts`, `web/lib/runtime/proxy.ts`, and `web/lib/private-beta/proxy.ts` reused that helper.
- Summary: Added an architecture-contracts OpenSpec scenario for non-auth Web proxies, made `Set-Cookie` relay opt-in on `buildProxyResponse()`, kept `proxyAuthRequest()` explicitly opted in for login/logout/CSRF flows, and left non-auth proxies on the existing status/body/content-type/cache-control relay contract without cookie mutation headers.
- Files changed: `web/lib/auth/proxy.ts`, `web/lib/auth/proxy.test.ts`, `web/lib/worlds/proxy.test.ts`, `web/lib/runtime/proxy.test.ts`, `web/lib/api-proxy.test.ts`, `web/lib/private-beta/proxy.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added focused coverage proving auth proxy requests continue relaying backend cookie mutations while generic API, world, runtime, and private beta non-auth proxies strip backend `Set-Cookie` headers.
- Verification: `npm run test -- lib/auth/proxy.test.ts lib/worlds/proxy.test.ts lib/runtime/proxy.test.ts lib/private-beta/proxy.test.ts lib/api-proxy.test.ts` passed with 5 files and 12 tests; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 51 files and 175 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue Web/e2e audit on remaining Next route handler method exposure, response shaping beyond cookies, role boundary, evidence redaction, and client-side rendering sinks. Current user instruction remains SSH/CLI-only, and completed commits should be pushed immediately while incomplete work remains uncommitted.

## Post-v1.1 RC Audit and Hardening Web UI local app route link path boundary entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Browser-side Web local app route link and navigation path-boundary remediation for F-053.
- Finding: F-053 found workspace navigation, world index navigation, agent builder links, conversation transcript links, player resume/privacy links, overview shortcut links, reader playback/scene links, and narrative reader links constructing `/worlds/...` local app routes from decoded world and nested identifiers without encoding every dynamic segment.
- Summary: Added an architecture-contracts OpenSpec delta for Web UI local app links, encoded world, agent, conversation, narrative artifact, resume conversation, imported world, and overview shortcut route segments at the existing component call sites, and preserved existing media download helpers.
- Files changed: `web/features/worlds/worlds-index.tsx`, `web/features/agents/agent-list.tsx`, `web/features/conversations/conversation-list.tsx`, `web/features/workspace/workspace-shell.tsx`, `web/features/worlds/player-interactions.tsx`, `web/features/worlds/world-overview.tsx`, `web/features/worlds/conversation-playback.tsx`, `web/features/worlds/conversation-scene-view.tsx`, `web/features/worlds/narrative-reader.tsx`, focused Web tests, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added reserved-character route-link coverage for worlds index, agent list, conversation list, workspace shell navigation, player resume/privacy links, overview shortcuts, playback/scene navigation, and narrative reader list/detail links.
- Verification: `npm run test -- features/agents/agent-list.test.tsx features/conversations/conversation-list.test.tsx features/workspace/workspace-shell.test.tsx features/worlds/worlds-index.test.tsx features/worlds/player-interactions.test.tsx features/worlds/conversation-playback.test.tsx features/worlds/conversation-scene-view.test.tsx features/worlds/narrative-reader.test.tsx features/worlds/world-overview.test.tsx` passed with 9 files and 25 tests; a focused source scan for raw local `/worlds/` route interpolation patterns in `web/features`, `web/components`, and `web/app` returned no matches; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 49 files and 169 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue Web/e2e audit on remaining Next route handlers and proxy modules, especially CSRF forwarding, method exposure, response header behavior, role boundary, evidence redaction, and client-side rendering sinks. Current user instruction remains SSH/CLI-only, and completed commits should be pushed immediately while incomplete work remains uncommitted.

## Post-v1.1 RC Audit and Hardening Web server workspace loader backend path boundary entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Server-rendered Web world workspace, agent, conversation, player, reader, worldline, and memory backend admin loader backend API path-boundary remediation for F-052.
- Finding: F-052 found `web/lib/worlds/server.ts` building backend API paths from decoded `worldId`, `agentId`, `conversationId`, `artifactId`, worldline IDs, backend record IDs, and memory backend profile IDs without encoding every dynamic segment.
- Summary: Added an architecture-contracts OpenSpec delta for Web server workspace loaders, then routed world paths through `serverWorldPath()` and nested identifiers through `pathSegment()` while preserving existing query filters as query data. This extends the earlier admin-loader path-boundary hardening to the remaining server-rendered workspace loaders and platform memory backend loader.
- Files changed: `web/lib/worlds/server.ts`, `web/lib/worlds/server.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Expanded Web server loader coverage to exercise representative workspace, agent detail, conversation detail/playback, player interaction, worldline comparison, narrative reader detail, and memory backend admin paths with identifiers containing `/`, `?`, and `#`.
- Verification: `npm run test -- lib/worlds/server.test.ts` passed with 2 tests; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 47 files and 163 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue Web/e2e audit for remaining Next route handlers and proxy modules, especially CSRF forwarding, response header behavior, method exposure, role boundary, evidence redaction, and client-side rendering sinks. Current user instruction for this session is SSH/CLI-only, and completed commits should be pushed immediately while incomplete work remains uncommitted.

## Post-v1.1 RC Audit and Hardening Web private beta/beta feedback client path boundary entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Browser-side Web same-origin private beta onboarding, beta feedback, and player-surface route path-boundary remediation for F-051.
- Finding: F-051 found `web/lib/private-beta/client.ts`, `web/lib/beta-feedback/client.ts`, and `web/features/private-beta/private-beta-onboarding.tsx` building API paths or player links from decoded `worldId`/`reportId` values without encoding dynamic path segments.
- Summary: Reused the existing architecture-contracts Web API client route-boundary delta, then encoded private beta world identifiers, beta feedback world/report identifiers, and the private beta player-surface world route segment. Feedback filters continue to use `URLSearchParams` as query data.
- Files changed: `web/lib/private-beta/client.ts`, `web/lib/private-beta/client.test.ts`, `web/lib/beta-feedback/client.ts`, `web/lib/beta-feedback/client.test.ts`, `web/features/private-beta/private-beta-onboarding.tsx`, `web/features/private-beta/private-beta-onboarding.test.tsx`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added private beta and beta feedback client coverage proving world/report identifiers containing `/`, `?`, and `#` stay encoded inside same-origin API path segments; updated private beta onboarding component coverage proving the player-surface link encodes the world route segment without leaking invite tokens or internal fields.
- Verification: `npm run test -- lib/private-beta/client.test.ts lib/beta-feedback/client.test.ts features/private-beta/private-beta-onboarding.test.tsx` passed with 3 files and 6 tests; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 47 files and 162 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue Web/e2e audit for remaining client/proxy modules and Next route handlers, especially CSRF forwarding, response header behavior, role boundary, evidence redaction, and client-side rendering sinks. Current user instruction for this session is SSH/CLI-only, and completed commits should be pushed immediately while incomplete work remains uncommitted.

## Post-v1.1 RC Audit and Hardening Web admin preset/memory/provider API client path boundary entry

- Date: 2026-06-10
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Browser-side Web same-origin platform admin preset, memory backend, memory write job, and provider profile API path-boundary remediation for F-050.
- Finding: F-050 found `web/lib/worlds/client.ts` building agent preset, memory backend profile, memory write job retry, and provider profile helper URLs from decoded preset/profile/job identifiers without encoding dynamic path segments.
- Summary: Added an architecture-contracts OpenSpec delta requiring platform admin Web helpers to preserve same-origin route boundaries, then encoded preset, memory backend profile, memory write job, and provider profile identifiers for the scoped helper group. Existing memory log/job filters remain query data.
- Files changed: `web/lib/worlds/client.ts`, `web/lib/worlds/client.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added Web worlds client helper coverage proving preset, memory backend profile, memory write job, and provider profile identifiers containing `/`, `?`, and `#` remain encoded inside same-origin API path segments across representative read and state-changing platform admin helpers.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 35 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 158 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue the Web/e2e security audit outside `web/lib/worlds/client.ts`, especially other client/proxy modules and Next route handlers for CSRF forwarding, method exposure, response header behavior, role boundary, evidence redaction, client-side data leaks, XSS-prone rendering sinks, and admin/player/member boundary drift. Do not use browser/computer-use plugins and do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web event/episode/group/relationship/conflict/rumor/dashboard API client path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Browser-side Web same-origin event trigger, scene beat, daily episode, group interaction, relationship suggestion, organization conflict, rumor, rumor propagation, and living-world dashboard API path-boundary remediation for F-046.
- Finding: F-046 found `web/lib/worlds/client.ts` building event trigger condition, scene beat, daily episode, group interaction, relationship suggestion, organization conflict, rumor, rumor propagation, and living-world dashboard helper URLs from decoded `worldId` and nested identifier values without encoding dynamic path segments.
- Summary: Added an architecture-contracts OpenSpec delta requiring these browser-side Web helpers to preserve same-origin route boundaries, then encoded world, condition, group context, relationship suggestion, organization conflict, and rumor propagation identifiers for the scoped helper group. Existing worldline filters remain query data built with `URLSearchParams`.
- Files changed: `web/lib/worlds/client.ts`, `web/lib/worlds/client.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added Web worlds client helper coverage proving world, worldline, condition, group context, relationship suggestion, organization conflict, and rumor propagation identifiers containing `/`, `?`, and `#` remain encoded inside same-origin API path segments or query values across representative read and state-changing helpers.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 31 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 154 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue the Web/e2e security audit for remaining `web/lib/worlds/client.ts` helper path construction outside this event/episode/group/relationship/conflict/rumor/dashboard scope, especially knowledge, secrets, emotional states, relationship repairs, player journal/notifications/interventions, reviews, agent memory/persona/observation/run, narrative artifacts, memberships, member candidates, and diagnostics helpers, plus Next route handlers, CSRF forwarding, method exposure, response header behavior, client rendering/XSS sinks, admin/player/member boundary leaks, and project e2e stability. Do not use browser/computer-use plugins and do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web organization/agent/calendar/schedule API client path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Browser-side Web same-origin organization, agent, calendar, and schedule API path-boundary remediation for F-043.
- Finding: F-043 found `web/lib/worlds/client.ts` building organization, membership, faction track, agent relationship, agent presence, agent calendar, schedule rule, and calendar conflict helper URLs from decoded `worldId` and nested identifier values without encoding dynamic path segments.
- Summary: Added an architecture-contracts OpenSpec delta requiring these browser-side Web helpers to preserve same-origin route boundaries, then encoded world, organization, membership, track, agent, relationship, calendar entry, and schedule rule identifiers for the scoped helper group. Existing filters remain query data built with `URLSearchParams`.
- Files changed: `web/lib/worlds/client.ts`, `web/lib/worlds/client.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added Web worlds client helper coverage proving world, organization, membership, track, agent, relationship, calendar entry, schedule rule, and worldline identifiers containing `/`, `?`, and `#` remain encoded inside same-origin API path segments or query values across representative read and state-changing organization/agent/calendar/schedule helpers.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 28 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 151 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue the Web/e2e security audit for remaining `web/lib/worlds/client.ts` helper path construction outside this organization/agent/calendar/schedule scope, especially daily-life/offscreen and later living-world helper groups, plus Next route handlers, CSRF forwarding, method exposure, response header behavior, client rendering/XSS sinks, admin/player/member boundary leaks, and project e2e stability. Do not use browser/computer-use plugins and do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web clock/replay/scene API client path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Browser-side Web same-origin clock, replay, snapshot, event audit, scene, and location-edge API path-boundary remediation for F-042.
- Finding: F-042 found `web/lib/worlds/client.ts` building clock, replay, snapshot, event audit, scene, and location-edge helper URLs from decoded `worldId`, `sceneId`, and `edgeId` values without encoding dynamic path segments.
- Summary: Added an architecture-contracts OpenSpec delta requiring these browser-side Web helpers to preserve same-origin route boundaries, then encoded world, scene, and location-edge identifiers for the scoped helper group. Existing filters remain query data built with `URLSearchParams`.
- Files changed: `web/lib/worlds/client.ts`, `web/lib/worlds/client.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added Web worlds client helper coverage proving world, worldline, actor-ref, event-name, scene, and location-edge identifiers containing `/`, `?`, and `#` remain encoded inside same-origin API path segments or query values across representative read and state-changing clock/replay/scene helpers.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 27 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 150 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue the Web/e2e security audit for remaining `web/lib/worlds/client.ts` helper path construction outside this clock/replay/scene scope, especially organization/agent/calendar/schedule and later living-world helper groups, plus Next route handlers, CSRF forwarding, method exposure, response header behavior, client rendering/XSS sinks, admin/player/member boundary leaks, and project e2e stability. Do not use browser/computer-use plugins and do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web core world API client path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Browser-side Web same-origin core world API path-boundary remediation for F-041.
- Finding: F-041 found `web/lib/worlds/client.ts` building core world management, worldline, GM, resolution rule, player actor, session resume, and player choice helper URLs from decoded `worldId` and nested identifier values without encoding dynamic path segments.
- Summary: Added an architecture-contracts OpenSpec delta requiring browser-side core world API clients to preserve same-origin route boundaries, then encoded world and nested identifiers for the scoped core helper group. Existing filters remain query data built with `URLSearchParams`.
- Files changed: `web/lib/worlds/client.ts`, `web/lib/worlds/client.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added Web worlds client helper coverage proving world, worldline, agenda, proposal, resolution rule, and user identifiers containing `/`, `?`, and `#` remain encoded inside same-origin API path segments or query values across representative read and state-changing core world helpers.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 26 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 149 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue the Web/e2e security audit for remaining `web/lib/worlds/client.ts` helper path construction outside this core group, Next route handlers, CSRF forwarding, method exposure, response header behavior, client rendering/XSS sinks, admin/player/member boundary leaks, and project e2e stability. Do not use browser/computer-use plugins and do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web server admin loader backend path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Server-rendered Web admin loader backend API path-boundary remediation for F-040.
- Finding: F-040 found `web/lib/worlds/server.ts` building provider, media, visual, speech, invocation, and multimodal diagnostics admin backend fetch paths from decoded `worldId` and nested backend record identifiers without encoding dynamic path segments; selected worldline filters in the same loader group were also appended without query encoding.
- Summary: Added an architecture-contracts OpenSpec delta requiring Web server admin loaders to preserve backend API route boundaries, then encoded world and nested record identifiers for the affected admin loader group. Loader query strings now use a shared `URLSearchParams` helper for this remediation scope.
- Files changed: `web/lib/worlds/server.ts`, `web/lib/worlds/server.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added Web server loader coverage proving world, provider, media asset, sprite set, agent, invocation, and worldline identifiers containing `/`, `?`, and `#` remain encoded inside representative backend API path segments or query values.
- Verification: `npm run test -- lib/worlds/server.test.ts` passed with 1 passed; `npm run lint` passed; `npm run typecheck` passed; full `npm run test` passed with 45 files and 148 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` was attempted twice and hit existing flake points, first at publication blocker after 12 passed and 8 skipped, then at scene view after 15 passed and 5 skipped; focused reruns for publication blocker and scene view passed, and a focused group covering the skipped player/privacy/worldline/release-gate/member tests passed with 5 passed; `npm run check:next-env` passed after restoring the expected `.next/types/routes.d.ts` import regenerated by e2e/dev; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed before commit.
- Follow-up notes: Continue the Web/e2e security audit for remaining server-side Web data loader path construction outside this admin-loader scope, broader `web/lib/worlds/client.ts` helper path construction, Next route handlers, CSRF forwarding, method exposure, response header behavior, client rendering/XSS sinks, admin/player/member boundary leaks, and project e2e stability. Do not use browser/computer-use plugins and do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web multimodal diagnostics API client path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Browser-side Web same-origin multimodal diagnostics API path-boundary remediation for F-039.
- Finding: F-039 found `web/lib/worlds/diagnostics.ts` building multimodal diagnostics, eval-run list/detail, and eval execution helper URLs from decoded `worldId` and `runId` values without encoding dynamic path segments.
- Summary: Added an architecture-contracts OpenSpec delta requiring browser-side multimodal diagnostics API clients to preserve same-origin route boundaries, then encoded world and eval-run identifiers for diagnostics, eval-run collection/detail, and eval execution helper paths. Existing filter objects remain query data built with `URLSearchParams`.
- Files changed: `web/lib/worlds/diagnostics.ts`, `web/lib/worlds/diagnostics.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added Web diagnostics helper coverage proving world and eval-run identifiers containing `/`, `?`, and `#` remain encoded inside same-origin API path segments across representative read and state-changing diagnostics helpers.
- Verification: `npm run test -- lib/worlds/diagnostics.test.ts` passed with 3 passed; `npm run lint` passed; `npm run typecheck` passed; full `npm run test` passed with 44 files and 147 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed before commit.
- Follow-up notes: Continue the Web/e2e security audit for remaining client helper path construction outside this diagnostics scope, server-side Web data loader path construction, Next route handlers, CSRF forwarding, method exposure, response header behavior, client rendering/XSS sinks, admin/player/member boundary leaks, and project e2e stability. Do not use browser/computer-use plugins and do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web invocation ledger API client path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Browser-side Web same-origin invocation ledger API path-boundary remediation for F-038.
- Finding: F-038 found `web/lib/worlds/invocations.ts` building model invocation list, detail, prompt snapshot, tag, tag deletion, and redaction helper URLs from decoded `worldId`, `invocationId`, and `tagId` values without encoding dynamic path segments.
- Summary: Added an architecture-contracts OpenSpec delta requiring browser-side invocation ledger API clients to preserve same-origin route boundaries, then encoded world, invocation, and tag identifiers for invocation collection/detail, prompt snapshot, tags, tag deletion, and redaction helper paths. Existing filter objects remain query data built with `URLSearchParams`.
- Files changed: `web/lib/worlds/invocations.ts`, `web/lib/worlds/invocations.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added Web invocation ledger helper coverage proving world, invocation, and tag identifiers containing `/`, `?`, and `#` remain encoded inside same-origin API path segments across representative read and state-changing invocation helpers.
- Verification: `npm run test -- lib/worlds/invocations.test.ts` passed with 3 passed; `npm run lint` passed; `npm run typecheck` passed; full `npm run test` passed with 44 files and 146 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed before commit.
- Follow-up notes: Continue the Web/e2e security audit for remaining client helper path construction outside this invocation-ledger scope, diagnostics helpers, server-side Web data loader path construction, Next route handlers, CSRF forwarding, method exposure, response header behavior, client rendering/XSS sinks, admin/player/member boundary leaks, and project e2e stability. Do not use browser/computer-use plugins and do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web media admin API client path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Browser-side Web same-origin media admin API path-boundary remediation for F-037.
- Finding: F-037 found `web/lib/worlds/media.ts` building media asset, object, reference, job, upload, and download helper URLs from decoded `worldId`, `assetId`, `jobId`, and `objectId` values without encoding dynamic path segments.
- Summary: Added an architecture-contracts OpenSpec delta requiring browser-side media admin API clients to preserve same-origin route boundaries, then encoded world, asset, job, and object identifiers for media asset collection/detail, asset objects, asset references, media references, media jobs, job cancel/retry, upload, and object download helper paths. Existing filter objects remain query data built with `URLSearchParams`.
- Files changed: `web/lib/worlds/media.ts`, `web/lib/worlds/media.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added Web media helper coverage proving world, asset, job, and object identifiers containing `/`, `?`, and `#` remain encoded inside same-origin API path segments across representative read and state-changing media helpers.
- Verification: `npm run test -- lib/worlds/media.test.ts` passed with 5 passed; `npm run lint` passed; `npm run typecheck` passed; full `npm run test` passed with 44 files and 145 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed before commit.
- Follow-up notes: Continue the Web/e2e security audit for remaining client helper path construction outside this media-admin scope, server-side Web data loader path construction, Next route handlers, CSRF forwarding, method exposure, response header behavior, client rendering/XSS sinks, admin/player/member boundary leaks, and project e2e stability. Do not use browser/computer-use plugins and do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web visual admin API client path boundary entry

- Date: 2026-06-10
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Browser-side Web same-origin visual admin API path-boundary remediation for F-036.
- Finding: F-036 found `web/lib/worlds/visual.ts` building sprite set, sprite variant, scene background, resolver, and compose-scene helper URLs from decoded `worldId`, `spriteSetId`, `variantId`, and `backgroundId` values without encoding dynamic path segments.
- Summary: Added an architecture-contracts OpenSpec delta requiring browser-side visual admin API clients to preserve same-origin route boundaries, then encoded world, sprite set, sprite variant, and background identifiers for sprite set collection/detail, sprite variants, scene backgrounds, resolver previews, and compose-scene helper paths. Existing visual filters remain query data built with `URLSearchParams`.
- Files changed: `web/lib/worlds/visual.ts`, `web/lib/worlds/visual.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added Web visual helper coverage proving world, sprite set, sprite variant, and background identifiers containing `/`, `?`, and `#` remain encoded inside same-origin API path segments across representative read and state-changing visual helpers.
- Verification: `npm run test -- lib/worlds/visual.test.ts` passed with 4 passed; `npm run lint` passed; `npm run typecheck` passed; full `npm run test` passed with 44 files and 144 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed before commit.
- Follow-up notes: Continue the Web/e2e security audit for remaining client helper path construction outside this visual-admin scope, Next route handlers, CSRF forwarding, method exposure, response header behavior, client rendering/XSS sinks, admin/player/member boundary leaks, and project e2e stability. Do not use browser/computer-use plugins and do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web speech admin API client path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Browser-side Web same-origin speech admin API path-boundary remediation for F-035.
- Finding: F-035 found `web/lib/worlds/speech.ts` building speech voice profile, agent voice binding, style mapping, transcript, TTS, and STT helper URLs from decoded `worldId`, `agentId`, `voiceProfileId`, `bindingId`, and `mappingId` values without encoding dynamic path segments.
- Summary: Added an architecture-contracts OpenSpec delta requiring browser-side speech admin API clients to preserve same-origin route boundaries, then encoded world, agent, voice profile, binding, and style mapping identifiers for speech collection/detail, agent voice binding, style mapping, transcript, TTS, and STT helper paths. Existing filter objects remain query data built with `URLSearchParams`.
- Files changed: `web/lib/worlds/speech.ts`, `web/lib/worlds/speech.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added Web speech helper coverage proving world, agent, voice profile, binding, and style mapping identifiers containing `/`, `?`, and `#` remain encoded inside same-origin API path segments across representative read and state-changing speech helpers.
- Verification: `npm run test -- lib/worlds/speech.test.ts` passed with 3 passed; `npm run lint` passed; `npm run typecheck` passed; full `npm run test` passed with 44 files and 143 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run check:next-env` passed; full `npm run test:e2e` was attempted and failed on the workspace/conversation e2e after 11 passed and 9 skipped, then the focused workspace/conversation rerun failed at a different runtime notice assertion, and a second focused rerun passed; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed before commit.
- Follow-up notes: Continue the Web/e2e security audit for remaining client helper path construction outside this speech-admin scope, Next route handlers, CSRF forwarding, method exposure, response header behavior, client rendering/XSS sinks, admin/player/member boundary leaks, and project e2e instability. Do not use browser/computer-use plugins and do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web provider integration API client path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Browser-side Web same-origin provider integration API path-boundary remediation for F-034.
- Finding: F-034 found `web/lib/worlds/provider-integrations.ts` building provider configuration, model discovery, capability, health-check, history, and smoke-test helper URLs from decoded `worldId` and `providerId` values without encoding dynamic path segments.
- Summary: Added an architecture-contracts OpenSpec delta requiring browser-side provider integration API clients to preserve same-origin route boundaries, then encoded world and provider identifiers for provider collection, templates, model-discovery, detail, capabilities, health-check, health-check history, and smoke-test helper paths. The health-check history limit remains query data built with `URLSearchParams`.
- Files changed: `web/lib/worlds/provider-integrations.ts`, `web/lib/worlds/provider-integrations.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added Web provider integration helper coverage proving world/provider identifiers containing `/`, `?`, and `#` remain encoded inside same-origin API path segments across representative read and state-changing provider helpers.
- Verification: `npm run test -- lib/worlds/provider-integrations.test.ts` passed with 5 passed; `npm run lint` passed; `npm run typecheck` passed; full `npm run test` passed with 44 files and 142 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run check:next-env` passed; `npm run test:e2e` passed with 21 passed; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed before commit.
- Follow-up notes: Continue the Web/e2e security audit for remaining client helper path construction outside this provider-integration scope, Next route handlers, CSRF forwarding, method exposure, response header behavior, client rendering/XSS sinks, admin/player/member boundary leaks, and project e2e gaps. Do not use browser/computer-use plugins and do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web conversation API client path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Browser-side Web same-origin conversation API path-boundary remediation for F-033.
- Finding: F-033 found `web/lib/worlds/client.ts` building conversation read and state-changing control helper URLs from decoded `worldId` and `conversationId` values without encoding dynamic path segments.
- Summary: Added an architecture-contracts OpenSpec delta requiring browser-side same-origin API clients to preserve route boundaries, then encoded world and conversation identifiers for scoped conversation collection/detail, participants, turns, narrative, diagnostics, seed, advance, start, pause, resume, and stop helper paths.
- Files changed: `web/lib/worlds/client.ts`, `web/lib/worlds/client.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added Web client helper coverage proving world/conversation identifiers containing `/`, `?`, and `#` remain encoded inside same-origin API path segments across representative read and state-changing conversation helpers.
- Verification: `npm run test -- lib/worlds/client.test.ts passed with 25 passed; npm run lint passed; npm run typecheck passed; full npm run test passed with 44 files and 141 tests; npm run build passed; npm run check:next-env passed; npm run test:e2e passed with 21 passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.`
- Follow-up notes: Continue the Web/e2e security audit for remaining client helper path construction outside this conversation-helper scope, Next route handlers, CSRF forwarding, method exposure, response header behavior, client rendering/XSS sinks, admin/player/member boundary leaks, and project e2e gaps. Do not use browser/computer-use plugins and do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web conversation live socket path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Browser-side Web realtime live socket path-boundary remediation for F-032.
- Finding: F-032 found `web/lib/realtime.ts` building conversation live WebSocket URLs from decoded `worldId` and `conversationId` values without encoding dynamic path segments.
- Summary: Added an architecture-contracts OpenSpec delta requiring browser-initiated realtime URLs to preserve backend route boundaries, then encoded world and conversation identifiers before opening conversation live-control sockets.
- Files changed: `web/lib/realtime.ts`, `web/lib/realtime.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added browser-side realtime helper coverage proving world/conversation identifiers containing `/`, `?`, and `#` remain encoded inside WebSocket path segments.
- Verification: `npm run test -- lib/realtime.test.ts` passed with 2 passed; `npm run lint` passed; `npm run typecheck` passed; full `npm run test` passed with 44 files and 140 tests; `npm run build` passed; `npm run check:next-env` passed; full `npm run test:e2e` was attempted and failed on the scene-view safe-media test after 15 passed and 5 skipped, then the failing scene-view test passed on focused rerun; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed before commit.
- Follow-up notes: Continue the Web/e2e security audit for remaining client helper path construction, CSRF forwarding, method exposure, response header behavior, client rendering/XSS sinks, admin/player/member boundary leaks, and project e2e gaps. Do not use browser/computer-use plugins and do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web memory backend proxy query entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web same-origin runtime proxy query preservation remediation for F-031.
- Finding: F-031 found memory backend jobs/logs route handlers embedding the request query into the backend path argument before `proxyRuntimeRequest` appended the same query again.
- Summary: Added an architecture-contracts OpenSpec delta requiring runtime proxy query parameters to be appended exactly once, then removed route-local query concatenation from memory backend jobs/logs route handlers.
- Files changed: `web/app/api/memory-backend-profiles/[profileId]/jobs/route.ts`, `web/app/api/memory-backend-profiles/[profileId]/logs/route.ts`, `web/lib/runtime/proxy.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Added runtime proxy route-handler coverage proving jobs/logs query strings are forwarded exactly once and encoded profile IDs remain path segments.
- Verification: `npm run test -- lib/runtime/proxy.test.ts` passed with 2 passed; `npm run lint` passed; `npm run typecheck` passed; full `npm run test` passed with 43 files and 138 tests; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed before commit.
- Follow-up notes: Continue the Web/e2e security audit for CSRF forwarding, method exposure, response header behavior, client rendering/XSS sinks, admin/player/member boundary leaks, and project e2e gaps. Do not use browser/computer-use plugins and do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web realtime stream proxy path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web same-origin realtime stream proxy path-boundary remediation for F-030.
- Finding: F-030 found `web/app/api/worlds/[worldId]/stream/route.ts` and `web/app/api/worlds/[worldId]/conversations/[conversationId]/stream/route.ts` forwarding decoded route parameters directly into backend stream paths without encoding.
- Summary: Added an architecture-contracts OpenSpec delta requiring Web API proxies to preserve backend route boundaries with fixed path templates and encoded dynamic segments, then encoded world and conversation stream identifiers before forwarding to backend SSE endpoints.
- Files changed: `web/app/api/worlds/[worldId]/stream/route.ts`, `web/app/api/worlds/[worldId]/conversations/[conversationId]/stream/route.ts`, `web/lib/realtime/proxy.test.ts`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Expanded realtime proxy coverage to call the world and conversation stream route handlers with decoded identifiers containing `/`, asserting the backend fetch URL keeps those slashes encoded inside identifier segments while preserving the query string.
- Verification: `npm run test -- lib/realtime/proxy.test.ts` passed with 3 passed; `npm run lint` passed; `npm run typecheck` passed; full `npm run test` passed with 42 files and 136 tests; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed before commit.
- Follow-up notes: Continue the Web/e2e security audit for remaining Next route handlers, CSRF forwarding, client rendering/XSS sinks, admin/player/member boundary leaks, and project e2e gaps. Do not use browser/computer-use plugins and do not push unless explicitly requested.

## v1.1 Normal Use / Release Candidate archive entry

- Date: 2026-05-22
- Branch: main
- Scope: OpenSpec archive, v1.1 current specs, release notes, and harness bookkeeping.
- Summary: Archived the completed v1.1 Normal Use / Release Candidate OpenSpec change, synced implemented v1.1 capabilities into current OpenSpec specs, and added v1.1 release notes.
- Files changed: `/openspec/specs/**`, `/openspec/changes/archive/2026-05-22-v1-1-normal-use-release-candidate/**`, `/docs/agent/harness/release-notes/v1.1-normal-use-release-candidate.md`, and harness docs.
- Tests added/updated: N/A.
- Docs updated: OpenSpec current specs, OpenSpec archive, v1.1 release notes, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: v1.1 is closed locally. Do not start a new version without explicit instruction. No backend/Web runtime behavior changed and no push was performed.

## v1.1 Phase 8 Release Candidate Gate merge entry

- Date: 2026-05-21
- Branch: main
- Scope: v1.1 Normal Use / Release Candidate Phase 8 merge bookkeeping.
- Summary: Fast-forward merged `feature/v1.1-8-release-candidate-gate` into local `main`, marked Phase 8 complete in OpenSpec tasks, and left v1.1 closeout/archive tasks open for explicit acceptance.
- Files changed: OpenSpec tasks, task board, active handoff, and change journal.
- Tests added/updated: N/A, merge bookkeeping only after the already-passing Phase 8 backend/OpenSpec gate.
- Docs updated: OpenSpec task `9.6`, task board, active handoff, and change journal.
- Follow-up notes: v1.1 Phase 1-8 implementation is complete locally. Do not archive v1.1 until explicitly instructed. No push performed.

## v1.1 Phase 8 Release Candidate Gate planning entry

- Date: 2026-05-21
- Branch: feature/v1.1-8-release-candidate-gate
- Scope: v1.1 Normal Use / Release Candidate Phase 8 docs-only checkpoint before backend/API implementation.
- Summary: Confirmed Phase 8 stays inside the existing observability/readiness boundary as a backend/API-only, platform-admin release-candidate gate. The report will aggregate v1.1 normal-use evidence plus prior readiness gates, distinguish RC from public launch, and avoid new readiness tables, Web UI, migrations, real provider calls, broad `worlds.py` routes, or unsafe evidence exposure.
- Files changed: `docs/agent/harness/feature-updates/v1.1.8-release-candidate-gate-plan.md`, OpenSpec task `9.1`, and harness docs.
- Tests added/updated: N/A, planning checkpoint.
- Docs updated: Phase 8 checkpoint, task board, active handoff, project index, file inventory, and change journal.
- Follow-up notes: Implement `ReleaseCandidateGateReport`, service aggregation, admin-only observability endpoint, and focused backend tests. Mark the UI task complete as not applicable because no Web UI is scoped for Phase 8.

## v1.1 Phase 8 Release Candidate Gate implementation entry

- Date: 2026-05-21
- Branch: feature/v1.1-8-release-candidate-gate
- Scope: v1.1 Normal Use / Release Candidate Phase 8 implementation only.
- Summary: Added a platform-admin release-candidate readiness report under the existing observability/readiness boundary. The report aggregates private beta gate evidence, supplied backup/restore drill evidence, deterministic normal-use stress evidence, content safety/moderation escalation evidence, import/export package metadata evidence, provider reliability evidence, user-facing polish review evidence, manual RC checklist items, and no-leak checks. It keeps `public_launch_ready=false`, adds no migrations, no Web UI, no provider execution, no duplicate readiness tables, no broad `worlds.py` routes, and no tester/player/member surface exposure.
- Files changed: `backend/packages/observability/src/noveland/observability/{contracts,services,__init__}.py`, `backend/services/api/src/noveland/services/api/observability.py`, `backend/tests/test_production_readiness_gate.py`, Phase 8 checkpoint, OpenSpec tasks through `9.4`, and harness docs.
- Tests added/updated: Added RC gate coverage for complete normal-use evidence pass, missing backup/stress/moderation/packaging/provider/UX/manual evidence failures, world-event leak blocking, admin-only endpoint access, public-launch distinction, duplicate-framework guard, and forbidden-marker response checks. Targeted checks passed: focused readiness pytest (`27 passed`), focused ruff, and focused mypy.
- Docs updated: Phase 8 checkpoint, task board, active handoff, project index, file inventory, and change journal.
- Follow-up notes: Full backend/OpenSpec gate passed: backend ruff, backend mypy (`326 source files`), backend pytest (`555 passed, 8 skipped`), OpenSpec strict changes/specs validation, and `git diff --check`. Commit Phase 8, fast-forward merge to local `main`, and record merge bookkeeping. Phase 8 has no Web UI, so `impeccable` was not required.

## v1.1 Phase 7 User-facing Polish planning entry

- Date: 2026-05-21
- Branch: feature/v1.1-7-user-facing-polish
- Scope: v1.1 Normal Use / Release Candidate Phase 7 docs-only checkpoint before Web polish.
- Summary: Confirmed Phase 7 is limited to existing Web surfaces for private beta onboarding, feedback, player resume, playback/scene fallbacks, provider status clarity, and shared responsive/accessibility polish. `impeccable` was loaded before Web edits; `PRODUCT.md` is present, `DESIGN.md` is absent, and the phase follows the product/polish references plus existing Noveland UI conventions.
- Files changed: `docs/agent/harness/feature-updates/v1.1.7-user-facing-polish-plan.md`, OpenSpec tasks `8.1` and `8.2`, and harness docs.
- Tests added/updated: N/A, planning checkpoint.
- Docs updated: Phase 7 checkpoint, task board, active handoff, project index, file inventory, and change journal.
- Follow-up notes: Implement narrow Web polish only. Do not add backend behavior, migrations, API routes, new product flows, broad redesigns, or unsafe tester/player evidence.

## v1.1 Phase 7 User-facing Polish implementation entry

- Date: 2026-05-21
- Branch: feature/v1.1-7-user-facing-polish
- Scope: v1.1 Normal Use / Release Candidate Phase 7 Web polish only.
- Summary: Polished existing private beta onboarding, beta feedback, player resume, playback/scene fallback, and provider status surfaces. The implementation adds safe helper/status copy, busy labels, responsive form/action behavior, visible focus states, and provider degraded/configuration guidance without backend contract changes, new routes, redesign scope, or unsafe evidence exposure.
- Files changed: `web/app/globals.css`, `web/features/private-beta/{private-beta-onboarding,beta-feedback-panel}.tsx`, `web/features/worlds/{conversation-playback,conversation-scene-view,player-interactions}.tsx`, `web/features/admin/provider-admin.tsx`, focused Web tests, OpenSpec tasks through `8.4`, and harness docs.
- Tests added/updated: Updated focused Web unit coverage for safe onboarding status, feedback safe-evidence guidance, playback/scene media fallbacks, player resume empty/recovery states, and provider health action copy. Targeted check passed: `cd web && npm run test -- private-beta-onboarding.test.tsx beta-feedback-panel.test.tsx conversation-playback.test.tsx conversation-scene-view.test.tsx player-interactions.test.tsx provider-admin.test.tsx` (`16 passed`).
- Docs updated: Phase 7 checkpoint, task board, active handoff, project index, file inventory, and change journal.
- Follow-up notes: Full Phase 7 Web/OpenSpec gate passed: Web lint, Web typecheck, Web unit tests (`134 passed`), Web build, Web `check:next-env`, Web e2e (`21 passed`), OpenSpec strict changes/specs validation, and `git diff --check`. Commit Phase 7 and fast-forward merge to local `main`. Backend behavior was not changed.

## v1.1 Phase 7 User-facing Polish merge entry

- Date: 2026-05-21
- Branch: main
- Scope: v1.1 Normal Use / Release Candidate Phase 7 merge bookkeeping.
- Summary: Fast-forward merged `feature/v1.1-7-user-facing-polish` into local `main`, marked Phase 7 complete in OpenSpec tasks, and moved harness handoff state to Phase 8 Release Candidate Gate.
- Files changed: OpenSpec tasks, task board, active handoff, and change journal.
- Tests added/updated: N/A, merge bookkeeping only after the already-passing Phase 7 Web/OpenSpec gate.
- Docs updated: OpenSpec task `8.6`, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 8 on `feature/v1.1-8-release-candidate-gate` from clean local `main` with a docs-only RC gate evidence ownership checkpoint before implementation. No push performed.

## v1.1 Phase 5 Import/Export Stability implementation entry

- Date: 2026-05-21
- Branch: feature/v1.1-5-import-export-stability
- Scope: v1.1 Normal Use / Release Candidate Phase 5 implementation only.
- Summary: Added the Phase 5 checkpoint and extended the existing `world_packaging` boundary with safe provider, persona, memory, visual mapping, voice mapping, and source traceability manifest sections. Export preview now supports public-sample exclusion for user-provided galgame media/source content as placeholder metadata, omits provider auth refs, strips unsafe JSON keys and values, and reports repeatable import duplicate warnings. Import apply remains explicit, creates only the existing world/worldline/scene/media placeholder records, and preserves specialized manifests as safe review/apply metadata for existing owners instead of directly mutating provider, persona, memory, visual, or voice records. The phase adds no migration, Web UI, broad `worlds.py` routes, marketplace behavior, provider calls, proprietary fixtures, provider execution, or world-event writes.
- Files changed: `backend/packages/world_packaging/{pyproject.toml,src/noveland/world_packaging/{contracts,service}.py}`, `backend/tests/test_api_world_packaging.py`, `backend/uv.lock`, Phase 5 checkpoint, OpenSpec tasks through `6.4`, and harness docs.
- Tests added/updated: Added world packaging API coverage for safe extended manifest export, public-sample galgame asset/source placeholder exclusion, repeatable duplicate-package import preview warnings, explicit apply preserving extended manifests as safe metadata, no direct specialized-record mutation, and forbidden-marker leak checks. Targeted checks passed before full gate: focused world packaging ruff, focused world packaging mypy, and `cd backend && uv run pytest tests/test_api_world_packaging.py tests/test_sample_world_release_package.py -q` (`12 passed`).
- Docs updated: Phase 5 checkpoint, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Full backend/OpenSpec gate passed: backend ruff, backend mypy (`325 source files`), backend pytest (`546 passed, 8 skipped`), OpenSpec strict changes/specs validation, and `git diff --check`. Commit Phase 5, fast-forward merge to local `main`, and record merge bookkeeping before starting Phase 6. No Web UI was touched, so `impeccable` was not required for Phase 5.

## v1.1 Phase 5 Import/Export Stability merge entry

- Date: 2026-05-21
- Branch: main
- Scope: v1.1 Normal Use / Release Candidate Phase 5 merge bookkeeping.
- Summary: Fast-forward merged `feature/v1.1-5-import-export-stability` into local `main`, marked Phase 5 complete in OpenSpec tasks, and moved harness handoff state to Phase 6 Provider Reliability Layer.
- Files changed: OpenSpec tasks, task board, active handoff, and change journal.
- Tests added/updated: N/A, merge bookkeeping only after the already-passing Phase 5 backend/OpenSpec gate.
- Docs updated: OpenSpec task `6.6`, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 6 on `feature/v1.1-6-provider-reliability-layer` from clean local `main` with a docs-only provider reliability policy/profile checkpoint before implementation. No push performed.

## v1.1 Phase 6 Provider Reliability Layer planning entry

- Date: 2026-05-21
- Branch: feature/v1.1-6-provider-reliability-layer
- Scope: v1.1 Normal Use / Release Candidate Phase 6 docs-only checkpoint before implementation.
- Summary: Confirmed Phase 6 will stay inside the existing providers boundary and remain migration-free. Provider reliability will add health trend/degraded-mode reports, manual-first fallback/model-switch validation with opt-in policy in safe provider config, fallback audit metadata through `ProviderExecutionService`, and audited media-job requeue using existing media jobs. No Web UI is scoped for this phase.
- Files changed: `docs/agent/harness/feature-updates/v1.1.6-provider-reliability-layer-plan.md`, OpenSpec task `7.1`, and harness docs.
- Tests added/updated: N/A, planning checkpoint.
- Docs updated: Phase 6 checkpoint, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Implement provider reliability service/contracts/router updates and focused provider/API tests. Preserve manual-first fallback, quota-before-execution, no hidden retries, and no unsafe evidence leaks.

## v1.1 Phase 6 Provider Reliability Layer implementation entry

- Date: 2026-05-21
- Branch: feature/v1.1-6-provider-reliability-layer
- Scope: v1.1 Normal Use / Release Candidate Phase 6 implementation only.
- Summary: Added a migration-free provider reliability service under the existing providers package. The implementation adds health-trend reliability reports, degraded-mode status, manual-first fallback planning, explicit fallback execution metadata in `ProviderExecutionService`, and audited provider media-job requeue. Fallback remains disabled by default and can run only when explicitly requested and a safe opt-in policy validates primary degraded evidence, fallback provider ownership/status, capability compatibility, quota, auth availability, and audit metadata. The phase adds no Web UI, real-provider default tests, automatic hidden fallback, marketplace behavior, broad `worlds.py` routes, provider output world-state mutation, or unsafe evidence exposure.
- Files changed: `backend/packages/providers/src/noveland/providers/{__init__,contracts,reliability,service}.py`, `backend/services/api/src/noveland/services/api/providers.py`, `backend/tests/test_provider_execution_service.py`, `backend/tests/test_api_providers.py`, Phase 6 checkpoint, OpenSpec tasks through `7.4`, and harness docs.
- Tests added/updated: Added provider service/API coverage for degraded reports from health and invocation evidence, fallback disabled by default, manual fallback opt-in, capability/quota/auth/audit validation, no hidden fallback, explicit fallback invocation metadata, admin-only reliability endpoints, audited provider media-job requeue, and no secret/storage/raw prompt leak markers. Targeted checks passed: focused provider ruff, focused provider mypy, and `cd backend && uv run pytest tests/test_provider_execution_service.py tests/test_api_providers.py -q` (`28 passed`).
- Docs updated: Phase 6 checkpoint, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Full backend/OpenSpec gate passed: backend ruff, backend mypy (`326 source files`), backend pytest (`550 passed, 8 skipped`), OpenSpec strict changes/specs validation, and `git diff --check`. Commit Phase 6, fast-forward merge to local `main`, and record merge bookkeeping before starting Phase 7. No Web UI was touched, so `impeccable` was not required for Phase 6.

## v1.1 Phase 6 Provider Reliability Layer merge entry

- Date: 2026-05-21
- Branch: main
- Scope: v1.1 Normal Use / Release Candidate Phase 6 merge bookkeeping.
- Summary: Fast-forward merged `feature/v1.1-6-provider-reliability-layer` into local `main`, marked Phase 6 complete in OpenSpec tasks, and moved harness handoff state to Phase 7 User-facing Polish.
- Files changed: OpenSpec tasks, task board, active handoff, and change journal.
- Tests added/updated: N/A, merge bookkeeping only after the already-passing Phase 6 backend/OpenSpec gate.
- Docs updated: OpenSpec task `7.6`, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 7 on `feature/v1.1-7-user-facing-polish` from clean local `main`, read/use `impeccable`, and keep polish scoped to existing user/operator flows. No push performed.

## post-v1.1 RC audit F-014 membership/faction track metadata redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend security audit F-014 remediation.
- Summary: Redacted ordinary member organization membership and faction progress track metadata in member-readable list responses while preserving admin metadata visibility for world management. The fix keeps safe organization identity, agent identity, role, visibility, responsibility, progress, pressure, summary, and timing fields available to members.
- Files changed: `backend/services/api/src/noveland/services/api/worlds.py`, `backend/tests/test_api_worlds.py`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Extended `test_organization_memberships_and_faction_tracks_append_events` to prove admin membership/faction metadata retention and ordinary member list redaction. Targeted checks passed: focused pytest, focused ruff, focused mypy, OpenSpec change/spec validation, and `git diff --check`.
- Docs updated: OpenSpec architecture-contracts delta, OpenSpec tasks finding F-014, task board, active handoff, project index, file inventory, and change journal.
- Follow-up notes: Continue the backend member-readable DTO audit for worldline metadata, player choices, dashboard hidden counts, journal/notification/intervention metadata, agent relationship metadata, and calendar metadata before moving to Web/e2e security. No push performed.

## post-v1.1 RC audit F-015 worldline metadata redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend security audit F-015 remediation.
- Summary: Redacted ordinary member worldline metadata in member-readable list responses while preserving admin metadata visibility for branch management. The fix keeps safe branch identity, parent/fork references, status, actor refs, and timing fields visible to members.
- Files changed: `backend/services/api/src/noveland/services/api/worlds.py`, `backend/tests/test_api_worlds.py`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Extended `test_world_member_can_read_safe_worldline_comparison_without_mutation` to prove admin worldline metadata retention and ordinary member list redaction. Targeted checks passed: focused pytest, focused ruff, focused mypy, OpenSpec change/spec validation, and `git diff --check`.
- Docs updated: OpenSpec architecture-contracts delta, OpenSpec tasks finding F-015, task board, active handoff, project index, file inventory, and change journal.
- Follow-up notes: Continue the backend member-readable DTO audit for player choices, dashboard hidden counts, journal/notification/intervention metadata, agent relationship metadata, and calendar metadata before moving to Web/e2e security. No push performed.

## post-v1.1 RC audit F-016 player choice prompt redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend security audit F-016 remediation.
- Summary: Redacted ordinary member player choice prompt text in create/list responses while preserving admin prompt visibility for world management and review. The fix keeps safe choice identity, selected option, context, consequence preview, applied event refs, and timing fields visible to members.
- Files changed: `backend/services/api/src/noveland/services/api/worlds.py`, `backend/tests/test_api_worlds.py`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Extended `test_world_member_can_use_own_player_interaction_records_without_admin_scope` to prove member choice prompt redaction on create/list responses and admin list retention. Targeted checks passed: focused pytest, focused ruff, focused mypy, OpenSpec change/spec validation, and `git diff --check`.
- Docs updated: OpenSpec architecture-contracts delta, OpenSpec tasks finding F-016, task board, active handoff, project index, file inventory, and change journal.
- Follow-up notes: Continue the backend member-readable DTO audit for player choice preview diagnostics, dashboard hidden counts, journal/notification/intervention metadata/source fields, agent relationship metadata, and calendar metadata before moving to Web/e2e security. No push performed.

## post-v1.1 RC audit F-017 player choice preview diagnostics redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend security audit F-017 remediation.
- Summary: Redacted ordinary member player choice preview diagnostics while preserving admin diagnostics visibility for world management and review. The fix keeps safe relationship, faction, and offscreen consequence preview fields available to members.
- Files changed: `backend/services/api/src/noveland/services/api/worlds.py`, `backend/tests/test_api_worlds.py`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Extended `test_world_member_can_use_own_player_interaction_records_without_admin_scope` to prove member preview diagnostics redaction and admin preview diagnostics retention. Targeted checks passed: focused pytest, focused ruff, focused mypy, OpenSpec change/spec validation, and `git diff --check`.
- Docs updated: OpenSpec architecture-contracts delta, OpenSpec tasks finding F-017, task board, active handoff, project index, file inventory, and change journal.
- Follow-up notes: Continue the backend member-readable DTO audit for dashboard hidden counts, journal/notification/intervention metadata/source fields, agent relationship metadata, and calendar metadata before moving to Web/e2e security. No push performed.

## post-v1.1 RC audit F-018 living world dashboard hidden count redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend security audit F-018 remediation.
- Summary: Redacted ordinary member living-world dashboard hidden secret counts while preserving admin visibility for world management and review. The fix keeps safe aggregate dashboard counters available to members.
- Files changed: `backend/services/api/src/noveland/services/api/worlds.py`, `backend/tests/test_api_worlds.py`, `openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md`, `openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md`, and harness docs.
- Tests added/updated: Extended `test_knowledge_player_guardrail_apis_and_acceptance_gap_fixes` to prove admin dashboard hidden secret count retention and ordinary member dashboard redaction to zero. Targeted checks passed: focused pytest, focused ruff, focused mypy, OpenSpec change/spec validation, and `git diff --check`.
- Docs updated: OpenSpec architecture-contracts delta, OpenSpec tasks finding F-018, task board, active handoff, project index, file inventory, and change journal.
- Follow-up notes: Continue the backend member-readable DTO audit for journal/notification/intervention metadata/source fields, agent relationship metadata, and calendar metadata before moving to Web/e2e security. No push performed.

## Entry format

- Date:
- Branch:
- Scope:
- Summary:
- Files changed:
- Tests added/updated:
- Docs updated:
- Follow-up notes:

## v1.1 Phase 4 Content Safety & Moderation Hardening implementation entry

- Date: 2026-05-21
- Branch: feature/v1.1-4-content-safety-moderation-hardening
- Scope: v1.1 Normal Use / Release Candidate Phase 4 implementation only.
- Summary: Added the Phase 4 checkpoint and hardened the existing moderation boundary with admin-only safety-review reports for player-visible output findings plus explicit beta-feedback-to-moderation escalation. Escalation links the feedback report to a moderation report, moves the feedback into investigation, preserves reporter privacy for other testers, keeps moderation evidence admin-only, and sanitizes evidence/metadata. Existing applied moderation action suppression remains the reader/player visibility control. The phase adds no migrations, Web UI, broad `worlds.py` routes, duplicate moderation framework, public forum behavior, automatic punitive action, provider calls, or world-event writes.
- Files changed: `backend/packages/moderation/{pyproject.toml,src/noveland/moderation/{__init__,contracts,service}.py}`, `backend/services/api/src/noveland/services/api/moderation.py`, `backend/tests/test_api_moderation.py`, `backend/uv.lock`, Phase 4 checkpoint, OpenSpec tasks through `5.4`, and harness docs.
- Tests added/updated: Added moderation API coverage for admin-only safety review creation, safe evidence refs, sanitized metadata, feedback escalation privacy, feedback-to-moderation linking, unchanged reporter-private beta feedback visibility, admin-only moderation evidence, no world-event writes, and forbidden-marker leak checks. Targeted checks passed: focused moderation ruff, focused moderation mypy, and `cd backend && uv run pytest tests/test_api_moderation.py -q` (`7 passed`).
- Docs updated: Phase 4 checkpoint, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Run the full backend/OpenSpec gate, then commit Phase 4, fast-forward merge to local `main`, and record merge bookkeeping before starting Phase 5. No Web UI was touched, so `impeccable` was not required for Phase 4.

## v1.1 Phase 4 Content Safety & Moderation Hardening merge entry

- Date: 2026-05-21
- Branch: main
- Scope: v1.1 Normal Use / Release Candidate Phase 4 merge bookkeeping.
- Summary: Fast-forward merged `feature/v1.1-4-content-safety-moderation-hardening` into local `main`, marked Phase 4 complete in OpenSpec tasks, and moved harness handoff state to Phase 5 Import/Export Stability.
- Files changed: OpenSpec tasks, task board, active handoff, and change journal.
- Tests added/updated: N/A, merge bookkeeping only after the already-passing Phase 4 backend/OpenSpec gate.
- Docs updated: OpenSpec task `5.6`, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 5 on `feature/v1.1-5-import-export-stability` from clean local `main` with a docs-only import/export manifest and asset policy checkpoint before implementation. No push performed.

## v1.1 Phase 3 Multi-world / Multi-user Stress Test implementation entry

- Date: 2026-05-21
- Branch: feature/v1.1-3-multi-world-multi-user-stress
- Scope: v1.1 Normal Use / Release Candidate Phase 3 implementation only.
- Summary: Added the Phase 3 checkpoint and a backend-only `NormalUseStressService` under the existing observability boundary. The report validates the accepted normal-use baseline of 3 worlds, 2 worldlines per world, 2 player sessions per world, at least 2 fake provider profiles, deterministic 120-turn equivalent coverage, player/worldline isolation, quota evidence, runtime-path coverage, and safe aggregate reporting. Real-provider stress remains disabled by default and is reported as opt-in only. The phase adds no migrations, Web UI, API routes, broad `worlds.py` routes, real provider calls, or duplicate readiness framework.
- Files changed: `backend/packages/observability/src/noveland/observability/{contracts,services,__init__}.py`, `backend/tests/test_normal_use_stress.py`, Phase 3 checkpoint, OpenSpec tasks through `4.4`, and harness docs.
- Tests added/updated: Added focused stress tests for deterministic fake-provider baseline pass, cross-worldline player-session leak detection, missing quota policy blocker, insufficient turn-equivalent blocker, and safe report evidence. Targeted checks passed: focused ruff, focused mypy, and `cd backend && uv run pytest tests/test_normal_use_stress.py -q` (`4 passed`). Full backend/OpenSpec gate passed: backend ruff, backend mypy (`325 source files`), backend pytest (`541 passed, 8 skipped`), OpenSpec strict changes/specs validation, and `git diff --check`.
- Docs updated: Phase 3 checkpoint, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Commit Phase 3, fast-forward merge to local `main`, and record merge bookkeeping before starting Phase 4. No Web UI was touched, so `impeccable` was not required for Phase 3.

## v1.1 Phase 3 Multi-world / Multi-user Stress Test merge entry

- Date: 2026-05-21
- Branch: main
- Scope: v1.1 Normal Use / Release Candidate Phase 3 merge bookkeeping.
- Summary: Fast-forward merged `feature/v1.1-3-multi-world-multi-user-stress` into local `main`, marked Phase 3 complete in OpenSpec tasks, and moved harness handoff state to Phase 4 Content Safety & Moderation Hardening.
- Files changed: OpenSpec tasks, task board, active handoff, and change journal.
- Tests added/updated: N/A, merge bookkeeping only after the already-passing Phase 3 backend/OpenSpec gate.
- Docs updated: OpenSpec task `4.6`, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 4 on `feature/v1.1-4-content-safety-moderation-hardening` from clean local `main` with a docs-only moderation/feedback/privacy checkpoint before implementation. No push performed.

## v1.1 Phase 1 Operational Runbooks implementation entry

- Date: 2026-05-21
- Branch: feature/v1.1-1-operational-runbooks
- Scope: v1.1 Normal Use / Release Candidate Phase 1 docs-only operational runbooks; no backend runtime behavior, Web UI, migrations, API routes, provider calls, or push.
- Summary: Added the Phase 1 planning checkpoint and normal-use operator runbooks for provider outage, quota exhaustion, stuck media jobs, migration failure, backup/restore, rollback, worldline restore, secret rotation, private beta invite/session/feedback incidents, import/export recovery, and provider fallback/degraded mode. Each runbook references existing controls where possible and keeps evidence collection redacted.
- Files changed: `docs/agent/harness/feature-updates/v1.1.1-operational-runbooks-plan.md`, `docs/agent/operations/runbooks/**`, `backend/tests/test_operational_runbooks_docs.py`, OpenSpec tasks through `2.3`, and harness docs.
- Tests added/updated: Added a docs consistency test to verify required runbook files, operator sections, redaction language, existing control references, and recovery boundaries. Targeted docs test passed (`4 passed`). Applicable backend/OpenSpec gate passed: backend ruff, backend mypy (`322 source files`), backend pytest (`533 passed, 8 skipped`), OpenSpec strict changes/specs validation, and `git diff --check`.
- Docs updated: Phase 1 checkpoint, operational runbooks, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Commit Phase 1 and fast-forward merge to local `main`, then record merge bookkeeping before starting Phase 2. No Web UI was touched, so `impeccable` was not required for Phase 1.

## v1.1 Phase 1 Operational Runbooks merge entry

- Date: 2026-05-21
- Branch: main
- Scope: v1.1 Normal Use / Release Candidate Phase 1 merge bookkeeping.
- Summary: Fast-forward merged `feature/v1.1-1-operational-runbooks` into local `main`, marked Phase 1 complete in OpenSpec tasks, and moved harness handoff state to Phase 2 Real Backup/Restore Drill.
- Files changed: OpenSpec tasks, task board, active handoff, and change journal.
- Tests added/updated: N/A, merge bookkeeping only after the already-passing Phase 1 docs/backend/OpenSpec gate.
- Docs updated: OpenSpec task `2.5`, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 2 on `feature/v1.1-2-backup-restore-drill` from clean local `main` with a docs-only fresh local restore drill checkpoint before implementation. No push performed.

## v1.1 Phase 2 Real Backup/Restore Drill implementation entry

- Date: 2026-05-21
- Branch: feature/v1.1-2-backup-restore-drill
- Scope: v1.1 Normal Use / Release Candidate Phase 2 implementation only.
- Summary: Added the Phase 2 checkpoint and a read-only fresh local/single-host restore drill verifier. The verifier reuses storage integrity audit evidence to check restored database state, media objects, checksums, snapshot payloads, provider config metadata without secrets, OpenSpec provenance, and safe report redaction. Added platform-admin `/observability/readiness/backup-restore-drill` under the existing observability/readiness boundary. The phase adds no migrations, provider calls, Web UI, broad `worlds.py` routes, persisted drill tables, or public restore reports.
- Files changed: `backend/packages/storage/src/noveland/storage/restore_drill.py`, storage/observability exports and contracts, `backend/services/api/src/noveland/services/api/observability.py`, `backend/tests/test_backup_restore_drill.py`, Phase 2 checkpoint, OpenSpec tasks through `3.4`, and harness docs.
- Tests added/updated: Added backup/restore drill tests for complete restored fixture pass, missing media/checksum safe blocker, provider config secret-marker blocker, admin-only endpoint access, and no forbidden response markers. Targeted Phase 2 checks passed: focused ruff, focused mypy, and `cd backend && uv run pytest tests/test_backup_restore_drill.py -q` (`4 passed`). Full backend/OpenSpec gate passed: backend ruff, backend mypy (`324 source files`), backend pytest (`537 passed, 8 skipped`), OpenSpec strict changes/specs validation, and `git diff --check`.
- Docs updated: Phase 2 checkpoint, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Commit Phase 2, fast-forward merge to local `main`, and record merge bookkeeping before starting Phase 3. No Web UI was touched, so `impeccable` was not required for Phase 2.

## v1.1 Phase 2 Real Backup/Restore Drill merge entry

- Date: 2026-05-21
- Branch: main
- Scope: v1.1 Normal Use / Release Candidate Phase 2 merge bookkeeping.
- Summary: Fast-forward merged `feature/v1.1-2-backup-restore-drill` into local `main`, marked Phase 2 complete in OpenSpec tasks, and moved harness handoff state to Phase 3 Multi-world / Multi-user Stress Test.
- Files changed: OpenSpec tasks, task board, active handoff, and change journal.
- Tests added/updated: N/A, merge bookkeeping only after the already-passing Phase 2 backend/OpenSpec gate.
- Docs updated: OpenSpec task `3.6`, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 3 on `feature/v1.1-3-multi-world-multi-user-stress` from clean local `main` with a docs-only stress baseline checkpoint before implementation. No push performed.

## v1.1 Normal Use / Release Candidate feasibility review entry

- Date: 2026-05-21
- Branch: main
- Scope: v1.1 Normal Use / Release Candidate feasibility review and OpenSpec plan adaptation only; no backend/Web implementation, migrations, runtime behavior changes, API behavior changes, or push.
- Summary: Reviewed the active v1.1 OpenSpec and current v1.0-complete repository against normal-use/release-candidate readiness. The review concludes v1.1 can start after minor OpenSpec adjustments. The existing phase order remains valid, with explicit checkpoints for fresh local restore target, deterministic stress baseline, moderation/feedback/privacy integration, import/export asset policy, manual-first provider reliability, `impeccable`-shaped UI polish, and RC gate evidence ownership.
- Files changed: `/docs/agent/harness/feature-updates/v1.1-normal-use-release-candidate-feasibility-review.md`, `/openspec/changes/v1-1-normal-use-release-candidate/{proposal.md,design.md,phase-plan.md,tasks.md,specs/**/spec.md}`, and harness docs.
- Tests added/updated: N/A, documentation-only feasibility review.
- Docs updated: v1.1 feasibility review, OpenSpec proposal/design/phase-plan/tasks/spec deltas, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Phase 1 Operational Runbooks may start after review acceptance. Do not implement v1.1 backend/Web work until the relevant phase checkpoint is written and accepted. Use `impeccable` before any Web implementation. No push performed.

## v1.0 Private Beta MVP archive entry

- Date: 2026-05-21
- Branch: main
- Scope: OpenSpec archive, v1.0 current specs, release notes, and harness bookkeeping.
- Summary: Archived the completed v1.0 Private Beta MVP OpenSpec change, synced implemented v1.0 capabilities into current OpenSpec specs, and added v1.0 release notes.
- Files changed: `/openspec/specs/**`, `/openspec/changes/archive/2026-05-21-v1-0-private-beta-mvp/**`, `/docs/agent/harness/release-notes/v1.0-private-beta-mvp.md`, and harness docs.
- Tests added/updated: N/A.
- Docs updated: OpenSpec current specs, OpenSpec archive, v1.0 release notes, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: v1.0 is closed locally. v1.1 Normal Use / Release Candidate feasibility review may start when explicitly requested. No backend/Web runtime behavior changed and no push was performed.

## v1.0 Phase 6 Beta Feedback System merge entry

- Date: 2026-05-20
- Branch: main
- Scope: v1.0 Private Beta MVP Phase 6 merge bookkeeping.
- Summary: Fast-forward merged `feature/v1.0-6-beta-feedback` into local `main`, marked Phase 6 complete in OpenSpec tasks, and moved harness handoff state to Phase 7 Beta Content Iteration Loop.
- Files changed: OpenSpec tasks, task board, active handoff, and change journal.
- Tests added/updated: N/A, merge bookkeeping only after the already-passing Phase 6 full gate.
- Docs updated: OpenSpec task `7.7`, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 7 on `feature/v1.0-7-beta-content-iteration` from clean local `main` with a docs-only repair proposal ownership checkpoint before implementation. No push performed.

## v1.0 Phase 6 Beta Feedback System implementation entry

- Date: 2026-05-20
- Branch: feature/v1.0-6-beta-feedback
- Scope: v1.0 Private Beta MVP Phase 6 implementation only.
- Summary: Added the Phase 6 planning checkpoint and a dedicated beta feedback boundary with `backend/packages/beta_feedback/`, app-level `beta_feedback.py`, migration `20260520_0048_beta_feedback_reports.py`, member feedback submission, reporter-private list/read behavior, admin triage, safe evidence refs, and repair-proposal link refs for Phase 7. Added a minimal `/worlds/{worldId}/feedback` Web surface after using `impeccable`, with tester submission and admin triage forms. The phase adds no public forum/social features, moderation punishment, provider calls, automatic repair mutation, broad `worlds.py` routes, world-event writes, or raw prompt/output/storage/path/secret/invite-token exposure.
- Files changed: `backend/packages/beta_feedback/**`, `backend/services/api/src/noveland/services/api/beta_feedback.py`, migration `20260520_0048_beta_feedback_reports.py`, API app/package metadata, schema/import/alembic tests, `web/app/worlds/[worldId]/feedback/page.tsx`, `web/features/private-beta/beta-feedback-panel.tsx`, `web/lib/beta-feedback/**`, workspace nav/CSS, Phase 6 OpenSpec docs/tasks, the Phase 6 checkpoint, and harness docs.
- Tests added/updated: Backend API/schema/import/alembic coverage for feedback create/list/read, admin triage, reporter privacy, cross-world and cross-worldline evidence rejection, hidden/developer-only evidence suppression, repair-proposal safe refs, no world-event writes, and forbidden-marker leak checks. Web unit coverage verifies feedback submission, filtering, triage, and no rendered internal metadata leakage. Targeted checks passed: focused ruff, focused mypy, focused backend pytest (`35 passed`), focused Web unit test (`2 passed`), and Web typecheck. Full Phase 6 gate passed: backend ruff, backend mypy (`321 source files`), backend pytest (`520 passed, 8 skipped`), Web lint, Web typecheck, Web unit tests (`133 passed`), Web build, Web `check:next-env`, Web e2e (`21 passed`), OpenSpec strict changes/specs validation, and `git diff --check`.
- Docs updated: Phase 6 checkpoint, OpenSpec design/phase-plan/spec/tasks through `7.6`, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Commit Phase 6, fast-forward merge to local `main`, and record merge bookkeeping before starting Phase 7. No push performed.

## v1.0 Phase 5 Memory & Persona QA merge entry

- Date: 2026-05-20
- Branch: main
- Scope: v1.0 Private Beta MVP Phase 5 merge bookkeeping.
- Summary: Fast-forward merged `feature/v1.0-5-memory-persona-qa` into local `main`, marked Phase 5 complete in OpenSpec tasks, and moved harness handoff state to Phase 6 Beta Feedback System.
- Files changed: OpenSpec tasks, task board, active handoff, and change journal.
- Tests added/updated: N/A, merge bookkeeping only after the already-passing Phase 5 gate.
- Docs updated: OpenSpec task `6.6`, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 6 on `feature/v1.0-6-beta-feedback` from clean local `main` with a docs-only feedback ownership checkpoint before implementation. No push performed.

## v1.0 Phase 5 Memory & Persona QA implementation entry

- Date: 2026-05-20
- Branch: feature/v1.0-5-memory-persona-qa
- Scope: v1.0 Private Beta MVP Phase 5 implementation only.
- Summary: Added the Phase 5 planning checkpoint and extended the existing narrative quality boundary with response-only memory/persona QA DTOs, deterministic `NarrativeQualityService.run_memory_persona_qa()`, and world-admin `POST /worlds/{world_id}/narrative-quality/memory-persona/qa`. The report detects missing persona/memory, memory contamination, persona drift, dialogue style drift, relationship drift, traceability gaps, and worldline contamination using safe evidence refs and proposal-only repair suggestion types. Phase 5 adds no migration, Web UI, provider execution, direct persona/memory mutation, duplicate eval framework, broad `worlds.py` routes, or world-event writes.
- Files changed: `backend/packages/narrative_quality/src/noveland/narrative_quality/{contracts.py,service.py}`, `backend/services/api/src/noveland/services/api/narrative_quality.py`, `backend/tests/test_narrative_quality_service.py`, `backend/tests/test_api_narrative_quality.py`, Phase 5 OpenSpec docs/tasks, the Phase 5 checkpoint, and harness docs.
- Tests added/updated: Narrative quality service/API tests now cover traceable QA success, memory contamination, persona/style/relationship drift, cross-worldline conversation rejection, admin-only API ACL, proposal-only repair suggestions, no direct memory/persona/world-event mutation, and no forbidden response leaks. Targeted checks passed: focused ruff, focused mypy, and `cd backend && uv run pytest tests/test_narrative_quality_service.py tests/test_api_narrative_quality.py -q` (`75 passed`). Full backend/OpenSpec gate passed: backend ruff, backend mypy (`315 source files`), backend pytest (`515 passed, 8 skipped`), OpenSpec strict changes/specs validation, and `git diff --check`.
- Docs updated: Phase 5 checkpoint, OpenSpec design/phase-plan/tasks through `6.5`, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Commit Phase 5 and fast-forward merge to local `main` if the branch stays clean. No Web UI was added in Phase 5, so no new `impeccable` UI work was required.

## v1.0 Phase 4 World Setup Wizard merge entry

- Date: 2026-05-20
- Branch: main
- Scope: v1.0 Private Beta MVP Phase 4 merge bookkeeping.
- Summary: Fast-forward merged `feature/v1.0-4-world-setup-wizard` into local `main`, marked Phase 4 complete in OpenSpec tasks, and moved harness handoff state to Phase 5 Memory & Persona QA.
- Files changed: OpenSpec tasks, task board, active handoff, and change journal.
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec task `5.6`, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 5 on `feature/v1.0-5-memory-persona-qa` from clean local `main` with a docs-only QA diagnostics ownership checkpoint before implementation. No push performed.

## v1.0 Phase 4 World Setup Wizard implementation entry

- Date: 2026-05-20
- Branch: feature/v1.0-4-world-setup-wizard
- Scope: v1.0 Private Beta MVP Phase 4 implementation only.
- Summary: Added the Phase 4 planning checkpoint and extended the existing observability/readiness boundary with `PrivateBetaSetupReadinessReport`, `ProductionReadinessGateService.private_beta_setup_report()`, and platform-admin `GET /observability/readiness/private-beta-setup`. The report reuses existing readiness sections and safe evidence refs to validate private beta invite/access, least-privilege membership/profile bootstrap, player session restore, player/capability quota controls, provider/model lab readiness, persona/memory, visual, voice, media, source traceability, self-use MVP evidence, and recent world-event leak markers. Phase 4 adds no migration, setup framework tables, Web UI, provider execution, broad `worlds.py` routes, or tester-visible admin diagnostics.
- Files changed: `backend/packages/observability/{pyproject.toml,src/noveland/observability/{__init__.py,contracts.py,services.py}}`, `backend/services/api/src/noveland/services/api/observability.py`, `backend/tests/test_production_readiness_gate.py`, `backend/uv.lock`, Phase 4 OpenSpec docs/tasks, the Phase 4 checkpoint, and harness docs.
- Tests added/updated: Production readiness tests now cover complete private beta setup pass, missing access/session/quota/provider/persona/memory/visual/voice blockers, self-use evidence redaction, platform-admin-only endpoint ACL, no forbidden response leaks, and no duplicate setup/readiness framework tables. Targeted checks passed: focused readiness pytest (`17 passed`), focused ruff, and focused mypy. Full backend/OpenSpec gate passed: backend ruff, backend mypy (`315 source files`), backend pytest (`510 passed, 8 skipped`), OpenSpec strict changes/specs validation, and `git diff --check`.
- Docs updated: Phase 4 checkpoint, OpenSpec design/spec/tasks through `5.5`, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Commit Phase 4, fast-forward merge to local `main`, then record merge bookkeeping before starting Phase 5 Memory & Persona QA. No Web UI was added in Phase 4, so `impeccable` was not required.

## v1.0 Phase 3 Cost & Quota Real Enforcement merge entry

- Date: 2026-05-20
- Branch: main
- Scope: v1.0 Private Beta MVP Phase 3 merge bookkeeping.
- Summary: Fast-forward merged `feature/v1.0-3-cost-quota-enforcement` into local `main`, marked Phase 3 complete in OpenSpec tasks, and moved harness handoff state to Phase 4 World Setup Wizard.
- Files changed: OpenSpec tasks, task board, active handoff, and change journal.
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec task `4.7`, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 4 on `feature/v1.0-4-world-setup-wizard` from clean local `main` with a docs-only readiness aggregation checkpoint before implementation. No push performed.

## v1.0 Phase 3 Cost & Quota Real Enforcement implementation entry

- Date: 2026-05-20
- Branch: feature/v1.0-3-cost-quota-enforcement
- Scope: v1.0 Private Beta MVP Phase 3 implementation only.
- Summary: Extended provider-owned quota enforcement so `ProviderExecutionService` evaluates world, provider, capability, and optional player actor scope before secret resolution or adapter execution. The existing `provider_budget_policies.limits_json` now supports safe `capabilities`, `players`, and `default_player` nested limits without a new migration. Provider quota status accepts safe admin filters for provider, player actor, and capability. Image and speech service requests now carry optional `player_actor_id` and explicit capability keys; admin smoke/test paths are also quota-guarded.
- Files changed: provider budget/contracts/routing/service, provider API quota/status and smoke/test inputs, image and speech request/service contracts, provider execution/API tests, Phase 3 checkpoint, and OpenSpec/harness docs.
- Tests added/updated: Provider execution and provider API tests now cover world/provider limits, emergency stop before secret resolution, capability-scoped blocking, per-player/default-player isolation, scoped quota status, safe quota evidence, smoke-test quota guarding, and no secret/path/raw prompt leak. Targeted checks passed: provider ruff, provider mypy, focused pytest (`24 passed`), and broader targeted provider/image/speech pytest (`36 passed`). Full Phase 3 backend gate passed: backend ruff, backend mypy (`315 source files`), backend pytest (`506 passed, 8 skipped`), OpenSpec strict changes/specs validation, and `git diff --check`.
- Docs updated: OpenSpec Phase 3 tasks through `4.6`, Phase 3 design/spec/task deltas, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Commit Phase 3 and fast-forward merge to local `main`, then record merge bookkeeping before starting Phase 4. No Web UI was added in Phase 3, so no new `impeccable` UI work was required beyond the already loaded frontend policy.

## v1.0 Phase 3 Cost & Quota Real Enforcement planning entry

- Date: 2026-05-20
- Branch: feature/v1.0-3-cost-quota-enforcement
- Scope: v1.0 Private Beta MVP Phase 3 docs-only planning checkpoint before implementation.
- Summary: Confirmed that quota enforcement should stay inside the existing provider boundary so `ProviderExecutionService` remains the single pre-spend guard. Phase 3 will extend `provider_budget_policies.limits_json` with optional player and capability scopes, carry optional `player_actor_id` and `capability_key` on provider execution requests, and avoid a new migration unless the JSON policy proves insufficient.
- Files changed: `docs/agent/harness/feature-updates/v1.0.3-cost-quota-real-enforcement-plan.md`, OpenSpec design/spec/tasks, and harness docs.
- Tests added/updated: N/A, planning checkpoint.
- Docs updated: Phase 3 checkpoint, OpenSpec design/spec/tasks, project index, file inventory, task board, and change journal.
- Follow-up notes: Implement Phase 3 on this branch with no broad `worlds.py` routes, no tester provider/admin exposure, no real provider calls by default, no hidden retries after quota blocks, and no raw prompt/output/storage/secret leaks.

## v1.0 Phase 2 Player Session Stability merge entry

- Date: 2026-05-20
- Branch: main
- Scope: v1.0 Private Beta MVP Phase 2 merge bookkeeping.
- Summary: Fast-forward merged `feature/v1.0-2-player-session-stability` into local `main`, marked Phase 2 complete in OpenSpec tasks, and moved harness handoff state to Phase 3 Cost & Quota Real Enforcement.
- Files changed: OpenSpec tasks, task board, active handoff, and change journal.
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec task `3.6`, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 3 on `feature/v1.0-3-cost-quota-enforcement` from clean local `main` with a docs-only quota ownership/checkpoint before implementation. No push performed.

## v1.0 Phase 2 Player Session Stability implementation entry

- Date: 2026-05-20
- Branch: feature/v1.0-2-player-session-stability
- Scope: v1.0 Private Beta MVP Phase 2 implementation only.
- Summary: Added a dedicated player session stability boundary with `backend/packages/player_sessions/`, app-level `player_sessions.py`, migration `20260517_0047_player_sessions.py`, player-owned resume records scoped by world, worldline, current user, and player actor, safe recovery status calculation for stale conversation, missing media, provider, media, and presentation failures, and player-safe resume/restore UI on the existing player surface. The implementation adds no broad `worlds.py` routes, no admin diagnostics in tester DTOs, no raw event payload access, no provider calls, and no storage path, base64, bytes, raw prompt/output, prompt snapshot, secret, or invite-token exposure.
- Files changed: `backend/packages/player_sessions/**`, `backend/services/api/src/noveland/services/api/player_sessions.py`, migration `20260517_0047_player_sessions.py`, API app/package metadata, schema/import/alembic tests, `web/features/worlds/player-interactions.tsx`, `web/lib/worlds/{client,server,types}.ts`, and Phase 2 OpenSpec/harness docs.
- Tests added/updated: Backend API/schema/import/alembic coverage for resume round trip, cross-player isolation, cross-world/worldline rejection, stale conversation and provider/media/presentation fallback, no forbidden marker leaks, and workspace import/schema metadata. Web unit coverage verifies resume panel rendering and fallback copy. Full Phase 2 gate passed: backend ruff, backend mypy, backend pytest (`503 passed, 8 skipped`), Web lint, Web typecheck, Web unit tests (`131 passed`), Web build, Web `check:next-env`, Web e2e (`21 passed`), OpenSpec strict changes/specs validation, and `git diff --check`.
- Docs updated: OpenSpec Phase 2 task `3.5`, Phase 2 design/spec/task deltas, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Commit Phase 2, fast-forward merge to local `main`, then record merge bookkeeping before starting Phase 3 Cost & Quota Real Enforcement. No push performed.

## v1.0 Phase 2 Player Session Stability planning entry

- Date: 2026-05-20
- Branch: feature/v1.0-2-player-session-stability
- Scope: v1.0 Private Beta MVP Phase 2 docs-only planning checkpoint before implementation.
- Summary: Confirmed that player resume state should use a dedicated `player_sessions` package and app-level router rather than private beta invite records or overloaded conversation history. The first migration will add `player_sessions` scoped by world, worldline, user, and player actor, with optional conversation, scene, last turn, last presentation, safe route/resume JSON, recovery status, status, and last-seen timestamps.
- Files changed: `docs/agent/harness/feature-updates/v1.0.2-player-session-stability-plan.md`, OpenSpec design/spec/tasks, and harness docs.
- Tests added/updated: N/A, planning checkpoint.
- Docs updated: Phase 2 checkpoint, OpenSpec design/spec/tasks, project index, file inventory, task board, and change journal.
- Follow-up notes: Implement Phase 2 on this branch with no broad `worlds.py` routes, no browser-only resume state, no admin diagnostics in tester/player DTOs, and no raw event/prompt/output/storage/secret leaks.

## v1.0 Phase 1 Private Beta Onboarding & Access Model merge entry

- Date: 2026-05-17
- Branch: main
- Scope: v1.0 Private Beta MVP Phase 1 merge bookkeeping.
- Summary: Fast-forward merged `feature/v1.0-1-private-beta-access` into local `main`, marked Phase 1 complete in OpenSpec tasks, and moved harness handoff state to a pause before Phase 2 Player Session Stability.
- Files changed: OpenSpec tasks, task board, active handoff, and change journal.
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec task `2.7`, task board, active handoff, and change journal.
- Follow-up notes: Pause before Phase 2. The next accepted v1.0 step is the Player Session Stability docs-only planning checkpoint; no push performed.

## v1.0 Phase 1 Private Beta Onboarding & Access Model implementation entry

- Date: 2026-05-17
- Branch: feature/v1.0-1-private-beta-access
- Scope: v1.0 Private Beta MVP Phase 1 implementation only.
- Summary: Added the dedicated private beta access boundary with hashed invite tokens, invite lifecycle/audit, least-privilege `human_user` membership bootstrap after redemption, worldline-scoped player profile setup, and a minimal authenticated Web onboarding surface for invite redemption and player identity creation. The router is app-level only and no broad `worlds.py` routes, public signup, provider/admin/media/invocation privileges, resolved secrets, raw tokens, storage paths, raw prompts/outputs, or world-event writes were added.
- Files changed: `backend/packages/private_beta/**`, `backend/services/api/src/noveland/services/api/private_beta.py`, migration `20260517_0046_private_beta_invites.py`, API app/package metadata, schema/import tests, `web/app/private-beta/page.tsx`, `web/app/api/private-beta/[...privateBetaPath]/route.ts`, `web/features/private-beta/**`, `web/lib/private-beta/**`, and private beta CSS.
- Tests added/updated: Backend API/schema/import/alembic coverage for invite create/list/detail/revoke, token hash-only storage, valid/idempotent redemption, expired/revoked/waitlisted rejection, cross-worldline validation, least-privilege membership/profile bootstrap, admin-route rejection, no forbidden marker leaks, and no `world_events` writes. Web unit coverage verifies invite redemption, player identity creation, guidance rendering, and no invite-token leak in rendered content. Full Phase 1 gate passed: backend ruff, backend mypy, backend pytest (`499 passed, 8 skipped`), Web lint, Web typecheck, Web unit tests (`130 passed`), Web build, Web `check:next-env`, Web e2e (`21 passed`), OpenSpec strict changes/specs validation, and `git diff --check`.
- Docs updated: OpenSpec Phase 1 tasks and harness docs.
- Follow-up notes: Commit Phase 1 and fast-forward merge to local `main`, then record merge bookkeeping before starting Phase 2. No push performed.

## v1.0 Phase 1 Private Beta Onboarding & Access Model planning entry

- Date: 2026-05-17
- Branch: main
- Scope: v1.0 Private Beta MVP Phase 1 docs-only planning checkpoint; no backend/Web implementation, migrations, runtime behavior changes, API behavior changes, or push.
- Summary: Confirmed that private beta onboarding must use a dedicated invite/access model rather than membership-only access. The checkpoint assigns ownership to planned `backend/packages/private_beta/` and app-level `private_beta.py`, keeps `WorldMembership` as the least-privilege enforcement layer after valid redemption, defines invite lifecycle states, plans the `private_beta_invites` first migration, requires hashed non-guessable invite tokens, and limits Phase 1 Web scope to API-first plus minimal redemption/onboarding flow after `impeccable`.
- Files changed: `/docs/agent/harness/feature-updates/v1.0.1-private-beta-onboarding-access-model-plan.md`, `/openspec/changes/v1-0-private-beta-mvp/{design.md,phase-plan.md,tasks.md,specs/private-beta-onboarding/spec.md}`, and harness docs.
- Tests added/updated: N/A, documentation-only planning checkpoint.
- Docs updated: Phase 1 checkpoint, OpenSpec design/phase-plan/tasks/spec delta, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 1 implementation only after checkpoint acceptance. Do not add broad routes to `worlds.py`; do not store/log raw invite tokens; do not grant admin/provider/media/invocation privileges to testers. Use `impeccable` before any Web implementation. No push performed.

## v1.0 Private Beta MVP feasibility review entry

- Date: 2026-05-17
- Branch: main
- Scope: v1.0 Private Beta MVP feasibility review and OpenSpec plan revision only; no backend/Web implementation, migrations, runtime behavior changes, API behavior changes, or push.
- Summary: Reviewed the active v1.0 OpenSpec and current v0.9-complete repository against the private beta requirement for 1-3 invited testers. The review concludes v0.9 provides the content/provider foundation but v1.0 cannot start as-is: access, player session restore, per-player/capability quota, feedback ownership, and readiness ownership decisions must be front-loaded. Revised the v1.0 phase order to Private Beta Onboarding & Access Model, Player Session Stability, Cost & Quota Real Enforcement, World Setup Wizard, Memory & Persona QA, Beta Feedback System, Beta Content Iteration Loop, and Private Beta Gate.
- Files changed: `/docs/agent/harness/feature-updates/v1.0-private-beta-mvp-feasibility-review.md`, `/openspec/changes/v1-0-private-beta-mvp/{proposal.md,design.md,phase-plan.md,tasks.md,specs/**/spec.md}`, and harness docs.
- Tests added/updated: N/A, documentation-only feasibility review.
- Docs updated: v1.0 feasibility review, OpenSpec proposal/design/phase-plan/tasks/spec deltas, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Do not implement v1.0 until the feasibility review is accepted. The next implementation entry is Phase 1 Private Beta Onboarding & Access Model, starting with a docs-only checkpoint for invite/access ownership. Use `impeccable` before any Web implementation. No push performed.

## v0.9 Self-use MVP Demo World Cut archive entry

- Date: 2026-05-17
- Branch: main
- Scope: OpenSpec archive, v0.9 current specs, release notes, and harness bookkeeping.
- Summary: Archived the completed v0.9 Self-use MVP Demo World Cut OpenSpec change, synced implemented v0.9 capabilities into current OpenSpec specs, and added v0.9 release notes.
- Files changed: `/openspec/specs/**`, `/openspec/changes/archive/2026-05-17-v0-9-self-use-mvp-demo-world-cut/**`, `/docs/agent/harness/release-notes/v0.9-self-use-mvp-demo-world-cut.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A
- Docs updated: OpenSpec current specs, OpenSpec archive, v0.9 release notes, project index, file inventory, task board, active handoff.
- Follow-up notes: v0.9 is closed locally. v1.0 Private Beta MVP feasibility review may start when explicitly requested. No backend/Web runtime behavior changed and no push was performed.

## v0.9 Phase 10 Self-use MVP Gate planning/implementation entry

- Date: 2026-05-17
- Branch: feat/v0.9-self-use-mvp-gate
- Scope: v0.9 Self-use MVP Demo World Cut Phase 10 only.
- Summary: Added a backend/API-only self-use MVP gate under the existing observability readiness boundary. The platform-admin report aggregates safe evidence for demo entry, conversation continuity, persona/memory, visual playback and visual generation readiness, voice playback, provider/model lab setup, media jobs, invocation ledger, source traceability, recent world-event leak markers, and manual 30-minute play/resume/failure-note checklist items. It is read-only, does not persist a duplicate readiness framework, does not run providers, and does not imply private beta or public launch readiness.
- Files changed: `backend/packages/observability/**`, `backend/services/api/src/noveland/services/api/observability.py`, `backend/tests/test_production_readiness_gate.py`, OpenSpec tasks, and harness docs.
- Tests added/updated: Production readiness gate tests now cover self-use MVP pass/block reports, manual checklist blocking, provider/media/memory/visual/voice/invocation/source-traceability diagnostics, platform-admin API ACL, safe no-leak response behavior, and no duplicate framework persistence.
- Docs updated: Phase 10 checkpoint, task board, project index, file inventory, change journal, OpenSpec tasks.
- Follow-up notes: Commit `fe4aaee` fast-forward merged to local `main`; no push performed. No Web UI, migration, provider calls, broad `worlds.py` routes, or archive were added.

## v0.9 Phase 9 Demo World Assembly planning/implementation entry

- Date: 2026-05-17
- Branch: feat/v0.9-demo-world-assembly
- Scope: v0.9 Self-use MVP Demo World Cut Phase 9 only.
- Summary: Added backend/API-first demo world assembly under the existing authoring review/apply boundary. The new assembly endpoint creates a reviewable `demo_world_assembly` proposal from applied persona, memory, visual, voice, visual generation profile, and reviewed dialogue evidence; approved apply creates a manual-chain conversation session, participants, seed turn, and initial presentation references without provider calls, canon mutation, broad `worlds.py` routes, or world-event writes.
- Files changed: `backend/packages/authoring/**`, `backend/services/api/src/noveland/services/api/authoring.py`, authoring service/API tests, OpenSpec tasks, and harness docs.
- Tests added/updated: Authoring service/API and conversation presentation coverage for reviewable assembly creation, approval-before-apply enforcement, missing evidence blocking, admin ACL/member rejection, source traceability preservation, manual-chain conversation entry, presentation seed refs, and no storage/path/base64/raw prompt/raw output leaks.
- Docs updated: Phase 9 checkpoint, task board, active handoff, project index, file inventory, change journal, OpenSpec tasks.
- Follow-up notes: Commit `2833233` fast-forward merged to local `main`; no push performed. No Web UI and no migration were added; `impeccable` was not needed. Phase 10 should add the self-use MVP gate evidence/checklist without replacing v1.0 beta readiness.

## v0.9 Phase 8 Voice Profile Mapping planning/implementation entry

- Date: 2026-05-17
- Branch: feat/v0.9-voice-profile-mapping
- Scope: v0.9 Self-use MVP Demo World Cut Phase 8 only.
- Summary: Added reviewed apply support for imported voice-reference proposals. Approved voice matches create or reuse `VoiceProfile` records, bind them to agents through `VoiceProfileService`, preserve provider/provider voice IDs without secret resolution, carry style/emotion hints into binding overrides, mark approved audio as voice-reference candidates, and leave TTS/STT execution on existing speech/provider paths.
- Files changed: `backend/packages/authoring/**`, authoring service tests, OpenSpec tasks, and harness docs.
- Tests added/updated: Authoring/speech/provider lab tests cover reviewed voice apply, fake TTS smoke through the applied agent binding, MiMo/custom gateway template reuse without hardcoded endpoints, provider voice ID propagation without secret leakage, audio-only validation, no storage/path/base64/raw prompt/raw output leaks, and no world-event writes.
- Docs updated: Phase 8 checkpoint, task board, active handoff, project index, file inventory, change journal, OpenSpec tasks.
- Follow-up notes: Commit `568061b` fast-forward merged to local `main`; no push performed. Phase 8 added no Web UI and no migration; `impeccable` was not needed. Phase 9 should assemble a minimal demo world from reviewed/applied authoring, persona/memory, visual, voice, and dialogue outputs.

## v0.9 Phase 7 Visual Asset Mapping planning/implementation entry

- Date: 2026-05-17
- Branch: feat/v0.9-visual-asset-mapping
- Scope: v0.9 Self-use MVP Demo World Cut Phase 7 only.
- Summary: Added reviewed apply support for imported visual asset mapping proposals. Approved sprite matches create or reuse `CharacterSpriteSet` records and create `CharacterSpriteVariant` bindings through `VisualAssetService`; approved background matches create `SceneBackgroundProfile` bindings; approved CG matches are recorded as safe media metadata/generation-reference candidates because there is no first-class CG binding table yet. The phase preserves source traceability, worldline isolation, restricted-media rejection, and no `world_events` writes.
- Files changed: `backend/packages/authoring/**`, authoring service tests, OpenSpec tasks, and harness docs.
- Tests added/updated: Authoring service/API/visual tests cover reviewed sprite/background/CG apply, fallback/default sprite/background behavior, generation-reference metadata, cross-worldline rejection, restricted media behavior through existing matching rules, no storage/path/base64/raw prompt/raw output leaks, and no world-event writes.
- Docs updated: Phase 7 checkpoint, task board, active handoff, project index, file inventory, change journal, OpenSpec tasks.
- Follow-up notes: Commit `f9ee434` fast-forward merged to local `main`; no push performed. Phase 7 added no Web UI and no migration; `impeccable` was not needed. Phase 8 should reuse speech voice profiles, agent voice bindings, and style mappings for reviewed voice profile mapping.

## v0.9 Phase 6 Character Memory Distillation Agent planning/implementation entry

- Date: 2026-05-17
- Branch: feat/v0.9-character-memory-distillation
- Scope: v0.9 Self-use MVP Demo World Cut Phase 6 only.
- Summary: Added provider-backed character memory distillation under the existing authoring boundary. The implementation uses `ProviderExecutionService` for text distillation evidence, creates reviewable persona, memory, and visual-generation-profile recommendation proposals, and only writes `AgentPersona`, `Agent.character_profile`, and `AgentMemoryItem` after explicit proposal approval/apply. It preserves source traceability and does not modify `MemoryWriteJob.source_kind`, canon, visual bindings, voice bindings, world state, or world events.
- Files changed: `backend/packages/authoring/**`, `backend/services/api/src/noveland/services/api/authoring.py`, authoring service/API tests, OpenSpec tasks, and harness docs.
- Tests added/updated: Authoring service/API coverage for provider invocation/prompt snapshot evidence, proposal-only distillation, visual profile recommendations as review-only proposals, explicit approval before persona/memory mutation, traceable applied persona and memory metadata, admin ACL, no storage/path/base64/raw prompt/raw output/prompt snapshot response leaks, and no `world_events` writes.
- Docs updated: Phase 6 checkpoint, task board, active handoff, project index, file inventory, change journal, OpenSpec tasks.
- Follow-up notes: Commit `6d97262` fast-forward merged to local `main`; no push performed. Phase 6 added no Web UI and no migration; `impeccable` was not needed. Phase 7 should reuse authoring asset-match proposals and existing visual records for reviewed visual asset mapping.

## v0.9 Phase 4 Galgame Source Intake planning/implementation entry

- Date: 2026-05-17
- Branch: feat/v0.9-galgame-source-intake
- Scope: v0.9 Self-use MVP Demo World Cut Phase 4 only.
- Summary: Added a migration-free galgame source intake path that previews and applies user-provided already-unpacked source directories through existing authoring and media boundaries. The implementation rejects packed/archive/executable-like inputs, does not unpack/decrypt/crack/bypass DRM, stores accepted media as private imported-original media assets/objects, stores script/profile/route text as bounded source fragments, and returns safe source refs and filenames without raw filesystem paths or storage URIs.
- Files changed: `backend/packages/authoring/src/noveland/authoring/galgame_intake.py`, authoring contracts/API, media upload source-kind support, authoring service/API tests, OpenSpec tasks, and harness docs.
- Tests added/updated: Authoring service/API coverage for preview inventory, apply import records, source traceability, media objects, generation reference candidate metadata, archive rejection, confirmation requirement, admin ACL, no storage/path/base64/raw-prompt response leaks, and no `world_events` writes.
- Docs updated: Phase 4 checkpoint, task board, active handoff, project index, file inventory, change journal, OpenSpec tasks.
- Follow-up notes: Commit `9d7e985` fast-forward merged to local `main`; no push performed. Phase 5 should reuse source fragments from this intake for deterministic script dialogue extraction. Phase 4 added no Web UI and no migration; `impeccable` was not needed.

## v0.9 Phase 5 Script Dialogue Extraction planning/implementation entry

- Date: 2026-05-17
- Branch: feat/v0.9-script-dialogue-extraction
- Scope: v0.9 Self-use MVP Demo World Cut Phase 5 only.
- Summary: Enhanced the existing deterministic authoring parser so script fragments produce reviewable proposals with dialogue line text, emotion hints, relationship hints, and manual-label candidates for unknown script lines. Provider-backed extraction remains out of scope for Phase 5, so there are no model calls, provider spend, prompt snapshots, or invocation ledger writes.
- Files changed: `backend/packages/authoring/src/noveland/authoring/parser.py`, authoring contracts/service result counts, authoring service/API tests, OpenSpec tasks, and harness docs.
- Tests added/updated: Authoring service/API/regression fixture coverage for enriched dialogue proposals, emotion/relationship/manual-label counts, source traceability, ACL through existing authoring API, no world-event writes, and no storage leak markers.
- Docs updated: Phase 5 checkpoint, task board, active handoff, project index, change journal, OpenSpec tasks.
- Follow-up notes: Commit `b688247` fast-forward merged to local `main`; no push performed. Phase 6 can consume reviewed dialogue and manual-label proposals. Phase 5 added no Web UI and no migration; `impeccable` was not needed.

## v0.9 Phase 3 Provider Worktree Integration Test Harness planning/implementation entry

- Date: 2026-05-17
- Branch: feat/v0.9-provider-worktree-harness
- Scope: v0.9 Self-use MVP Demo World Cut Phase 3 only.
- Summary: Added a provider lab checkpoint, operator worktree instructions, a strict `real_provider` pytest marker, default-skip opt-in convention through `NOVELAND_RUN_REAL_PROVIDER_TESTS=1`, and fake/mock provider contract tests for the required LLM, speech, image, ComfyUI, and generic provider families. No migrations, Web UI, API route changes, runtime behavior changes, or default real provider calls were added.
- Files changed: `docs/agent/harness/feature-updates/v0.9.3-provider-worktree-integration-harness-plan.md`, `docs/agent/operations/provider-lab.md`, `backend/pyproject.toml`, `backend/tests/test_provider_lab_harness.py`, OpenSpec tasks, and harness docs.
- Tests added/updated: `backend/tests/test_provider_lab_harness.py` covers required provider templates, model discovery manual fallback, fake provider parity, OpenAI-compatible and Anthropic-compatible dry-run text execution, MiMo TTS/ASR dry-run execution, visual generation mapping for ComfyUI/Z-Image/GPT/OpenAI-compatible/generic image providers, and default-skipped real-provider examples.
- Docs updated: Provider lab operation doc, Phase 3 checkpoint, task board, active handoff, project index, file inventory, change journal, OpenSpec tasks.
- Follow-up notes: Phase 4 Galgame Source Intake should start from clean local `main` after Phase 3 validation and fast-forward merge. Keep accepting only user-provided already-unpacked assets; no cracking, unpacking, DRM bypass, or raw path/source leakage.

## v0.9 Phase 2 Visual Generation Control Plane planning entry

- Date: 2026-05-16
- Branch: main
- Scope: v0.9 Self-use MVP Demo World Cut Phase 2 planning checkpoint
- Summary: Added the docs-only Phase 2 checkpoint for a dedicated Visual Generation Control Plane package/router/schema boundary. The plan assigns ownership to `backend/packages/visual_generation/` and `visual_generation.py`, expects a migration for workflow templates, visual model inventory, character/worldline visual generation profiles, and provider-neutral generation plans, and preserves the template/slot boundary that forbids runtime agents from executing arbitrary ComfyUI workflow JSON.
- Files changed: `/docs/agent/harness/feature-updates/v0.9.2-visual-generation-control-plane-plan.md`, `/docs/agent/harness/**`, `/openspec/changes/v0-9-self-use-mvp-demo-world-cut/tasks.md`
- Tests added/updated: N/A
- Docs updated: Phase 2 checkpoint, project index, file inventory, task board, active handoff, change journal, OpenSpec tasks
- Follow-up notes: Implement Phase 2 on `feat/v0.9-visual-generation-control-plane`. Do not add Web UI unless minimal admin diagnostics are explicitly needed, and use `impeccable` first if Web work is included. Do not build a ComfyUI graph editor, do not add broad `worlds.py` routes, and do not run real providers by default.

## v0.9.2 Visual Generation Control Plane implementation entry

- Date: 2026-05-17
- Branch: feat/v0.9-visual-generation-control-plane
- Scope: v0.9 Phase 2 backend/API-first Visual Generation Control Plane only.
- Summary: Added dedicated `visual_generation` package and app-level visual-generation router for workflow templates, workflow template versions, visual model inventory, strict-worldline character visual generation profiles, provider-neutral visual generation plans, reference records, slot validation, and validation-only/dry-run provider mapping across ComfyUI, Z-Image, GPT/OpenAI-compatible image, and generic custom HTTP providers. Phase 2 performs no real provider calls by default, adds no Web UI, does not touch `worlds.py`, does not execute arbitrary runtime ComfyUI workflow JSON, and keeps AI-assisted profile/workflow changes review/apply-only through profile review state and safe plan source context.
- Files changed: `backend/packages/visual_generation/**`, `backend/services/api/src/noveland/services/api/visual_generation.py`, API app registration, backend workspace/package metadata, migration `20260517_0045_visual_generation_control_plane.py`, schema/import tests, targeted service/API tests, OpenSpec tasks, and harness docs.
- Tests added/updated: visual generation service and API tests for template/version CRUD, slot validation, model inventory filtering, strict worldline profiles, LoRA allowed/banned/base-model checks, provider-neutral plan validation, ComfyUI/Z-Image/OpenAI/generic dry-run mapping, raw workflow rejection, cross-worldline reference rejection, restricted inventory suppression, no-leak payload/reference metadata validation, no world-event pollution, and no provider invocation writes.
- Verification: Targeted Phase 2 tests passed (`40 passed`; focused service/API rerun `12 passed`, then service-only hardening rerun `8 passed`). Full backend gate passed after hardening: ruff, mypy (`300 source files`), and pytest (`466 passed, 7 skipped`). Web was not touched; Web lint/typecheck/unit/build/check:next-env passed (`128 passed`). Docker compose config, OpenSpec strict changes/specs validation, and `git diff --check` passed.
- Follow-up notes: Fast-forward merge Phase 2 to local `main` after validation. Next accepted v0.9 work is Phase 3 Provider Worktree Integration Test Harness only when explicitly requested. Web e2e was not required because Phase 2 touched no Web files; no push performed.

## v0.9-v1.1 OpenSpec milestone roadmap entry

- Date: 2026-05-16
- Branch: main
- Scope: OpenSpec roadmap planning for v0.9 Self-use MVP Demo World Cut, v1.0 Private Beta MVP, and v1.1 Normal Use / Release Candidate
- Summary: Added active OpenSpec roadmap changes for the next three milestones, shifting the project from platform expansion toward self-use playable demo, private beta, and release-candidate readiness.
- Files changed: `/openspec/changes/v0-9-self-use-mvp-demo-world-cut/**`, `/openspec/changes/v1-0-private-beta-mvp/**`, `/openspec/changes/v1-1-normal-use-release-candidate/**`, `/docs/agent/harness/**`
- Tests added/updated: N/A
- Docs updated: OpenSpec proposals/designs/phase plans/tasks/specs plus project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Do not implement v0.9 until a feasibility review is written and accepted. v1.0 requires v0.9 completion/archive first; v1.1 requires v1.0 completion/archive first. No backend/Web runtime behavior changed.

## v0.9 Visual Generation Control Plane OpenSpec update entry

- Date: 2026-05-16
- Branch: main
- Scope: OpenSpec roadmap update for v0.9 Self-use MVP Demo World Cut
- Summary: Inserted Visual Generation Control Plane as v0.9 Phase 2, adding provider-neutral image generation planning across ComfyUI, Z-Image, GPT Image, OpenAI-compatible image APIs, and generic image providers. The plan forbids arbitrary runtime agent ComfyUI workflow JSON execution and uses versioned workflow templates, validated slots, model inventory, character visual generation profiles, and reviewable AI-assisted workflow/profile proposals.
- Files changed: `/openspec/changes/v0-9-self-use-mvp-demo-world-cut/**`, `/docs/agent/harness/**`
- Tests added/updated: N/A
- Docs updated: v0.9 proposal, design, phase plan, tasks, affected v0.9 specs, new visual-generation-control-plane spec, project index, file inventory, active handoff, and change journal.
- Follow-up notes: Future v0.9 feasibility review must resolve package/router/schema ownership for workflow templates, model inventory, visual generation profiles, and provider-neutral visual generation plans before implementation. No backend/Web runtime behavior changed.

## v0.8 Public Experience & Ecosystem archive entry

- Date: 2026-05-16
- Branch: main
- Scope: OpenSpec archive, v0.8 current specs, release notes, and harness bookkeeping
- Summary: Archived the completed v0.8 Public Experience & Ecosystem OpenSpec change, synced implemented public experience capabilities into current OpenSpec specs, and added v0.8 release notes.
- Files changed: `/openspec/specs/**`, `/openspec/changes/archive/2026-05-16-v0-8-public-experience-ecosystem/**`, `/docs/agent/harness/**`
- Tests added/updated: N/A
- Docs updated: OpenSpec current specs, OpenSpec archive, v0.8 release notes, project index, file inventory, task board, active handoff
- Follow-up notes: v0.8 is closed. v0.6 and v0.7 remain locally complete and ready to archive only if explicitly requested. Do not push unless explicitly requested.

## v0.6/v0.7 OpenSpec historical archive cleanup entry

- Date: 2026-05-16
- Branch: main
- Scope: OpenSpec historical archive cleanup and current spec sync
- Summary: Archived the completed v0.6 Runtime Narrative Quality and v0.7 Production Hardening OpenSpec changes so `openspec validate --changes --strict` has no active changes remaining.
- Files changed: `/openspec/specs/**`, `/openspec/changes/archive/2026-05-16-v0-6-runtime-narrative-quality/**`, `/openspec/changes/archive/2026-05-16-v0-7-production-hardening/**`, `/docs/agent/harness/**`
- Tests added/updated: N/A
- Docs updated: OpenSpec current specs, OpenSpec archives, project index, file inventory, task board, active handoff
- Follow-up notes: v0.6/v0.7 release notes were not requested and were not generated. No backend/Web runtime behavior changed.

## Initial entry

- Date: TBD
- Branch: TBD
- Scope: docs/agent
- Summary: Initial governance package created.
- Files changed: `/docs/agent/**`
- Tests added/updated: N/A
- Docs updated: initial package
- Follow-up notes: scaffold repository next

## v0.5 Authoring & Import Studio archive entry

- Date: 2026-05-15
- Branch: main
- Scope: OpenSpec archive, v0.5 current specs, release notes, and harness bookkeeping
- Summary: Archived the completed v0.5 Authoring & Import Studio OpenSpec change, synced implemented authoring/import capabilities into current OpenSpec specs, and added v0.5 release notes.
- Files changed: `/openspec/specs/**`, `/openspec/changes/archive/2026-05-15-v0-5-authoring-import-studio/**`, `/docs/agent/harness/**`
- Tests added/updated: N/A
- Docs updated: OpenSpec current specs, OpenSpec archive, v0.5 release notes, project index, file inventory, task board, active handoff
- Follow-up notes: Start v0.6 with feasibility review only; do not implement v0.6 until architecture scope is accepted.

## v0.6 Runtime Narrative Quality feasibility review entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.6 OpenSpec feasibility review
- Summary: Reviewed the proposed v0.6 Runtime Narrative Quality change against current main and identified required OpenSpec revisions before implementation.
- Files changed: `/docs/agent/harness/feature-updates/v0.6-runtime-narrative-quality-feasibility-review.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A
- Docs updated: v0.6 feasibility review, project index, change journal, task board, active handoff
- Follow-up notes: Update v0.6 OpenSpec before implementation; provider text execution alignment and narrative artifact worldline strategy are the main pre-implementation decisions.

## v0.6.1 Runtime Context Contract v2 planning entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.6 Runtime Narrative Quality Phase 1 planning
- Summary: Added the Phase 1 implementation checkpoint for runtime context contracts and the dedicated narrative quality package/router boundary.
- Files changed: `/docs/agent/harness/feature-updates/v0.6.1-runtime-context-contract-v2-plan.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A
- Docs updated: project index, file inventory, change journal, active handoff
- Follow-up notes: Implement Phase 1 on `feat/runtime-context-contract-v2`; do not add Web UI or broad `worlds.py` routes.

## v0.6.5 Narrative Writer v2 planning entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.6 Runtime Narrative Quality Phase 5 planning
- Summary: Added the Phase 5 implementation checkpoint for Narrative Writer v2, including first-class narrative artifact/publication worldline strategy and provider-kernel text generation boundaries.
- Files changed: `/docs/agent/harness/feature-updates/v0.6.5-narrative-writer-v2-plan.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A
- Docs updated: project index, file inventory, change journal, task board, active handoff
- Follow-up notes: Implement Phase 5 on `feat/narrative-writer-v2`; do not add Web UI, broad `worlds.py` routes, legacy provider profile expansion, automatic publication, or world event writes.

## v0.6.5 Narrative Writer v2 implementation entry

- Date: 2026-05-15
- Branch: feat/narrative-writer-v2
- Scope: v0.6 Runtime Narrative Quality Phase 5 implementation
- Summary: Added first-class nullable narrative artifact/publication worldline columns and an admin-only Narrative Writer v2 generation API that uses provider-kernel text execution to create strict-worldline draft artifacts.
- Files changed: `/backend/packages/narrative/**`, `/backend/packages/narrative_quality/**`, `/backend/services/api/src/noveland/services/api/narrative_quality.py`, `/backend/migrations/**`, `/backend/tests/**`, `/docs/agent/harness/**`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`
- Tests added/updated: narrative quality service/API tests for writer v2, narrative writer publication worldline assertion, schema metadata, Alembic head, provider execution regression
- Docs updated: task board, active handoff, change journal, migrations README
- Follow-up notes: Full local gate must pass before fast-forward merge. Phase 5 does not publish artifacts, write world events, expand legacy provider profiles, or add Web UI.

## v0.6.5 Narrative Writer v2 merge entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.6 Runtime Narrative Quality Phase 5 merge bookkeeping
- Summary: Recorded successful full local gate and fast-forward merge for Narrative Writer v2.
- Files changed: `/docs/agent/harness/**`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`
- Tests added/updated: N/A
- Docs updated: task board, active handoff, change journal, OpenSpec tasks
- Follow-up notes: Begin Phase 6 Continuity Review v2 from clean local `main`; no push performed.

## v0.6.6 Continuity Review v2 planning entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.6 Runtime Narrative Quality Phase 6 planning
- Summary: Added the Phase 6 implementation checkpoint for API-first Continuity Review v2, reusing existing guardrail review records and forbidding automatic repair, provider calls, Web UI, and broad `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.6.6-continuity-review-v2-plan.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A
- Docs updated: project index, file inventory, change journal, task board, active handoff
- Follow-up notes: Implement Phase 6 on `feat/continuity-review-v2`; no migration expected.

## v0.6.6 Continuity Review v2 implementation entry

- Date: 2026-05-15
- Branch: feat/continuity-review-v2
- Scope: v0.6 Runtime Narrative Quality Phase 6 implementation
- Summary: Added an admin-only Continuity Review v2 API under the narrative quality router, reusing `LivingWorldGuardrailService.review_narrative_continuity` and existing `NarrativeContinuityReview` records while returning safe findings, conflict reports, repair suggestions, and evidence refs.
- Files changed: `/backend/packages/narrative_quality/**`, `/backend/services/api/src/noveland/services/api/narrative_quality.py`, `/backend/tests/**`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`
- Tests added/updated: narrative quality service/API tests for artifact review, explicit text review, hidden secret leak, time/knowledge risks, relationship jumps, route context gaps, cross-worldline rejection, sensitive metadata rejection, ACL, and response redaction.
- Docs updated: OpenSpec tasks
- Follow-up notes: Full local gate must pass before fast-forward merge. Phase 6 does not add provider calls, automatic repair apply, Web UI, broad `worlds.py` routes, or world event writes.

## v0.6.6 Continuity Review v2 merge entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.6 Runtime Narrative Quality Phase 6 merge bookkeeping
- Summary: Recorded successful targeted tests, full local gate, and fast-forward merge for Continuity Review v2.
- Files changed: `/docs/agent/harness/**`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`
- Tests added/updated: N/A
- Docs updated: project index, task board, active handoff, change journal, OpenSpec tasks
- Follow-up notes: Begin Phase 7 Runtime Pacing Controller from clean local `main`; no push performed.

## v0.6.7 Runtime Pacing Controller planning entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.6 Runtime Narrative Quality Phase 7 planning
- Summary: Added the Phase 7 implementation checkpoint for API-first runtime pacing diagnostics, reusing asset generation policies/proposals and media jobs while forbidding daemon hooks, provider calls, automatic spend, Web UI, and broad `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.6.7-runtime-pacing-controller-plan.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A
- Docs updated: project index, file inventory, change journal, task board, active handoff
- Follow-up notes: Implement Phase 7 on `feat/runtime-pacing-controller`; no migration expected.

## v0.6.7 Runtime Pacing Controller implementation entry

- Date: 2026-05-15
- Branch: feat/runtime-pacing-controller
- Scope: v0.6 Runtime Narrative Quality Phase 7 implementation
- Summary: Added an admin-only runtime pacing review API under the narrative quality router, summarizing pending media jobs, asset generation proposal budget pressure, lookahead coverage, current-turn asset gaps, offscreen compression opportunities, and safe recommendations without mutating media jobs, running providers, creating asset-generation jobs, writing world events, or adding Web UI.
- Files changed: `/backend/packages/narrative_quality/src/noveland/narrative_quality/contracts.py`, `/backend/packages/narrative_quality/src/noveland/narrative_quality/service.py`, `/backend/services/api/src/noveland/services/api/narrative_quality.py`, `/backend/tests/test_api_narrative_quality.py`, `/backend/tests/test_narrative_quality_service.py`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`
- Tests added/updated: narrative quality service/API tests for queue summaries, policy limits, duplicate invalidation keys, budget overflow, current-turn asset gaps, cross-worldline rejection, response sanitization, and admin ACL.
- Docs updated: OpenSpec tasks
- Follow-up notes: Full local gate passed before fast-forward merge. Phase 7 did not add migrations, provider calls, media job mutations, daemon hooks, Web UI, broad `worlds.py` routes, or world event writes.

## v0.6.7 Runtime Pacing Controller merge entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.6 Runtime Narrative Quality Phase 7 merge bookkeeping
- Summary: Recorded successful targeted tests, full local gate, and fast-forward merge for Runtime Pacing Controller. OpenSpec Phase 7 tasks now mark full local gate, fast-forward merge, and harness update complete.
- Files changed: `/docs/agent/harness/**`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`
- Tests added/updated: N/A
- Docs updated: project index, task board, active handoff, change journal, OpenSpec tasks
- Follow-up notes: Begin Phase 8 Route & Relationship Progression Quality from clean local `main`; no push performed.

## v0.6.8 Route & Relationship Progression Quality planning entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.6 Runtime Narrative Quality Phase 8 planning
- Summary: Added the Phase 8 implementation checkpoint for API-first route and relationship progression diagnostics, reusing relationship edges, route affinities, milestones, endings, player choices, GM proposals, plot threads, and world events while forbidding canonical mutation, provider calls, Web UI, broad `worlds.py` routes, and replacement relationship semantics.
- Files changed: `/docs/agent/harness/feature-updates/v0.6.8-route-relationship-progression-quality-plan.md`, `/docs/agent/harness/**`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`
- Tests added/updated: N/A
- Docs updated: project index, file inventory, change journal, task board, active handoff, OpenSpec tasks
- Follow-up notes: Implement Phase 8 on `feat/route-relationship-progression-quality`; no migration expected.

## v0.6.8 Route & Relationship Progression Quality implementation entry

- Date: 2026-05-15
- Branch: feat/route-relationship-progression-quality
- Scope: v0.6 Runtime Narrative Quality Phase 8 implementation
- Summary: Added an admin-only route and relationship progression review API under the narrative quality router. The implementation reads existing relationship edges, route affinities, milestones, endings, player choices, GM proposals, and recent world events to return safe summaries, findings, and review-only recommendations without provider calls, canonical mutation, world event writes, Web UI, broad `worlds.py` routes, migrations, or replacement relationship semantics.
- Files changed: `/backend/packages/narrative_quality/src/noveland/narrative_quality/contracts.py`, `/backend/packages/narrative_quality/src/noveland/narrative_quality/service.py`, `/backend/services/api/src/noveland/services/api/narrative_quality.py`, `/backend/tests/test_api_narrative_quality.py`, `/backend/tests/test_narrative_quality_service.py`
- Tests added/updated: narrative quality service/API tests for progression summaries, contradictory relationship metrics, route stage/milestone mismatch, unsatisfied ending requirements, high-risk progression proposal pressure, cross-worldline route rejection, response sanitization, no mutation side effects, and admin ACL.
- Docs updated: N/A
- Follow-up notes: Full local gate passed before fast-forward merge. Phase 8 did not add migrations, provider calls, canonical mutations, Web UI, broad `worlds.py` routes, or world event writes.

## v0.6.8 Route & Relationship Progression Quality merge entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.6 Runtime Narrative Quality Phase 8 merge bookkeeping
- Summary: Recorded successful targeted tests, full local gate, and fast-forward merge for Route & Relationship Progression Quality. OpenSpec Phase 8 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/docs/agent/harness/**`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`
- Tests added/updated: N/A
- Docs updated: project index, task board, active handoff, change journal, OpenSpec tasks
- Follow-up notes: Begin Phase 9 Long-run Living World Simulation Eval from clean local `main`; no push performed.

## v0.6.9 Long-run Living World Simulation Eval planning entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.6 Runtime Narrative Quality Phase 9 planning
- Summary: Added the Phase 9 implementation checkpoint for an API-first long-run living world simulation eval under the narrative quality boundary. The plan reuses `LongRunEvalRun` and `LivingWorldBetaService.run_long_eval()` for persisted metrics and forbids duplicate eval tables, provider calls, runtime daemon simulation, Web UI, broad `worlds.py` routes, and release gate semantic changes.
- Files changed: `/docs/agent/harness/feature-updates/v0.6.9-long-run-living-world-simulation-eval-plan.md`, `/docs/agent/harness/**`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`
- Tests added/updated: N/A
- Docs updated: project index, file inventory, change journal, task board, active handoff, OpenSpec tasks
- Follow-up notes: Implement Phase 9 on `feat/long-run-living-world-simulation-eval`; no migration expected.

## Storage backup auth runtime ops entry

- Date: 2026-05-04
- Branch: feat/storage-backup-auth-runtime-ops
- Scope: snapshot object storage, backup/restore ops, migration safety, auth hardening, runtime identity
- Summary: Added local object storage for new world snapshot replay payloads with inline fallback, backup verification tooling and playbook, Alembic safety checks, configurable auth session/cookie policy, seed-admin password validation, and centralized runtime actor identity for runtime-created events.
- Files changed: `/backend/packages/storage/**`, `/backend/packages/events/src/noveland/events/replay.py`, `/backend/services/api/src/noveland/services/api/{auth,csrf,worlds}.py`, `/backend/services/runtime/src/noveland/services/runtime/**`, `/backend/packages/core/src/noveland/core/settings.py`, `/backend/packages/auth/src/noveland/auth/seed_admin.py`, `/backend/packages/conversations/src/noveland/conversations/services.py`, `/backend/tests/**`, `/web/features/**`, `/web/lib/worlds/**`, `/.env.example`, `/README.md`, `/docs/agent/**`
- Tests added/updated: replay snapshot URI/integrity tests, migration safety tests, auth cookie policy tests, runtime daemon actor-ref tests, and Web snapshot metadata tests.
- Docs updated: README, backup/restore playbook, migrations README, project index, file inventory, task board, active handoff
- Follow-up notes: backup/restore remains local operator-driven; Web restore actions, remote object storage providers, and production secret/session policy enforcement remain later roadmap work.

## Access diagnostics scale readiness ops entry

- Date: 2026-05-04
- Branch: feat/access-diagnostics-scale-roadmap-plan
- Scope: access review, diagnostic retention, metrics, runtime supervision, deployment/performance ops, memory eval/backfill, queue readiness, sandbox design
- Summary: Added world access review and membership audit diagnostics, diagnostic retention dry-run/prune endpoints, platform-admin metrics and runtime supervision surfaces, memory eval recommendations, bounded memory backfill execution, DB queue readiness reporting, and ops docs for deployment, supervision, performance, diagnostics, queue readiness, and sandbox options.
- Files changed: `/backend/packages/observability/**`, `/backend/packages/memory/**`, `/backend/services/api/src/noveland/services/api/{runtime,worlds}.py`, `/backend/tests/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: runtime API tests for metrics/supervision/diagnostic retention/memory backfill/queue readiness; world API tests for access review and membership audit diagnostics; memory service tests for backfill idempotency and queue readiness.
- Docs updated: README, operations docs, project index, file inventory, task board, active handoff
- Follow-up notes: sandbox remains design-only; metrics are local text output; external queue adoption remains out of scope until a later queue migration phase.

## Runnable skeleton entry

- Date: 2026-04-15
- Branch: feat/bootstrap-runnable-skeleton
- Scope: repository scaffold
- Summary: Added runnable backend, web, contracts, and local infrastructure skeletons without implementing sensitive domain behavior.
- Files changed: `/README.md`, `/.editorconfig`, `/.gitignore`, `/.env.example`, `/backend/**`, `/web/**`, `/contracts/README.md`, `/infra/compose.yaml`, `/docs/agent/harness/**`
- Tests added/updated: backend health/import/Alembic config tests; frontend status component test; Playwright dashboard smoke test
- Docs updated: project index, file inventory, task board, debug journal, active handoff
- Follow-up notes: implement core database schema, plugin registry, world clock, event/snapshot baseline, and auth/session baseline as separate tasks.

## Core schema entry

- Date: 2026-04-15
- Branch: main
- Scope: core database schema
- Summary: Added SQLAlchemy metadata, core ORM models, first Alembic migration, and parameterized local database ports.
- Files changed: `/backend/packages/core/**`, `/backend/packages/auth/**`, `/backend/packages/worlds/**`, `/backend/packages/agents/**`, `/backend/migrations/**`, `/backend/tests/**`, `/.env.example`, `/infra/compose.yaml`, `/README.md`, `/docs/agent/**`
- Tests added/updated: schema metadata tests; workspace import coverage for ORM modules
- Docs updated: configuration/secrets, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: plugin registry, world clock state, event/snapshot baseline, and auth/session baseline remain separate tasks.

## Plugin registry skeleton entry

- Date: 2026-04-15
- Branch: feat/plugin-registry-skeleton
- Scope: plugin registry skeleton
- Summary: Added code-registered plugin contracts, manifest/config validation, typed registry errors, and contract tests.
- Files changed: `/backend/packages/plugins/**`, `/backend/tests/test_plugin_registry.py`, `/backend/tests/test_workspace_imports.py`, `/docs/agent/architecture/plugin-architecture.md`, `/docs/agent/harness/**`
- Tests added/updated: plugin registry contract tests; workspace import coverage for plugin modules
- Docs updated: plugin architecture, project index, file inventory, task board, active handoff
- Follow-up notes: world clock state model, event/snapshot baseline, and auth/session baseline remain separate tasks.

## World clock state model entry

- Date: 2026-04-15
- Branch: feat/world-clock-state-model
- Scope: world clock state model
- Summary: Added immutable world clock state transitions, current clock state persistence, transition audit persistence, and schema tests.
- Files changed: `/backend/packages/worlds/**`, `/backend/migrations/versions/20260415_0002_world_clock_state.py`, `/backend/tests/**`, `/backend/migrations/README.md`, `/docs/agent/architecture/world-clock-and-scheduling.md`, `/docs/agent/architecture/data-ownership.md`, `/docs/agent/harness/**`
- Tests added/updated: world clock pure logic tests; schema metadata coverage for clock tables; workspace import coverage for `noveland.worlds.clock`
- Docs updated: world clock scheduling, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: event/snapshot baseline and auth/session baseline remain separate tasks; runtime ticking, scheduling, calendar parsing, and UI controls are not implemented.

## Event log and snapshot baseline entry

- Date: 2026-04-16
- Branch: feat/event-snapshot-baseline
- Scope: event log and snapshot baseline
- Summary: Added world event/snapshot contracts, ORM models, Alembic migration, and a minimal transactional event store helper.
- Files changed: `/backend/packages/events/**`, `/backend/packages/core/src/noveland/core/database.py`, `/backend/migrations/versions/20260416_0003_event_snapshot_baseline.py`, `/backend/tests/**`, `/backend/migrations/README.md`, `/docs/agent/architecture/event-and-snapshot-model.md`, `/docs/agent/architecture/data-ownership.md`, `/docs/agent/harness/**`
- Tests added/updated: event contract tests; schema metadata coverage for event/snapshot tables; skipped-by-default PostgreSQL integration test for `WorldEventStore`
- Docs updated: event/snapshot architecture, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: auth/session baseline remains separate; replay engine, runtime event emission, NATS broadcast, UI controls, and object storage writes are not implemented.

## Auth/session baseline entry

- Date: 2026-04-16
- Branch: feat/auth-session-baseline
- Scope: auth/session baseline
- Summary: Added local password credential storage, opaque backend session storage, platform role assignments, typed auth contracts, and service helpers.
- Files changed: `/backend/packages/auth/**`, `/backend/migrations/versions/20260416_0004_auth_session_baseline.py`, `/backend/tests/**`, `/backend/migrations/README.md`, `/docs/agent/architecture/auth-and-access-model.md`, `/docs/agent/architecture/configuration-and-secrets.md`, `/docs/agent/architecture/data-ownership.md`, `/docs/agent/harness/**`
- Tests added/updated: auth contract tests; schema metadata coverage for auth tables; skipped-by-default PostgreSQL integration test for credential/session services
- Docs updated: auth/access model, configuration/secrets, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: login HTTP API, cookie/CSRF policy, OAuth/OIDC, password reset, MFA, auth middleware, agent runtime credential, and UI integration remain separate tasks.

## HTTP auth surface entry

- Date: 2026-04-16
- Branch: feat/http-auth-surface
- Scope: HTTP auth surface
- Summary: Added CSRF, login, current user, logout endpoints, API database dependencies, and local platform admin seed command.
- Files changed: `/backend/services/api/**`, `/backend/packages/auth/**`, `/backend/tests/test_api_auth.py`, `/backend/tests/test_api_auth_integration.py`, `/backend/tests/test_workspace_imports.py`, `/README.md`, `/docs/agent/**`
- Tests added/updated: API auth contract tests; skipped-by-default PostgreSQL seed/login/logout integration test; workspace import coverage for new API and seed modules
- Docs updated: README, auth/access model, configuration/secrets, project index, file inventory, task board, active handoff
- Follow-up notes: frontend login UI, OAuth/OIDC, password reset, MFA, authorization middleware, world access enforcement, and production cookie hardening remain separate tasks.

## Web auth integration entry

- Date: 2026-04-16
- Branch: feat/web-auth-integration
- Scope: web auth integration
- Summary: Added same-origin Next auth proxy routes, protected dashboard access, dedicated login page, current-user display, and logout flow.
- Files changed: `/web/app/**`, `/web/features/auth/**`, `/web/lib/auth/**`, `/web/tests/e2e/**`, `/.env.example`, `/README.md`, `/docs/agent/**`
- Tests added/updated: auth client tests; login/logout component tests; proxy helper tests; Playwright auth flow tests with local mock backend
- Docs updated: README, auth/access model, configuration/secrets, project index, file inventory, task board, active handoff
- Follow-up notes: authorization dependencies, world management APIs, real dashboard data, OAuth/OIDC, password reset, MFA, and production cookie hardening remain separate tasks.

## Authorization dependencies entry

- Date: 2026-04-16
- Branch: feat/authorization-dependencies
- Scope: API authorization dependencies
- Summary: Added lightweight platform-admin, world-member, and world-admin checks for backend route dependencies.
- Files changed: `/backend/services/api/**`, `/backend/packages/worlds/**`, `/backend/packages/agents/**`, `/backend/tests/**`, `/docs/agent/**`
- Tests added/updated: authorization dependency tests; workspace import coverage for authorization helpers
- Docs updated: auth/access model, project index, file inventory, task board, active handoff
- Follow-up notes: world management APIs, real dashboard data, broad policy engine, and frontend world access UI remain separate tasks.

## World management API entry

- Date: 2026-04-16
- Branch: feat/world-management-api
- Scope: world management API
- Summary: Added backend endpoints for worlds, scenes, memberships, and agents using the authorization dependency baseline.
- Files changed: `/backend/services/api/**`, `/backend/tests/test_api_worlds.py`, `/backend/tests/test_api_worlds_integration.py`, `/README.md`, `/docs/agent/**`
- Tests added/updated: SQLite-backed world management API tests; skipped-by-default PostgreSQL integration smoke; workspace import coverage for world router
- Docs updated: README, auth/access model, project index, file inventory, task board, active handoff
- Follow-up notes: real dashboard data, runtime loops, event emission, world clock controls, plugin execution, and Web world management UI remain separate tasks.

## World dashboard data entry

- Date: 2026-04-16
- Branch: feat/world-dashboard-data
- Scope: world dashboard data and management console
- Summary: Connected the protected web dashboard to the backend world API, added same-origin world proxy routes, added admin management controls, and extended backend world routes with CSRF, member candidates, membership user summaries, and soft-disable DELETE routes.
- Files changed: `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/test_api_worlds.py`, `/web/app/**`, `/web/features/dashboard/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: backend world API CSRF/member-candidate/soft-disable tests; world client/proxy/component tests; Playwright dashboard management flows with local mock backend
- Docs updated: README, auth/access model, project index, file inventory, task board, active handoff
- Follow-up notes: runtime clock service, event emission, replay, calendar rules, memory backend, and agent loop remain separate tasks.

## Runtime clock service entry

- Date: 2026-04-17
- Branch: feat/runtime-clock-service
- Scope: runtime clock service
- Summary: Added persistent world clock service, automatic clock initialization on world creation, clock control HTTP endpoints, and Web clock controls in the dashboard.
- Files changed: `/backend/packages/worlds/**`, `/backend/services/api/**`, `/backend/tests/**`, `/web/features/dashboard/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: clock service persistence tests; clock API permission/CSRF tests; Web client/component/E2E coverage for clock controls
- Docs updated: README, world clock architecture, project index, file inventory, task board, active handoff
- Follow-up notes: runtime event emission, NATS broadcast, replay, calendar rules, memory backend, and agent loop remain separate tasks.

## Runtime event emission and NATS baseline entry

- Date: 2026-04-17
- Branch: feat/runtime-event-nats-baseline
- Scope: runtime event emission and NATS broadcast baseline
- Summary: Added world event publisher interfaces, NATS event envelope broadcasting, and a finite runtime tick service that advances active running clocks and appends `world.clock_advanced` events.
- Files changed: `/backend/packages/events/**`, `/backend/services/runtime/**`, `/backend/tests/test_runtime_event_emission.py`, `/README.md`, `/docs/agent/**`
- Tests added/updated: runtime tick tests for running/paused clocks, event log append behavior, in-memory publisher envelopes, publish failure visibility, and workspace import coverage
- Docs updated: README, event/snapshot model, world clock architecture, project index, file inventory, task board, active handoff
- Follow-up notes: replay/snapshot restore, infinite runtime loop, external scheduler, agent loop, calendar rules, memory backend, and plugin execution remain separate tasks.

## Replay and snapshot restore baseline entry

- Date: 2026-04-17
- Branch: feat/replay-snapshot-restore
- Scope: replay and snapshot restore baseline
- Summary: Added `world_state.v1` replay reconstruction, inline snapshot creation, replay/snapshot HTTP endpoints, and a Web dashboard replay/snapshot panel.
- Files changed: `/backend/packages/events/**`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/**`, `/web/features/dashboard/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: replay service tests for empty state, latest snapshot plus incremental events, snapshot creation; API tests for replay/snapshot auth and CSRF; Web client/component/E2E coverage for replay and snapshots
- Docs updated: README, event/snapshot model, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: destructive restore, object-storage snapshot payload writes, calendar rules, memory backend, agent loop, narrative behavior, and plugin execution remain separate tasks.

## Calendar and schedule rules baseline entry

- Date: 2026-04-17
- Branch: feat/calendar-schedule-baseline
- Scope: agent calendar entries and world schedule rules
- Summary: Added world-scoped agent calendar entries, weekday/weekend/timetable schedule rules, service-level due resolution, backend APIs, and Web dashboard panels.
- Files changed: `/backend/packages/calendar/**`, `/backend/migrations/versions/20260417_0005_calendar_schedule_baseline.py`, `/backend/services/api/**`, `/backend/tests/**`, `/web/features/dashboard/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: calendar contract/service tests, schema metadata tests, world API tests, Web client/component/E2E coverage
- Docs updated: README, data ownership, world clock/scheduling, project index, file inventory, task board, active handoff
- Follow-up notes: memory vectors, provider profiles, runtime agent loop, narrative artifacts, and plugin execution remain separate tasks.

## Memory backend and local pgvector baseline entry

- Date: 2026-04-17
- Branch: feat/memory-pgvector-baseline
- Scope: private agent memory baseline
- Summary: Added the local pgvector-backed memory contract and ORM model, world-admin memory APIs, migration coverage, and a Web dashboard panel for viewing, adding, searching, and disabling agent memory items.
- Files changed: `/backend/packages/memory/**`, `/backend/migrations/versions/20260417_0006_memory_pgvector_baseline.py`, `/backend/services/api/**`, `/backend/tests/**`, `/web/features/dashboard/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: memory backend contract tests, world API memory tests, schema metadata tests, Web client/component/E2E coverage
- Docs updated: README, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: provider profiles, runtime agent loop, narrative artifacts, and plugin execution remain separate tasks.

## Agent loop and narrative baseline entry

- Date: 2026-04-17
- Branch: feat/agent-loop-narrative-baseline
- Scope: provider profiles, runtime daemon control, agent loop execution, and narrative artifacts
- Summary: Added non-secret provider profiles, database-backed runtime control, a daemon-aware agent loop, manual agent-run and narrative APIs, and Web dashboard panels for runtime/provider/run/artifact operations.
- Files changed: `/backend/packages/adapters/**`, `/backend/packages/agents/src/noveland/agents/models.py`, `/backend/packages/core/**`, `/backend/packages/narrative/**`, `/backend/services/api/**`, `/backend/services/runtime/**`, `/backend/migrations/versions/20260417_0007_agent_narrative_runtime_baseline.py`, `/backend/tests/**`, `/web/app/**`, `/web/features/dashboard/**`, `/web/lib/runtime/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/.env.example`, `/README.md`, `/docs/agent/**`
- Tests added/updated: provider adapter contract tests; runtime daemon iteration test; world API tests for agent runs and narrative artifacts; schema/import coverage for runtime/provider/narrative modules; Web client/component/E2E coverage for runtime controls, provider profiles, agent runs, and narrative artifacts
- Docs updated: README, configuration/secrets, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: production process supervision, richer prompt/runtime policy, provider retry/rate-limit handling, plugin execution, and advanced narrative reader flows remain separate tasks.

## Runtime observability and diagnostics entry

- Date: 2026-04-17
- Branch: feat/runtime-observability-diagnostics
- Scope: runtime/provider/agent diagnostics baseline
- Summary: Added runtime diagnostic event persistence, redacted diagnostic contracts/services, runtime/provider/agent/event-publisher diagnostic writes, admin diagnostics APIs, and Web dashboard diagnostics panels.
- Files changed: `/backend/packages/observability/**`, `/backend/packages/core/src/noveland/core/database.py`, `/backend/services/api/**`, `/backend/services/runtime/**`, `/backend/migrations/versions/20260417_0008_runtime_diagnostics_baseline.py`, `/backend/tests/**`, `/web/app/api/runtime/diagnostics/**`, `/web/features/dashboard/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: observability service/contract tests; runtime/event-publisher diagnostic tests; API diagnostics permission tests; schema/import coverage; Web client/component/mock-backend diagnostics coverage
- Docs updated: README, data ownership, architecture map, project index, file inventory, task board, active handoff
- Follow-up notes: provider timeout/retry/rate-limit hardening, provider test-call health state, and agent observation/persona policy remain separate tasks.

## Plugin runtime wiring entry

- Date: 2026-04-22
- Branch: feat/plugin-runtime-wiring
- Scope: explicit plugin bindings and runtime wiring
- Summary: Added built-in plugin identifiers and registry-backed implementations for model providers, memory backend, world rules, persona policy, and narrative writer; added explicit DB/plugin bindings plus plugin-aware Web configuration surfaces.
- Files changed: `/backend/packages/plugins/**`, `/backend/packages/adapters/**`, `/backend/packages/agents/**`, `/backend/packages/narrative/**`, `/backend/packages/worlds/**`, `/backend/services/api/**`, `/backend/services/runtime/**`, `/backend/migrations/versions/20260422_0015_plugin_runtime_wiring.py`, `/web/app/api/plugins/catalog/**`, `/web/features/admin/**`, `/web/features/agents/**`, `/web/features/conversations/**`, `/web/features/worlds/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/docs/agent/harness/**`
- Tests added/updated: plugin runtime regression through backend `ruff`, `mypy`, and full `pytest`; frontend `lint`, `typecheck`, `vitest`, `playwright`, and production build coverage updated for plugin-aware loaders and forms
- Docs updated: project index, file inventory, task board, active handoff
- Follow-up notes: plugin execution still uses code-registered built-ins only; marketplace, hot reload, and remote installation remain future work.

## Mem0 OSS-first long-term memory entry

- Date: 2026-04-24
- Branch: feat/memory-mem0-oss-foundation
- Scope: long-term memory refactor
- Summary: Replaced the old synchronous pgvector CRUD memory baseline with a Mem0 OSS-first long-term memory stack, including platform memory backend profiles, async memory write jobs/logs, conversation and runtime memory context integration, read-only web memory surfaces, profile snapshots, forget flows, and eval/health operators.
- Files changed: `/.env.example`, `/README.md`, `/backend/packages/core/src/noveland/core/settings.py`, `/backend/packages/memory/**`, `/backend/packages/plugins/**`, `/backend/packages/worlds/**`, `/backend/packages/conversations/**`, `/backend/services/api/**`, `/backend/services/runtime/**`, `/backend/migrations/versions/20260423_0016_memory_mem0_oss_foundation.py`, `/backend/migrations/versions/20260423_0017_memory_context_integration.py`, `/backend/migrations/versions/20260423_0018_memory_profiles_forget_evals.py`, `/backend/tests/**`, `/web/app/admin/memory-backends/**`, `/web/app/api/memory-backend-profiles/**`, `/web/features/admin/memory-backend-admin.tsx`, `/web/features/agents/agent-builder.tsx`, `/web/features/conversations/conversation-detail.tsx`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/docs/agent/harness/**`
- Tests added/updated: backend memory backend/service/API/runtime/schema/import tests; web type/client/component coverage for read-only memory and admin memory backend flows; Playwright mock backend updated for memory profiles and read-only memory behavior
- Docs updated: README, long-memory architecture, technical stack, configuration/secrets, data ownership, module boundaries, plugin architecture, architecture map, project index, file inventory, task board, active handoff
- Follow-up notes: Mem0 remains behind `MemoryService`; raw event storage still reuses existing world events, conversation turns, and agent runs; distributed job execution and richer profile derivation remain future work.

## Provider reliability hardening entry

- Date: 2026-04-17
- Branch: feat/provider-reliability-hardening
- Scope: provider timeout/retry/rate-limit and health-test baseline
- Summary: Added non-secret provider reliability fields, timeout/retry/error classification behavior, per-process rate limiting, provider test-call API, diagnostic recording, and Web provider panel controls.
- Files changed: `/backend/packages/adapters/**`, `/backend/services/api/src/noveland/services/api/runtime.py`, `/backend/migrations/versions/20260417_0009_provider_reliability.py`, `/backend/tests/**`, `/web/app/api/provider-profiles/[profileId]/test-call/**`, `/web/features/dashboard/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: provider adapter reliability tests, API test-call coverage, schema metadata checks, Web client/component/mock-backend coverage for reliability fields and provider test calls
- Docs updated: README, configuration/secrets, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: provider rate limiting is process-local; distributed rate limiting, richer provider health dashboards, agent observation/persona policy, and plugin runtime execution remain separate tasks.

## Agent observation and persona baseline entry

- Date: 2026-04-17
- Branch: feat/agent-observation-persona
- Scope: agent persona policy, filtered observations, prompt context convergence
- Summary: Added agent persona and filtered observation persistence, typed contracts/services, world-admin persona/observation APIs, runtime prompt enrichment, and Web dashboard persona/observation controls.
- Files changed: `/backend/packages/agents/**`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/services/runtime/src/noveland/services/runtime/agent_loop.py`, `/backend/migrations/versions/20260417_0010_agent_observation_persona.py`, `/backend/tests/**`, `/web/features/dashboard/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: persona/observation service tests, API permission and flow tests, schema/import coverage, runtime daemon prompt-context coverage, Web client/component/E2E coverage for persona and observations
- Docs updated: README, architecture map, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: observations are filtered derived records and do not alter event log semantics; same-scene multi-agent dialogue, public reader UI, plugin runtime execution, and advanced prompt policy remain future work.

## Conversation workspace baseline entry

- Date: 2026-04-19
- Branch: feat/conversation-workspace-baseline
- Scope: multi-agent conversation substrate and world-first Web workspace
- Summary: Added world/scene-scoped conversation sessions, deterministic round-robin participants and transcript turns, conversation API routes, runtime auto-dialogue ticking, explicit agent provider profile mapping, and a multi-page Web workspace for worlds, agents, conversations, narrative, providers, and runtime.
- Files changed: `/backend/packages/conversations/**`, `/backend/migrations/versions/20260419_0011_conversation_workspace_baseline.py`, `/backend/services/api/src/noveland/services/api/conversations.py`, `/backend/services/runtime/src/noveland/services/runtime/conversation_loop.py`, `/backend/tests/**`, `/web/app/worlds/**`, `/web/app/admin/**`, `/web/features/{admin,agents,conversations,workspace,worlds}/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: conversation service/API tests; runtime daemon auto-dialogue test; schema/import coverage; Web auth/E2E updates for multi-page workspace and conversations
- Docs updated: README, architecture map, module boundaries, data ownership, project index, file inventory, task board, active handoff
- Follow-up notes: conversation v1 uses deterministic round-robin only; LLM speaker selection, policy guardrails, richer stop conditions, and narrative writer consumption remain future tasks.

## Conversation policies and stop conditions entry

- Date: 2026-04-21
- Branch: feat/conversation-policies-stop-conditions
- Scope: per-session conversation policy, stop/failure guards, and diagnostics visibility
- Summary: Added explicit per-session policy config and terminal reason fields, skip/retry/fail stop-condition handling, conversation diagnostics over the existing observability store, new stop/diagnostics API routes, and Web policy editing plus diagnostic display in the conversation detail view.
- Files changed: `/backend/packages/conversations/**`, `/backend/packages/observability/**`, `/backend/services/api/src/noveland/services/api/conversations.py`, `/backend/services/runtime/src/noveland/services/runtime/conversation_loop.py`, `/backend/migrations/versions/20260421_0012_conversation_policies_stop_conditions.py`, `/backend/tests/**`, `/web/features/{agents,conversations,worlds}/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/docs/agent/**`
- Tests added/updated: conversation service policy coverage, API stop/diagnostics coverage, runtime daemon retry handling, schema metadata assertions, Web conversation detail policy/diagnostics tests, and mock-backend E2E updates for stopped/max-turn sessions
- Docs updated: project index, file inventory, task board, active handoff, change journal
- Follow-up notes: richer distributed conversation diagnostics, memory-aware conversation context, and writer consumption of transcripts remain separate future work.

## Narrative writer and summarizer pipeline entry

- Date: 2026-04-21
- Branch: feat/narrative-writer-summarizer
- Scope: conversation-first narrative generation pipeline
- Summary: Added per-session writer config, conversation-linked narrative artifact storage, manual and auto-on-complete summary/chapter generation, runtime hook-up for completed conversations, new conversation narrative API routes, and Web controls for writer config and generation.
- Files changed: `/backend/packages/conversations/**`, `/backend/packages/narrative/**`, `/backend/services/api/src/noveland/services/api/{conversations,worlds}.py`, `/backend/services/runtime/src/noveland/services/runtime/conversation_loop.py`, `/backend/migrations/versions/20260421_0013_narrative_writer_summarizer.py`, `/backend/tests/**`, `/web/features/conversations/**`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: narrative writer service tests, conversation API narrative generation/listing tests, runtime auto-generate coverage, schema metadata assertions, world client tests for conversation narrative routes, conversation detail component coverage, and mock-backend E2E narrative generation flow
- Docs updated: README, architecture map, module boundaries, data ownership, project index, file inventory, task board, active handoff, change journal
- Follow-up notes: dedicated reader routes, richer writer prompt controls, artifact publishing workflow, and transcript-to-memory integration remain future tasks.

## Dedicated narrative reader surface entry

- Date: 2026-04-21
- Branch: feat/narrative-reader-surface
- Scope: authenticated world-member narrative reader
- Summary: Added filtered narrative artifact list/detail APIs, a read-only reader surface under `/worlds/{worldId}/reader`, reader navigation, source-conversation linking, and Web test coverage for member access and reader rendering.
- Files changed: `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/test_api_worlds.py`, `/web/app/worlds/[worldId]/reader/**`, `/web/features/worlds/**`, `/web/features/workspace/workspace-shell.tsx`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/**`
- Tests added/updated: narrative artifact API filter/detail coverage for world members; reader component tests; world client tests for filtered narrative list/detail; mock-backend E2E coverage for reader redirects and member-readable narrative pages
- Docs updated: README, project index, file inventory, task board, active handoff, change journal
- Follow-up notes: public sharing, reader search/sorting, reader timeline views, and realtime narrative updates remain future tasks.

## Realtime updates entry

- Date: 2026-04-22
- Branch: feat/realtime-updates
- Scope: hybrid SSE updates and conversation live control
- Summary: Added platform/world/conversation SSE delta routes, conversation live WebSocket control with origin checks, same-origin Next streaming proxies, and local live hydration for runtime, world overview, and conversation detail views.
- Files changed: `/backend/services/api/src/noveland/services/api/realtime.py`, `/backend/services/api/src/noveland/services/api/app.py`, `/backend/tests/test_api_realtime.py`, `/web/app/api/runtime/stream/**`, `/web/app/api/worlds/[worldId]/stream/**`, `/web/app/api/worlds/[worldId]/conversations/[conversationId]/stream/**`, `/web/features/admin/**`, `/web/features/conversations/**`, `/web/features/worlds/**`, `/web/lib/auth/**`, `/web/lib/realtime.ts`, `/web/lib/realtime/**`, `/web/lib/worlds/types.ts`, `/.env.example`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: realtime API/auth/origin tests; streaming proxy tests; runtime admin and conversation detail component coverage for live updates; full backend/web regression suite
- Docs updated: README, project index, file inventory, task board, change journal
- Follow-up notes: Stage 1 adds incremental streaming and live conversation control without replacing existing SSR/REST loaders; world members remain read-only on the live WebSocket channel.

## Agent composition presets entry

- Date: 2026-04-22
- Branch: feat/agent-composition-presets
- Scope: platform-managed presets and world composition import/export
- Summary: Added `agent_presets`, preset-aware agent materialization, world composition export/import routes, preset admin UI, preset-aware agent creation, and composition controls in the world overview.
- Files changed: `/backend/packages/agents/**`, `/backend/services/api/src/noveland/services/api/{app,worlds}.py`, `/backend/migrations/versions/20260422_0014_agent_composition_presets.py`, `/backend/tests/**`, `/web/app/admin/presets/**`, `/web/app/api/agent-presets/**`, `/web/app/api/world-compositions/**`, `/web/features/{admin,agents,worlds}/**`, `/web/lib/{api-proxy.ts,worlds/**}`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: preset API/schema tests; world composition export/import API tests; world client tests for preset/composition routes; component tests for preset admin and agent preset creation flow; Playwright mock-backend coverage for preset management and composition import/export
- Docs updated: README, project index, file inventory, task board, change journal, active handoff
- Follow-up notes: presets are materialized only at agent creation/import time, and world composition import always creates a new world instead of merging into an existing one.

## Runtime memory ops entry

- Date: 2026-05-01
- Branch: feat/runtime-memory-ops
- Scope: memory write job observability and retry operators
- Summary: Added platform-admin memory write job listing/retry APIs, runtime status memory job counts, daemon loop processed-memory-job result reporting, and Web memory backend job/failure controls.
- Files changed: `/backend/packages/memory/**`, `/backend/services/api/src/noveland/services/api/runtime.py`, `/backend/services/runtime/src/noveland/services/runtime/daemon.py`, `/backend/tests/**`, `/web/app/api/memory-backend-profiles/[profileId]/jobs/**`, `/web/app/api/memory-write-jobs/**`, `/web/features/admin/memory-backend-admin.tsx`, `/web/lib/worlds/**`, `/web/tests/e2e/**`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: memory service job list/summary/retry tests; runtime API permission/retry/status tests; runtime daemon processed-memory-job assertions; Web client and Playwright mock-backend coverage for memory job listing/retry.
- Docs updated: README, project index, file inventory, task board, active handoff, change journal
- Follow-up notes: Memory jobs still use the v1 database-backed queue; distributed workers, production queue coordination, and richer backfill remain future work.

## Long-term roadmap document entry

- Date: 2026-05-01
- Branch: main
- Scope: docs/agent roadmap planning
- Summary: Added a long-term Noveland roadmap with 50 mainline-sized phases, candidate bundles, and maintenance rules while keeping debug, checks, tests, and docs as phase acceptance criteria instead of separate roadmap stages.
- Files changed: `/docs/agent/harness/roadmap.md`, `/docs/agent/README.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: N/A; documentation-only planning update.
- Docs updated: roadmap, README, project index, file inventory, task board, active handoff, change journal
- Follow-up notes: Select the next implementation mainline from the roadmap when ready; do not treat all 50 phases as active task-board work.

## Runtime/provider/memory ops hardening entry

- Date: 2026-05-02
- Branch: main
- Scope: roadmap phases 1-5 ops hardening
- Summary: Implemented the first roadmap bundle across runtime status health, memory queue reliability metadata, memory backfill dry-run planning, and provider health summaries without adding a new queue or bypassing `MemoryService`.
- Files changed: `/backend/packages/core/src/noveland/core/settings.py`, `/backend/packages/memory/**`, `/backend/packages/adapters/**`, `/backend/services/api/src/noveland/services/api/{runtime,realtime}.py`, `/backend/tests/**`, `/web/app/api/{memory-backfill,provider-profiles}/**`, `/web/features/admin/**`, `/web/lib/worlds/**`, `/web/features/dashboard/world-management-dashboard.test.tsx`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: runtime API/realtime tests for health payloads; memory backend tests for retryable, terminal, stalled, and dry-run behavior; provider/admin Web tests; world client tests; mock backend coverage for new admin routes.
- Docs updated: README, task board, change journal, active handoff.
- Follow-up notes: Memory backfill remains planning-only; processing still uses the v1 database-backed queue. Next likely roadmap candidate is provider secret validation and recovery playbooks.

## Provider secrets and runtime recovery entry

- Date: 2026-05-02
- Branch: main
- Scope: provider secret-ref validation and runtime recovery playbook
- Summary: Added explicit provider health secret-ref metadata, preserved compatibility for `missing_secret_ref`, updated the provider admin surface, and added a local runtime recovery playbook for runtime, provider, memory queue, event audit, and snapshot checks.
- Files changed: `/backend/packages/adapters/**`, `/backend/services/api/src/noveland/services/api/runtime.py`, `/backend/tests/test_api_runtime.py`, `/web/features/admin/provider-admin.tsx`, `/web/features/admin/provider-admin.test.tsx`, `/web/lib/worlds/types.ts`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/README.md`, `/docs/agent/README.md`, `/docs/agent/git/workflow.md`, `/docs/agent/operations/runtime-recovery.md`, `/docs/agent/harness/**`
- Tests added/updated: provider health API coverage for configured, missing, and empty secret refs; provider admin rendering coverage for secret-ref status; Web client coverage remains aligned with provider health route mapping.
- Docs updated: README, runtime recovery playbook, project index, file inventory, task board, change journal, active handoff, and git workflow branch naming rule.
- Follow-up notes: Future branches must be named by feature/outcome rather than roadmap phase numbers. Next planned mainline is `Event/Replay/Clock Ops` on `feat/event-replay-clock-ops`, covering roadmap phases 8-12.

## Event/replay/clock ops entry

- Date: 2026-05-02
- Branch: feat/event-replay-clock-ops
- Scope: roadmap phases 8-12 event audit, snapshot integrity, replay workspace, clock ops visibility, and schedule preview
- Summary: Added a world-admin event audit API and Web panel; derived snapshot integrity reporting; a richer replay/snapshot workspace that separates live clock state from reconstructed replay state; clock transition audit visibility; and dry-run schedule rule preview without persisting rules or runtime work.
- Files changed: `/backend/packages/events/**`, `/backend/packages/calendar/**`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/**`, `/web/features/worlds/**`, `/web/features/dashboard/world-management-dashboard.test.tsx`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: event audit API filtering/permission tests; snapshot integrity service/API tests; clock transition API tests; schedule preview service/API tests; world overview component coverage; Web client route mapping; full mock-backend alignment.
- Docs updated: README endpoint list, project index, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Snapshot integrity is read-only and does not restore data. Schedule preview is dry-run only. Next likely mainline is `Agent/Conversation Diagnostics Ops` covering roadmap phases 13-17.

## Calendar/agent diagnostics ops entry

- Date: 2026-05-03
- Branch: feat/calendar-agent-diagnostics-ops
- Scope: roadmap phases 13-17 calendar conflicts, agent run inspection, persona policy validation, observation traceability, and conversation diagnostics
- Summary: Added read-only calendar conflict detection, world-admin agent run inspection, reusable persona policy validation, persisted observation traceability fields, and conversation diagnostics summaries.
- Files changed: `/backend/packages/{agents,calendar}/**`, `/backend/services/api/src/noveland/services/api/{worlds,conversations}.py`, `/backend/services/runtime/src/noveland/services/runtime/agent_loop.py`, `/backend/migrations/versions/20260503_0019_observation_traceability.py`, `/backend/tests/**`, `/web/features/{agents,conversations,dashboard,worlds}/**`, `/web/lib/worlds/**`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: calendar conflict service/API tests; agent run detail API and Web client tests; persona validation API/Web client coverage; observation schema/runtime/API tests; conversation diagnostics summary API/component/client coverage.
- Docs updated: README endpoint list, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Calendar conflict detection is read-only and hourly-sampled. Observation traceability requires applying migration `20260503_0019`. Next roadmap mainline is not selected yet.

## Conversation/narrative quality ops entry

- Date: 2026-05-04
- Branch: feat/conversation-narrative-quality-ops
- Scope: roadmap phases 18-22 conversation policy, memory controls, narrative prompt controls, and publishing workflow
- Summary: Added deterministic hybrid speaker policy preview, stronger conversation guardrails, operator-visible conversation memory controls, narrative writer prompt controls with dry-run preview, and a publication-backed narrative publishing workflow. Also closed stale gate docs, replaced deprecated FastAPI 422 constants, and added `next-env.d.ts` build-churn checking.
- Files changed: `/backend/packages/conversations/**`, `/backend/packages/narrative/**`, `/backend/services/api/src/noveland/services/api/{conversations,worlds}.py`, `/backend/migrations/versions/20260504_0020_narrative_publications.py`, `/backend/tests/**`, `/web/features/{conversations,worlds,dashboard}/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: conversation service/API tests for speaker policy, guardrails, memory controls, and prompt preview; narrative writer and publication API tests; schema metadata coverage for `narrative_publications`; Web component/client tests for conversation controls, prompt preview, narrative workspace publication controls, and reader visibility.
- Docs updated: README endpoint list, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Narrative publishing uses a separate `narrative_publications` table. Reader surfaces expose only published, reader-visible artifacts to non-editors; draft artifacts remain admin-visible. Apply migration `20260504_0020` before using the publishing workflow on persistent databases.

## Narrative reader/composition ops entry

- Date: 2026-05-04
- Branch: feat/narrative-reader-composition-ops
- Scope: roadmap phases 23-27 narrative reader search/timeline/realtime, world composition validation, and preset versioning
- Summary: Added publication-aware narrative reader search and timeline controls, realtime narrative artifact updates through the existing world stream, platform-admin composition import dry-run validation, richer composition export metadata, and explicit preset version provenance for materialized agents.
- Files changed: `/backend/packages/agents/**`, `/backend/services/api/src/noveland/services/api/{realtime,worlds}.py`, `/backend/migrations/versions/20260504_0021_agent_preset_versioning.py`, `/backend/tests/**`, `/web/app/api/world-compositions/validate/**`, `/web/features/{admin,agents,conversations,dashboard,worlds}/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: narrative API and Web tests for search/timeline; realtime API and reader/workspace tests for publication metadata; composition validation API/client/component/mock-backend tests; preset versioning API/schema/UI tests.
- Docs updated: README endpoint list, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Push of `main` remains blocked by missing GitHub HTTPS credentials in this environment. Apply migration `20260504_0021` before using preset version provenance on persistent databases.

## Plugin/preset evolution ops entry

- Date: 2026-05-04
- Branch: feat/plugin-preset-evolution-ops
- Scope: roadmap phases 28-32 preset update strategy, plugin binding persistence, plugin contract harness, plugin config UI schema, and plugin runtime diagnostics
- Summary: Added platform-admin preset update preview, derived plugin binding validation across existing persisted binding fields, built-in plugin contract harness coverage, schema-driven provider plugin config controls with JSON fallback, and plugin runtime diagnostics backed by a new diagnostic component.
- Files changed: `/backend/packages/observability/**`, `/backend/services/api/src/noveland/services/api/runtime.py`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/migrations/versions/20260504_0022_plugin_diagnostic_component.py`, `/backend/tests/**`, `/web/app/api/{agent-presets,plugins}/**`, `/web/features/{admin,plugins}/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: preset update preview API/UI/client tests; plugin binding API permission/validation tests; built-in plugin contract harness; provider plugin diagnostic API tests; provider admin schema/diagnostic rendering tests; mock backend routes for preset preview and plugin bindings.
- Docs updated: README endpoint list, project index, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Plugin bindings continue to use existing persisted fields rather than a new plugin layer. Persistent databases need migration `20260504_0022` before writing plugin diagnostics.

## Tool policy / scale / v2 readiness entry

- Date: 2026-05-05
- Branch: feat/tool-policy-scale-v2-readiness
- Scope: roadmap phases 48-50 external tool policy, scale readiness, and v2 expansion review
- Summary: Added policy-only external tool reporting, a derived platform-admin scale-readiness report, runtime admin visibility for both reports, and an evidence-based v2 readiness review that closes the current 50-phase roadmap without selecting a binding v2 direction.
- Files changed: `/backend/services/api/src/noveland/services/api/runtime.py`, `/backend/tests/test_api_runtime.py`, `/web/app/api/runtime/{tool-policy,scale-readiness}/**`, `/web/features/admin/runtime-admin.tsx`, `/web/lib/worlds/**`, `/README.md`, `/docs/agent/operations/{external-tool-policy,scale-readiness}.md`, `/docs/agent/harness/**`
- Tests added/updated: runtime API tests for tool policy permissions and scale readiness sections/blockers; runtime admin component and world client tests for policy/readiness rendering and routes.
- Docs updated: README, project index, file inventory, task board, change journal, active handoff, and v2 readiness review.
- Follow-up notes: External tool execution remains disabled. Scale readiness is a derived operator report, not a load test. The 50-phase roadmap is complete; next work should start from the v2 readiness review and real operator feedback.

## V2 living world roadmap entry

- Date: 2026-05-05
- Branch: docs/v2-living-world-roadmap
- Scope: long-term roadmap planning for the galgame sequel-style living world direction
- Summary: Added a new 50-phase V2 roadmap focused on world bible, canon continuity, relationships, organizations/factions, GM world engine, offscreen events, player choice consequences, branchable worldlines, route systems, information flow, and living-world beta validation.
- Files changed: `/docs/agent/harness/roadmap-v2-living-world.md`, `/docs/agent/README.md`, `/docs/agent/harness/{project-index,file-inventory,task-board,change-journal,handoffs/active-session}.md`
- Tests added/updated: N/A; documentation-only planning update.
- Docs updated: agent README read order, project index, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Do not treat all 50 V2 phases as active tasks. Select one V2 mainline bundle in `task-board.md` only when implementation starts.

## Living world character foundation entry

- Date: 2026-05-05
- Branch: feat/living-world-character-foundation
- Scope: V2 living-world roadmap phases 1-5 story world bible, canon continuity, character roster metadata, character profile sheets, and relationship graph v1.
- Summary: Added a world-scoped bible with continuity configuration, continuity metadata on event/narrative API responses, structured galgame character roster/profile fields on agents, and a world-scoped directed relationship edge table/API. Web world overview now exposes world bible editing, agent creation/builder flows expose structured character fields, and agent detail shows relationship graph create/update controls.
- Files changed: `/backend/migrations/versions/20260505_0023_living_world_character_foundation.py`, `/backend/packages/{agents,worlds}/src/noveland/*/models.py`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/{test_api_worlds,test_schema_metadata,test_alembic_config}.py`, `/backend/migrations/README.md`, `/web/features/{agents,worlds,workspace}/**`, `/web/lib/worlds/**`, `/docs/agent/harness/**`
- Tests added/updated: world bible API/access tests; continuity metadata API tests; agent metadata compatibility tests; relationship graph same-world/self-edge/update tests; schema metadata/alembic head tests; Web client route tests; agent list/builder/world overview component tests.
- Docs updated: task board, change journal, active handoff.
- Follow-up notes: Apply migration `20260505_0023` before using V2 character foundation on persistent databases. Relationship memory integration, organizations/factions, location graph, GM engine, worldlines, and player choices remain future V2 phases.

## Living world autonomous systems entry

- Date: 2026-05-05
- Branch: feat/living-world-autonomous-systems
- Scope: V2 living-world roadmap phases 6-15 relationship memory integration, organizations, memberships, faction progress, location graph, character presence, daily life scheduler, offscreen queue, event importance, and deterministic GM world engine v1.
- Summary: Added relationship-change memory write integration through `MemoryService`; organization, membership, faction track, location edge, presence, daily-life candidate, and offscreen queue persistence/API surfaces; world-event importance metadata and filters; deterministic GM runtime resolution for due offscreen events; and dense Web/admin panels plus Playwright mock routes for the new living-world autonomy surfaces.
- Files changed: `/backend/migrations/versions/20260505_0024_living_world_autonomous_systems.py`, `/backend/packages/{events,memory,worlds}/src/noveland/**`, `/backend/services/{api,runtime}/src/noveland/services/**`, `/backend/tests/{test_api_worlds,test_memory_backend,test_runtime_daemon,test_schema_metadata,test_alembic_config}.py`, `/backend/migrations/README.md`, `/web/features/{agents,dashboard,worlds}/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/docs/agent/harness/**`
- Tests added/updated: relationship memory write-job coverage; organization/membership/faction/presence/daily/offscreen/world-event importance API tests; deterministic GM runtime daemon tests; schema metadata/alembic coverage for `20260505_0024`; Web client/component tests; e2e mock backend coverage for new world APIs.
- Docs updated: migration README, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Apply migration `20260505_0024` before using autonomous living-world data on persistent databases. GM v1 is deterministic and does not call providers, external tools, or direct memory backend SDKs. V2 phases 16-20 remain the next candidate bundle.

## Living world GM choices worldlines entry

- Date: 2026-05-06
- Branch: feat/living-world-gm-choices-worldlines
- Scope: V2 living-world roadmap phases 16-25 GM agenda, event proposals, deterministic resolution rules, player actor/choices/consequences, branchable worldlines, snapshot fork, worldline memory isolation, and timeline comparison.
- Summary: Added primary/forked worldlines with compatibility defaults; scoped events, snapshots, replay, memory, relationships, faction tracks, presence, daily candidates, and offscreen queue by worldline; added GM agendas, event proposals, resolution-rule dry-runs, player actor profiles, choice records, consequence preview/apply, worldline fork copying, and timeline comparison; exposed dense Web/admin controls and Playwright mock routes for the new surfaces.
- Files changed: `/backend/migrations/versions/20260505_0025_living_world_gm_choices_worldlines.py`, `/backend/packages/{events,memory,worlds}/src/noveland/**`, `/backend/services/{api,runtime}/src/noveland/services/**`, `/backend/tests/**`, `/web/features/worlds/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/README.md`, `/docs/agent/harness/**`
- Tests added/updated: worldline API/fork/compare tests; GM agenda/proposal/review/rule dry-run tests; player actor/choice/consequence tests; replay/snapshot/event/memory worldline-scope tests; schema metadata/Alembic coverage for `20260505_0025`; Web client/component tests; full Playwright mock alignment for new worldline and GM routes.
- Docs updated: README endpoint list, migration README, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Apply migration `20260505_0025` before using worldline-scoped living-world data on persistent databases. GM work remains deterministic and does not call providers, external tools, subprocesses, or direct memory backend SDKs. V2 phases 26-35 are the next likely mainline bundle.

## Living world plot route rumor flow entry

- Date: 2026-05-06
- Branch: feat/living-world-plot-route-rumor-flow
- Scope: V2 living-world roadmap phases 26-35 promise/foreshadowing tracking, plot threads, route affinity, event flags, scene beats, daily episodes, group interactions, relationship suggestions, organization conflict, and rumor/information flow v1.
- Summary: Added worldline-scoped plot/route/rumor persistence and services; deterministic trigger dry-runs, scene beat and daily episode draft generation, relationship suggestion generation, organization conflict resolution, and rumor delivery; world-admin API surfaces; and dense Web/admin controls plus Playwright mock alignment.
- Files changed: `/backend/migrations/versions/20260506_0026_living_world_plot_route_rumor_flow.py`, `/backend/packages/{agents,worlds}/src/noveland/**`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/{test_api_worlds,test_schema_metadata,test_alembic_config}.py`, `/backend/migrations/README.md`, `/web/features/worlds/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/docs/agent/harness/**`
- Tests added/updated: world-admin API coverage for plot/route/rumor flows, worldline scoping, trigger dry-run, deterministic drafts, relationship suggestions, organization conflict event emission, rumor delivery, schema metadata, Alembic head, Web client routes, world overview rendering, and e2e mock backend route alignment.
- Docs updated: migration README, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Apply migration `20260506_0026` before using plot/route/rumor data on persistent databases. Rumor flow is v1 propagation/visibility only; character knowledge state, secrets, emotional state, relationship decay/repair, player journal, notifications, intervention controls, and GM style/continuity review remain later V2 phases.

## Living world knowledge player guardrails entry

- Date: 2026-05-07
- Branch: feat/living-world-knowledge-player-guardrails
- Scope: V2 living-world roadmap phases 36-45 character knowledge state, secrets/revelations, emotional state, relationship decay/repair, world-state dashboard v2, player-facing journal, in-world notifications, intervention controls, GM style guardrails, and narrative continuity review.
- Summary: Added worldline-scoped knowledge facts, secrets/reveals, emotional states, relationship repair records, player journal entries, notifications, interventions, GM style diagnostics, and narrative continuity reviews. Closed natural V2 phases 1-35 acceptance gaps by logging `apply=false` choices as events, propagating runtime memory worldline scope, rejecting unsupported historical worldline forks, expanding deterministic dry-run context, turning rumor delivery into knowledge state, generating daily episode drafts from resolved low-risk offscreen events, and passing group interaction context into conversation writer config.
- Files changed: `/backend/migrations/versions/20260507_0027_living_world_knowledge_player_guardrails.py`, `/backend/packages/{memory,worlds}/src/noveland/**`, `/backend/services/{api,runtime}/src/noveland/services/**`, `/backend/tests/{test_api_worlds,test_schema_metadata,test_alembic_config}.py`, `/backend/migrations/README.md`, `/web/features/worlds/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/docs/agent/harness/**`
- Tests added/updated: backend API/schema/Alembic coverage for knowledge, secrets, emotional state, relationship repair, journal, notification, intervention, style review, continuity review, dashboard, daily episode generation, memory write jobs, and fork rejection; Web client route tests; world overview rendering tests; Playwright mock backend alignment.
- Docs updated: migration README, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Apply migration `20260507_0027` before using knowledge/player/guardrail state on persistent databases. Review work is deterministic diagnostics only; it does not hard-block publication by default and does not call providers, external tools, subprocesses, or sandbox execution. V2 phases 46-50 remain as the next candidate bundle.

## Living world beta release readiness entry

- Date: 2026-05-07
- Branch: feat/living-world-beta-release-readiness
- Scope: V2 living-world roadmap phases 46-50 route/ending planning, long-run simulation evaluation, authoring toolchain v2, living-world release profile, and galgame living-world beta validation.
- Summary: Added worldline-scoped route milestones and ending candidates, deterministic ending dry-runs, long-run evaluation runs with recommendations/blockers, sequel-world authoring templates with preview/apply import jobs, release profile records, and beta checklist runs/items for sample-world readiness evidence. Web world overview now exposes dense beta-readiness panels, and the Playwright mock backend covers all new routes.
- Files changed: `/backend/migrations/versions/20260507_0028_living_world_beta_release_readiness.py`, `/backend/packages/worlds/src/noveland/worlds/{models,beta}.py`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/{test_api_worlds,test_schema_metadata,test_alembic_config}.py`, `/backend/migrations/README.md`, `/web/features/worlds/**`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/docs/agent/operations/living-world-release-profile.md`, `/docs/agent/harness/**`
- Tests added/updated: backend API/schema/Alembic coverage for route milestones, endings, long-run evals, authoring templates/imports, release profiles, and beta checklist evidence; Web client route mapping and world overview rendering tests; Playwright mock backend alignment.
- Docs updated: migration README, release profile operator note, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Apply migration `20260507_0028` before using beta readiness state on persistent databases. Long-run eval and beta validation are deterministic local evidence capture, not provider generation, external tool execution, or a public production launch.

## V2 runtime worldline memory isolation remediation entry

- Date: 2026-05-08
- Branch: fix/v2-runtime-worldline-memory-isolation
- Scope: V2 acceptance remediation bundle 1 for runtime run worldline scope, conversation session propagation, memory profile snapshots, memory backfill, memory forget/delete, fake/local memory backend filtering, and player-choice audit semantics.
- Summary: Added first-class `worldline_id` to runtime runs, conversation sessions, and agent profile snapshots; resolved omitted worldlines to each world's primary worldline for compatibility; propagated conversation worldline scope into runtime agent turns; scoped memory context, profile snapshots, delete/forget scrubbing, fake backend storage, retrieval logs, write jobs, and backfill candidates by worldline; exposed worldline metadata on runtime and memory ops API responses; and preserved legacy NULL rows as primary-worldline data.
- Files changed: `/backend/migrations/versions/20260507_0029_runtime_worldline_memory_isolation.py`, `/backend/packages/{agents,conversations,memory}/src/noveland/**`, `/backend/services/{api,runtime}/src/noveland/services/**`, `/backend/tests/{test_alembic_config,test_api_conversations,test_api_worlds,test_conversation_services,test_memory_backend,test_runtime_daemon,test_schema_metadata}.py`, `/backend/migrations/README.md`, `/web/features/admin/memory-backend-admin.test.tsx`, `/web/lib/worlds/types.ts`, `/docs/agent/harness/**`
- Tests added/updated: backend coverage for fork-scoped runtime run events and memory jobs, cross-world worldline rejection, conversation session/event worldline propagation, API run filtering by worldline, fake/local memory worldline isolation, memory build/delete scope isolation, backfill worldline preservation, legacy primary NULL compatibility, schema metadata, and Alembic head. Web memory-admin fixture updated for worldline-aware write jobs.
- Docs updated: migration README, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Apply migration `20260507_0029` before relying on runtime run, conversation session, or profile snapshot worldline scope in persistent databases. Remaining remediation bundles should proceed in order: prompt leak/publish guardrails, runtime GM/narrative execution depth, then beta acceptance gate hardening.

## V2 prompt leak publish guardrails remediation entry

- Date: 2026-05-08
- Branch: feat/v2-prompt-leak-publish-guardrails
- Scope: V2 acceptance remediation bundle 2 for leak-safe prompt context selection, speaker-scoped conversation prompts, narrative prompt/review boundaries, and publish-time blocker handling.
- Summary: Added a shared living-world context selector that admits only public facts, agent-visible knowledge, holder/revealed secrets, bounded emotional state, and relationship summaries into prompts; integrated it into agent runtime, conversation speaker prompts, and narrative writer generation/preview; expanded continuity review to detect hidden secret leaks without persisting secret text in diagnostics; and added a publish gate that blocks failed/leaky narrative artifacts while recording review metadata on successful publication.
- Files changed: `/backend/packages/worlds/src/noveland/worlds/living_context.py`, `/backend/packages/{conversations,narrative,worlds}/src/noveland/**`, `/backend/services/{api,runtime}/src/noveland/services/**`, `/backend/tests/{test_api_worlds,test_conversation_services,test_narrative_writer,test_runtime_daemon}.py`, `/web/features/{workspace,worlds}/**`, `/web/lib/worlds/**`, `/docs/agent/harness/**`
- Tests added/updated: backend coverage for runtime holder/non-holder secret filtering, conversation speaker-specific context filtering, narrative writer leak-safe prompts, publish blocker 422 behavior, and warning-override publication gate metadata; Web client/workspace coverage for structured blocker summaries and publication gate display.
- Docs updated: task board, change journal, and active handoff.
- Follow-up notes: Bundle 3 should build on this selector for world bible/open-hook context packs, group interaction execution, expanded trigger evaluation, and deterministic GM proposal planning.

## V2 runtime GM narrative execution remediation entry

- Date: 2026-05-08
- Branch: feat/v2-runtime-gm-narrative-execution
- Scope: V2 acceptance remediation bundle 3 for living-world runtime/narrative consumption depth, group interaction execution, expanded condition evaluation, and deterministic GM macro planning.
- Summary: Added a shared world condition evaluator for GM rules and event triggers; added living-world context packs that carry bounded world bible constraints, forbidden changes, open hooks, plot threads, route states, and continuity warnings into runtime/narrative prompts and metadata; added deterministic GM macro planning/execution and low-risk GM proposal draft conversion; and added group interaction execution into conversation sessions with participant roles, organization refs, scene constraints, and writer group context metadata.
- Files changed: `/backend/packages/worlds/src/noveland/worlds/{conditions,living_context,gm,plot,autonomous}.py`, `/backend/packages/narrative/src/noveland/narrative/**`, `/backend/services/{api,runtime}/src/noveland/services/**`, `/backend/tests/{test_api_worlds,test_api_conversations,test_narrative_writer,test_runtime_daemon}.py`, `/web/lib/worlds/**`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/docs/agent/harness/**`
- Tests added/updated: backend coverage for context-pack narrative metadata, group interaction execution, centralized trigger/rule condition evaluation, GM macro planning/execution, and low-risk daily draft conversion; Web client route mapping tests; Playwright mock backend route alignment for macro planning, draft conversion, and group execution.
- Docs updated: task board, change journal, file inventory, and active handoff.
- Follow-up notes: Bundle 4 should harden beta acceptance gates using the now-reliable worldline scope, leak-safe prompt/review boundary, and richer GM/narrative execution evidence. GM macro planning remains deterministic and does not call providers, external tools, subprocesses, or sandbox execution.

## V2 beta acceptance gating hardening remediation entry

- Date: 2026-05-08
- Branch: feat/v2-beta-acceptance-gating-hardening
- Scope: V2 acceptance remediation bundle 4 for beta readiness gate hardening, evidence metrics, checklist evidence refs, route/ending validation, and authoring import audit semantics.
- Summary: Hardened release profiles so `ready` requires latest passing checklist, latest completed long-run eval, resolvable structured evidence refs for snapshot/worldline/publication/continuity review/checklist/eval, and explicit warning decisions; kept `released` blocked behind a future launch gate. Expanded long-run eval metrics with distribution, traceability, snapshot/event refs, proposal/review counts, and warning counts. Added checklist item/run evidence refs, ending requirement validation, forbidden flag dry-runs, authoring target worldline/duplicate policy support, preview diff/audit metadata, applied refs, and authoring audit world events. Updated Web beta panels, route-mapping tests, overview tests, and Playwright mock backend evidence shapes.
- Files changed: `/backend/packages/worlds/src/noveland/worlds/beta.py`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/test_api_worlds.py`, `/web/features/worlds/world-overview.tsx`, `/web/features/worlds/world-overview.test.tsx`, `/web/lib/worlds/types.ts`, `/web/lib/worlds/client.test.ts`, `/web/tests/e2e/start-with-mock-auth.mjs`, `/docs/agent/harness/{task-board.md,change-journal.md,handoffs/active-session.md}`
- Tests added/updated: backend API coverage for blocked/allowed release profile gates, long-run eval evidence metrics, structured checklist refs, invalid/cross-worldline ending requirements, and authoring preview/apply audit refs; Web client body mapping tests; Web overview rendering tests for gate/evidence/audit summaries; Playwright mock backend alignment.
- Docs updated: task board, change journal, and active handoff. No new structural files were introduced, so `file-inventory.md` did not need a path update.
- Follow-up notes: This closes the planned four-bundle V2 acceptance remediation sequence locally. Future hardening should be driven by fresh acceptance reports, beta evidence, operator feedback, and production-readiness decisions rather than roadmap phase numbers.

## V2 acceptance contract hardening entry

- Date: 2026-05-09
- Branch: fix/v2-acceptance-contract-hardening
- Scope: Fresh post-remediation acceptance hardening for Web mock/backend contract parity, reader query coverage, beta/release form payload tests, release gate blocker enforcement, and stale handoff cleanup.
- Summary: Refreshed the active handoff after the completed remediation sequence; aligned the Playwright mock backend with real API behavior for narrative publication blockers and release profile gate blockers; expanded narrative artifact listing filters for search, source kind, publication status, published ordering, and limit; added e2e coverage for blocked publication visibility, reader filtering/ordering, and release gate enforcement; and added component coverage for V2 beta, release, route, ending, and worldline form payloads. Confirmed that omitted/null `worldline_id` is an intentional primary-worldline contract, so no selector code change was needed.
- Files changed: `/docs/agent/harness/{task-board.md,change-journal.md,handoffs/active-session.md}`, `/web/features/worlds/world-overview.test.tsx`, `/web/tests/e2e/{auth.spec.ts,start-with-mock-auth.mjs}`
- Tests added/updated: Web world overview form contract tests; Playwright coverage for publication blockers, reader query filters, published ordering, and release gate blockers; mock syntax and diff whitespace checks.
- Docs updated: task board, change journal, and active handoff.
- Follow-up notes: The auth e2e spec now runs serially because the mock backend uses shared mutable in-memory state. Future e2e additions should either keep shared-state tests serial or isolate mock state per test.

## V2 post-remediation source-of-record refresh entry

- Date: 2026-05-10
- Branch: docs/v2-post-remediation-source-of-record
- Scope: Documentation refresh after the follow-up release evidence, beta GM loop, Web mock parity, Mem0 isolation, and release-evidence e2e stabilization commits landed on local `main`.
- Summary: Updated the active handoff and task board so they no longer describe closed post-remediation risks as upcoming work. Added a debug-journal closure report that maps the 2026-05-09 remaining-risk bullets to the follow-up commits that closed them.
- Files changed: `/docs/agent/harness/{task-board.md,debug-journal.md,change-journal.md,handoffs/active-session.md}`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: task board, debug journal, change journal, and active handoff.
- Follow-up notes: Next preparation hardening should focus on Web runtime/SSE mock parity and Playwright mock state isolation before starting the next feature bundle.

## Current system architecture review entry

- Date: 2026-05-10
- Branch: main
- Scope: Architecture review documentation for planning the next framework update with an external architecture reviewer.
- Summary: Added `docs/agent/harness/current-system-architecture-review.md`, a current-state overview covering product direction, source-of-record files, stack, backend/Web architecture, core data model families, V2 living-world capabilities, major runtime flows, Web surfaces, tests, operations, known constraints, and recommended next framework work.
- Files changed: `/docs/agent/harness/current-system-architecture-review.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Use the architecture review together with the V2 roadmap and debug journal when deciding whether the next implementation should prioritize service decomposition, command/event/evidence framework consolidation, provider-backed generation boundaries, or Web surface modularization.

## Media Kernel Phase 1 plan entry

- Date: 2026-05-10
- Branch: main
- Scope: Final feature implementation plan for Media Kernel Phase 1.
- Summary: Added the version-prefixed feature update plan for backend-only Media Kernel Foundation work. The plan fixes the Phase 1 boundaries around narrative artifact context rejection, asset status semantics, generated storage URIs, no provider profile FK on media jobs, no media-created world events, and no public download/file-serving API.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.1-media-kernel-phase-1-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/media-kernel-foundation` after this docs-only work is committed on `main`.

## Media Kernel Foundation implementation entry

- Date: 2026-05-10
- Branch: feat/media-kernel-foundation
- Scope: Backend-only Media Kernel Phase 1 foundation.
- Summary: Added `noveland-media`, worldline-scoped media asset/job/context/input tables, binary local media storage with opaque `media://` URIs, media services, an independent `/worlds/{world_id}/media/*` API router, and backend coverage for schema, storage, service, API, ACL, and worldline isolation. Phase 1 records media jobs only; it does not execute providers, add upload/download routes, add Web UI, or create world events from media operations.
- Files changed: `/backend/packages/media/**`, `/backend/services/api/src/noveland/services/api/{app,media}.py`, `/backend/migrations/versions/20260510_0030_media_kernel_foundation.py`, `/backend/tests/{test_api_media.py,test_media_service.py,test_media_storage.py,test_schema_metadata.py,test_alembic_config.py,test_workspace_imports.py}`, `/backend/{pyproject.toml,uv.lock}`, `/backend/services/api/pyproject.toml`, `/backend/packages/core/src/noveland/core/database.py`, `/backend/migrations/README.md`, `/docs/agent/harness/**`
- Tests added/updated: Media storage tests, MediaService tests, Media API tests, schema metadata registration, Alembic head, workspace import coverage, plus backend lint/type/test gates.
- Docs updated: migration README, project index, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Narrative artifact media contexts remain schema-reserved but rejected by service/API until `narrative_artifacts` gains first-class `worldline_id`. Later media phases should add asset catalog/search, invocation ledger, performance annotation, provider integrations, binary upload/download policy, and Web media surfaces.

## Media Asset Catalog Phase 2 plan entry

- Date: 2026-05-10
- Branch: main
- Scope: Final feature implementation plan for Media Asset Catalog Phase 2.
- Summary: Added the version-prefixed Phase 2 plan for media asset tags, collections, collection items, asset search, and visibility-safe references/lineage enrichment. The plan fixes tag query parsing, `contains_text` bounds, asset/tag/collection visibility rules, member-safe counts, route ordering, and explicit non-goals around providers, upload/download, Web UI, invocation ledger, performance annotations, and pgvector search.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.2-media-asset-catalog-phase-2-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/media-asset-catalog` after this docs-only work is committed on `main`.

## Media Asset Catalog Phase 2 implementation entry

- Date: 2026-05-10
- Branch: feat/media-asset-catalog
- Scope: Backend-only Media Asset Catalog / Tag Index Phase 2.
- Summary: Added worldline-scoped media asset tags, collections, collection items, asset search, and visibility-safe reference/lineage enrichment. Search supports bounded title/description text filtering, repeatable AND tag filters with colon-safe value parsing, context filters, collection filters, and member-safe visibility rules across assets, tags, and collections. Phase 2 does not add providers, upload/download APIs, Web UI, invocation ledger, performance annotations, or pgvector search.
- Files changed: `/backend/packages/media/src/noveland/media/{catalog,contracts,models,__init__}.py`, `/backend/services/api/src/noveland/services/api/media.py`, `/backend/migrations/versions/20260510_0031_media_asset_catalog.py`, `/backend/tests/{test_media_catalog_service.py,test_api_media_catalog.py,test_schema_metadata.py,test_alembic_config.py,test_workspace_imports.py,test_api_media.py,test_media_service.py}`, `/backend/migrations/README.md`, `/docs/agent/harness/**`
- Tests added/updated: Media catalog service tests, Media catalog API tests, schema metadata registration, Alembic head coverage, workspace import coverage, and existing media API/service table setup coverage.
- Docs updated: migration README, project index, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Later media phases should add provider integrations, upload/download policy, invocation ledger, performance annotations, asset embeddings/similarity search, and Web media surfaces in separate feature-named branches.

## Model Invocation Ledger Phase 3 plan entry

- Date: 2026-05-11
- Branch: main
- Scope: Final feature implementation plan for Model Invocation Ledger Phase 3.
- Summary: Added the version-prefixed Phase 3 plan for a new `noveland-invocations` package, worldline-scoped `model_invocations`, prompt templates, prompt snapshots, invocation tags, runtime-run join table, redaction/retention/visibility policy, independent `/worlds/{world_id}/model-invocations` API router, and new-runtime integration. The plan explicitly excludes provider adapter refactors, Web UI, external tracing exporters, pgvector search, legacy backfill, `conversation_turns` schema changes, and raw prompt/output writes to world events.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.3-model-invocation-ledger-phase-3-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/model-invocation-ledger` after this docs-only work is committed on `main`.

## Model Invocation Ledger Phase 3 implementation entry

- Date: 2026-05-11
- Branch: feat/model-invocation-ledger
- Scope: Backend-only Model Invocation Ledger Phase 3.
- Summary: Added `noveland-invocations`, worldline-scoped invocation ledger tables, prompt templates, prompt snapshots, runtime-run join table, invocation tags, bounded search, redaction/retention/visibility controls, an independent `/worlds/{world_id}/model-invocations` API router, and new `AgentRuntimeRun` provider-call recording. Existing runtime runs remain source records for agent execution; canonical raw prompt/output for new calls is stored in invocation/snapshot records, not in `world_events.payload`.
- Files changed: `/backend/packages/invocations/**`, `/backend/services/api/src/noveland/services/api/{app,invocations}.py`, `/backend/services/runtime/src/noveland/services/runtime/agent_loop.py`, `/backend/migrations/versions/20260511_0032_model_invocation_ledger.py`, `/backend/tests/{test_invocation_ledger_service.py,test_api_invocations.py,test_runtime_daemon.py,test_api_conversations.py,test_api_worlds.py,test_schema_metadata.py,test_alembic_config.py,test_workspace_imports.py}`, `/backend/{pyproject.toml,uv.lock}`, `/backend/services/{api,runtime}/pyproject.toml`, `/backend/packages/core/src/noveland/core/database.py`, `/backend/migrations/README.md`, `/docs/agent/harness/**`
- Tests added/updated: Invocation ledger service tests, invocation API tests, runtime ledger integration assertions, schema metadata registration, Alembic head coverage, workspace import coverage, and legacy API fixture table coverage for runtime/conversation paths.
- Docs updated: migration README, project index, file inventory, task board, change journal, and active handoff.
- Follow-up notes: Provider adapter refactors, external tracing exporters, Web invocation browser, pgvector/similarity search, retention purge jobs, historical `AgentRuntimeRun` backfill, and provider-integration-specific invocation enrichment remain deferred.

## Media Kernel Phase 4 plan entry

- Date: 2026-05-11
- Branch: main
- Scope: Final feature implementation plan for Media Kernel Phase 4 additive extension.
- Summary: Added the version-prefixed Phase 4 plan to extend the existing Media Phase 1/2 foundation with media objects, generic media references, upload/download routes, richer media job updates, and Phase 3 invocation links without replacing existing media tables or APIs.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.4-media-kernel-phase-4-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/media-kernel` after this docs-only work is committed on `main`.

## Media Kernel Phase 4 implementation entry

- Date: 2026-05-11
- Branch: feat/media-kernel
- Scope: Backend-only Media Kernel Phase 4 additive extension.
- Summary: Extended the existing `noveland-media` foundation with multi-object asset records, generic media references, upload/download support, richer media job list/update/cancel flows, turn media attachment routes backed by `media_references`, and media-side Phase 3 invocation links. The implementation preserves existing media tables and route behavior, keeps storage URIs and bytes out of world events, and does not add provider adapters, Web UI, public reader routes, or background media job execution.
- Files changed: `/backend/packages/media/src/noveland/media/{contracts,models,service,storage,__init__}.py`, `/backend/services/api/src/noveland/services/api/{app,media}.py`, `/backend/migrations/versions/20260512_0033_media_kernel.py`, `/backend/tests/{test_media_service.py,test_api_media.py,test_schema_metadata.py,test_alembic_config.py}`, `/backend/{pyproject.toml,uv.lock}`, `/backend/services/api/pyproject.toml`, `/backend/migrations/README.md`, `/docs/agent/harness/**`
- Tests added/updated: Media service coverage for upload/object variants/references/turn media/job updates/source invocation and memory job validation; Media API coverage for upload/download ACL, generic refs, turn media, job patch/cancel, malformed upload metadata, and cross-worldline rejection; schema metadata and Alembic head coverage.
- Docs updated: migration README, file inventory, change journal, and active handoff.
- Follow-up notes: Provider-specific image/audio/video adapters, public reader media serving, S3/GCS storage, media embeddings/search, Web media management UI, and background media job execution remain deferred.

## Provider Execution Kernel Phase 5 plan entry

- Date: 2026-05-11
- Branch: main
- Scope: Final feature implementation plan for Provider Execution Kernel Phase 5.
- Summary: Added the version-prefixed Phase 5 plan for a new `noveland-providers` package, provider integration/capability/health tables, explicit `adapter_kind` execution dispatch, fake provider execution, model invocation ledger writes, media job/asset linkage, and an independent `/worlds/{world_id}/providers` API router.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.5-provider-execution-kernel-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/provider-execution-kernel` after this docs-only work is committed on `main`.

## Provider Execution Kernel Phase 5 implementation entry

- Date: 2026-05-11
- Branch: feat/provider-execution-kernel
- Scope: Backend-only Provider Execution Kernel Phase 5.
- Summary: Added `noveland-providers`, provider integration/capability/health tables, explicit `adapter_kind` routing, world-over-global provider resolution, fake text/image/STT/TTS execution, Phase 3 invocation and prompt snapshot writes, Phase 4 media job/asset/object writes for fake image/audio, and an independent `/worlds/{world_id}/providers` API router. The implementation leaves legacy `provider_profiles` unchanged and does not add real external provider adapters.
- Files changed: `/backend/packages/providers/**`, `/backend/services/api/src/noveland/services/api/{app,providers}.py`, `/backend/migrations/versions/20260512_0034_provider_execution_kernel.py`, `/backend/tests/{test_provider_registry_service.py,test_provider_execution_service.py,test_api_providers.py,test_schema_metadata.py,test_alembic_config.py,test_workspace_imports.py}`, `/backend/{pyproject.toml,uv.lock}`, `/backend/services/api/pyproject.toml`, `/backend/packages/core/src/noveland/core/database.py`, `/backend/migrations/README.md`, `/docs/agent/harness/**`
- Tests added/updated: Provider registry service tests, provider execution service tests, provider API tests, schema metadata registration, Alembic head coverage, workspace import coverage, plus backend lint/type/targeted gates.
- Docs updated: migration README, project index, file inventory, change journal, and active handoff.
- Follow-up notes: Real OpenAI image/speech, OpenAI-compatible image, ComfyUI, MiMo, OmniVoice, GPT-SoVITS, streaming, retry/load balancing, Web provider UI, and provider-profile refactors remain deferred to later phases.

## Image Provider & Visual Asset Pipeline Phase 6 plan entry

- Date: 2026-05-11
- Branch: main
- Scope: Final feature implementation plan for Image Provider & Visual Asset Pipeline Phase 6.
- Summary: Added the version-prefixed Phase 6 plan for image generation/edit/compose routes, media image services, deterministic composition, OpenAI/OpenAI-compatible image adapters, ComfyUI workflow adapter mapping, provider execution integration, and visual asset writeback through Phase 3 and Phase 4 foundations.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.6-image-provider-visual-pipeline-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/image-provider-visual-pipeline` after this docs-only work is committed on `main`.

## Image Provider & Visual Asset Pipeline Phase 6 implementation entry

- Date: 2026-05-11
- Branch: feat/image-provider-visual-pipeline
- Scope: Backend-only Image Provider & Visual Asset Pipeline Phase 6.
- Summary: Added image generation/edit/compose contracts and services, an independent `/worlds/{world_id}/images` router, Pillow-backed deterministic PNG composition, OpenAI/OpenAI-compatible image adapters, a ComfyUI remote workflow adapter with dry-run support, and provider execution dispatch for image adapters. Provider-backed image calls reuse media jobs, write model invocations and prompt snapshots, and store outputs through media assets/objects without writing prompts, bytes, paths, base64, or storage URIs to world events.
- Files changed: `/backend/packages/media/src/noveland/media/{image_contracts,image_service,composer,__init__}.py`, `/backend/packages/providers/src/noveland/providers/{service,fake}.py`, `/backend/packages/providers/src/noveland/providers/adapters/**`, `/backend/services/api/src/noveland/services/api/{app,images}.py`, `/backend/tests/{test_image_service.py,test_api_images.py,test_openai_image_adapter.py,test_comfyui_adapter.py,test_image_composer.py,test_workspace_imports.py}`, `/backend/{pyproject.toml,uv.lock}`, `/backend/packages/{media,providers}/pyproject.toml`, `/docs/agent/harness/**`
- Tests added/updated: Image service/API tests, OpenAI image adapter mocked HTTP tests, ComfyUI adapter mocked/dry-run tests, deterministic composer tests, and workspace import coverage.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: No schema migration was needed for Phase 6. Public reader delivery, Web image management UI, complex image editing, rembg/SAM2/IP-Adapter/ControlNet integrations, predictive background scheduling, and ComfyUI installation/model management remain deferred.

## Speech Provider & Voice Profile Pipeline Phase 7 plan entry

- Date: 2026-05-11
- Branch: main
- Scope: Final feature implementation plan for Speech Provider & Voice Profile Pipeline Phase 7.
- Summary: Added the version-prefixed Phase 7 plan for voice profiles, agent voice bindings, speech transcripts, style mappings, TTS/STT service orchestration, OpenAI speech adapters, MiMo TTS/ASR configurable HTTP contracts, OmniVoice/GPT-SoVITS configurable HTTP contracts, media writeback, invocation ledger integration, and conversation-turn media attachment via references.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.7-speech-provider-voice-profile-pipeline-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/speech-provider-voice-profile-pipeline` after this docs-only work is committed on `main`.

## Speech Provider & Voice Profile Pipeline Phase 7 implementation entry

- Date: 2026-05-12
- Branch: feat/speech-provider-voice-profile-pipeline
- Scope: Backend-only Speech Provider & Voice Profile Pipeline Phase 7.
- Summary: Added `noveland-speech`, voice profile and agent voice binding services, speech transcripts, style mappings, an independent `/worlds/{world_id}/speech` API router, OpenAI speech adapter mapping, configurable MiMo TTS/ASR and OmniVoice/GPT-SoVITS HTTP contract adapters, and provider execution dispatch for speech adapters. TTS/STT flows write model invocations and prompt snapshots, media jobs/assets/objects/references, and transcripts without mutating conversation turn text, auto-enqueueing memory writes, or writing audio bytes, paths, storage URIs, raw prompts, or raw outputs to world events.
- Files changed: `/backend/packages/speech/**`, `/backend/packages/providers/src/noveland/providers/{service,adapters/**}`, `/backend/services/api/src/noveland/services/api/{app,speech}.py`, `/backend/migrations/versions/20260512_0036_speech_voice_pipeline.py`, `/backend/tests/{test_speech_service.py,test_api_speech.py,test_openai_speech_adapter.py,test_mimo_speech_adapters.py,test_voice_profiles.py,test_schema_metadata.py,test_alembic_config.py,test_workspace_imports.py}`, `/backend/{pyproject.toml,uv.lock}`, `/backend/services/api/pyproject.toml`, `/backend/packages/core/src/noveland/core/database.py`, `/backend/migrations/README.md`, `/docs/agent/harness/**`
- Tests added/updated: Voice profile tests, speech service tests, speech API tests, OpenAI speech adapter mocked HTTP tests, MiMo/OmniVoice/GPT-SoVITS adapter contract tests, schema metadata registration, Alembic head coverage, workspace import coverage, plus backend lint/type/full pytest gates.
- Docs updated: migration README, project index, file inventory, change journal, and active handoff.
- Follow-up notes: Streaming speech, real-time calls, local MiMo/OmniVoice/GPT-SoVITS deployment, voice clone training, public reader audio delivery, Web recording/player UI, speaker identity/authentication, and memory auto-write remain deferred.

## Real Provider Configuration & Smoke Validation Phase 8 plan entry

- Date: 2026-05-12
- Branch: main
- Scope: Final feature implementation plan for Real Provider Configuration & Smoke Validation Phase 8.
- Summary: Added the version-prefixed Phase 8 plan for treating provider `auth_ref` as an opaque secret reference, resolving provider secrets from environment/settings at execution time, rejecting secret-like provider config fields, sanitizing provider API/health/ledger payloads, and adding safe provider smoke-test and health-check listing APIs without adding a vault, Web UI, provider marketplace, streaming, fallback routing, or new media product features.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.8-real-provider-smoke-validation-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/real-provider-smoke-validation` after this docs-only work is committed on `main`.

## Real Provider Configuration & Smoke Validation Phase 8 implementation entry

- Date: 2026-05-12
- Branch: feat/real-provider-smoke-validation
- Scope: Backend-only provider secret boundary and smoke validation hardening.
- Summary: Added provider secret reference resolution, recursive sensitive-key rejection for provider config/default params and execution payloads, sanitized provider API/health/ledger responses, health-check history listing, and safe provider smoke-test execution. Real OpenAI/OpenAI-compatible/MiMo/OmniVoice/GPT-SoVITS adapter execution now receives resolved secrets only in memory and treats missing required credentials as safe `auth_missing` failures with failed invocation records. Provider `auth_ref` remains an opaque reference string, restricted provider visibility is platform-admin-only, and OpenAI image/speech adapters no longer read `config_json.api_key`.
- Files changed: `/backend/packages/providers/src/noveland/providers/{secrets,contracts,health,registry,service}.py`, `/backend/packages/providers/src/noveland/providers/adapters/{openai_image,openai_speech}.py`, `/backend/services/api/src/noveland/services/api/providers.py`, `/backend/tests/{test_api_providers.py,test_provider_execution_service.py,test_provider_registry_service.py,test_openai_speech_adapter.py,test_workspace_imports.py}`, `/docs/agent/harness/**`
- Tests added/updated: Provider registry secret rejection/resolver tests, provider execution auth-missing/secret-leak tests, provider API smoke/health/ACL tests, OpenAI speech adapter in-memory secret mapping update, and workspace import coverage for `noveland.providers.secrets`.
- Docs updated: change journal and active handoff.
- Follow-up notes: No schema migration was needed for Phase 8. Full vault/KMS, encrypted DB secret storage, provider marketplace/UI, streaming, fallback/load balancing, and live provider tests beyond env-gated smoke coverage remain deferred.

## Character Sprite / Scene Asset System Phase 9 plan entry

- Date: 2026-05-12
- Branch: main
- Scope: Final feature implementation plan for Character Sprite / Scene Asset System Phase 9.
- Summary: Added the version-prefixed Phase 9 plan for strict-worldline visual binding records, character sprite sets/variants, scene background profiles, deterministic sprite/background resolution, and scene composition through the existing Phase 6 image composer without adding Web UI, provider generation, public reader delivery, or `worlds.py` route growth.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.9-character-sprite-scene-asset-system-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/visual-asset-system` after this docs-only work is committed on `main`.

## Character Sprite / Scene Asset System Phase 9 implementation entry

- Date: 2026-05-12
- Branch: feat/visual-asset-system
- Scope: Backend-only strict-worldline visual asset binding and resolver foundation.
- Summary: Added `noveland-visual`, strict-worldline character sprite sets/variants, scene background profiles, deterministic sprite/background resolution, a safe visual API router, and compose-scene orchestration through the existing Phase 6 `ImageService.compose_image()` path. Visual API responses use safe asset/object references that omit storage URIs while records continue to point at existing `media_assets` and `media_objects`.
- Files changed: `/backend/packages/visual/**`, `/backend/services/api/src/noveland/services/api/{app,visual}.py`, `/backend/migrations/versions/20260512_0037_visual_asset_system.py`, `/backend/tests/{test_visual_service.py,test_api_visual.py,test_schema_metadata.py,test_alembic_config.py,test_workspace_imports.py}`, `/backend/{pyproject.toml,uv.lock}`, `/backend/services/api/pyproject.toml`, `/backend/packages/core/src/noveland/core/database.py`, `/docs/agent/harness/**`
- Tests added/updated: Visual service tests, visual API tests, schema metadata registration, Alembic head coverage, workspace import coverage, plus backend lint/type targeted checks.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: No Web UI, background generation, public reader delivery, nullable worldline defaults, second media framework, or second composer was added.

## Multimodal Conversation Turn Integration Phase 10 plan entry

- Date: 2026-05-12
- Branch: main
- Scope: Final feature implementation plan for Multimodal Conversation Turn Integration Phase 10.
- Summary: Added the version-prefixed Phase 10 plan for canonical conversation turn presentation state, visual render orchestration through Phase 9/Phase 6 services, speech render/transcription orchestration through Phase 7 services, media reference attachment, and same-worldline validation without adding Web preview/playback UI, public reader delivery, streaming, runtime daemon orchestration, or memory auto-write.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.10-multimodal-conversation-turn-integration-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/multimodal-turn-presentation` after this docs-only work is committed on `main`.

## Multimodal Conversation Turn Integration Phase 10 implementation entry

- Date: 2026-05-12
- Branch: feat/multimodal-turn-presentation
- Scope: Backend-only canonical turn presentation and render orchestration.
- Summary: Added `conversation_turn_presentations`, conversation presentation contracts/service, and an independent API router for presentation CRUD plus visual, speech, and transcription render actions. Visual rendering reuses Phase 9 `VisualResolver` and Phase 6 deterministic composition through `VisualCompositionService`; speech rendering and transcription reuse Phase 7 `SpeechService`; rendered assets attach through Phase 4 `media_references` without mutating turn text or auto-writing STT transcripts to memory.
- Files changed: `/backend/packages/conversations/src/noveland/conversations/{contracts,models,presentation,__init__}.py`, `/backend/services/api/src/noveland/services/api/{app,conversation_presentations}.py`, `/backend/migrations/versions/20260512_0038_conversation_turn_presentations.py`, `/backend/tests/{test_conversation_presentation_service.py,test_api_conversation_presentations.py,test_schema_metadata.py,test_alembic_config.py,test_workspace_imports.py}`, `/docs/agent/harness/**`
- Tests added/updated: Presentation service tests, presentation API render orchestration tests, schema metadata registration, Alembic head coverage, and workspace import coverage.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: No Web preview/playback UI, public reader delivery, streaming, runtime daemon orchestration, second composer, or memory auto-write was added.

## Background Asset Generation Orchestrator Phase 11 plan entry

- Date: 2026-05-12
- Branch: main
- Scope: Final feature implementation plan for Background Asset Generation Orchestrator Phase 11.
- Summary: Added the version-prefixed Phase 11 plan for admin-reviewed asset generation policies, preview runs, persisted proposals, explicit apply into queued media jobs, and media job reprioritize/cancel-superseded helpers. The plan explicitly reuses existing media jobs, visual/speech/presentation/provider capability records and excludes daemon hooks, automatic provider execution, Web UI, streaming, and public reader delivery.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.11-background-asset-generation-orchestrator-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/asset-generation-orchestrator` after this docs-only work is committed on `main`.

## Background Asset Generation Orchestrator Phase 11 implementation entry

- Date: 2026-05-12
- Branch: feat/asset-generation-orchestrator
- Scope: Backend-only admin-reviewed asset generation proposal orchestrator.
- Summary: Added `noveland-asset-generation`, strict-worldline asset generation policies/runs/proposals, preview analysis for missing visual/speech assets, explicit admin apply into queued `media_jobs`, and media job reprioritize/cancel-superseded helpers. Preview/apply do not execute providers, do not hook a daemon, and do not write to `world_events.payload`.
- Files changed: `/backend/packages/asset_generation/**`, `/backend/services/api/src/noveland/services/api/{app,asset_generation}.py`, `/backend/migrations/versions/20260512_0039_asset_generation_orchestrator.py`, `/backend/tests/{test_asset_generation_service.py,test_api_asset_generation.py,test_schema_metadata.py,test_alembic_config.py,test_workspace_imports.py}`, `/backend/{pyproject.toml,uv.lock}`, `/backend/services/api/pyproject.toml`, `/backend/packages/core/src/noveland/core/database.py`
- Tests added/updated: Asset generation service tests, asset generation API tests, schema metadata registration, Alembic head coverage, workspace import coverage, plus full local gate.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: No Web UI, runtime daemon hook, automatic provider execution, streaming, public reader delivery, or hidden background spend was added.

## Multimodal Evaluation And Diagnostics Phase 12 plan entry

- Date: 2026-05-12
- Branch: main
- Scope: Final feature implementation plan for Multimodal Evaluation And Diagnostics Phase 12.
- Summary: Added the version-prefixed Phase 12 plan for backend-only multimodal safety/cost/quality diagnostics, `multimodal-smoke` eval runs stored in existing `long_run_eval_runs`, diagnostics APIs, provider/media/invocation/visual/speech leak checks, and sample-world regression coverage without creating a duplicate release framework.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.12-multimodal-eval-diagnostics-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/multimodal-eval-diagnostics` after this docs-only work is committed on `main`.

## Architecture Freeze & Regression Fixture Phase 13 plan entry

- Date: 2026-05-13
- Branch: main
- Scope: Final feature implementation plan for Architecture Freeze & Regression Fixture Phase 13.
- Summary: Added the version-prefixed Phase 13 plan for freezing Phase 3-12 architecture boundaries, adding architecture/API/data model inventories, concise ADRs, a multimodal sample-world fixture, and a regression test entrypoint without adding new product features, providers, Web UI, daemon execution, streaming, schema normalization, or release gate semantic changes.
- Files changed: `/docs/agent/harness/feature-updates/v0.3.1.13-architecture-freeze-regression-fixture-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: Implementation should start on `feat/architecture-freeze-regression-fixture` after this docs-only work is committed on `main`.

## Architecture Freeze & Regression Fixture Phase 13 implementation entry

- Date: 2026-05-13
- Branch: feat/architecture-freeze-regression-fixture
- Scope: Architecture freeze docs, ADRs, sample-world fixture, and regression entrypoint.
- Summary: Added Phase 3-12 architecture contract documentation, API and data model inventories, concise accepted ADRs, sample-world fixture documentation, a deterministic backend fixture helper, and a regression test that verifies worldline isolation, media integrity, resolver behavior, provider secret hygiene, access control, event payload hygiene, asset-generation admin control, and multimodal diagnostics.
- Files changed: `/docs/agent/architecture/{current-system-contracts.md,api-contract-inventory.md,data-model-inventory.md,adr/*.md}`, `/docs/agent/fixtures/multimodal-sample-world.md`, `/backend/tests/fixtures/multimodal_sample_world.py`, `/backend/tests/test_multimodal_sample_world_regression.py`, `/docs/agent/harness/**`
- Tests added/updated: `test_multimodal_sample_world_regression.py` plus targeted Phase 13 regression command.
- Docs updated: project index, file inventory, change journal, and active handoff.
- Follow-up notes: No new provider capability, business feature, Web UI, daemon execution, streaming, release gate semantic change, schema migration, or `worlds.py` refactor should be introduced in this phase.

## v0.4 Admin UX Foundation plan entry

- Date: 2026-05-13
- Branch: main
- Scope: Final implementation plan for v0.4 Operator/Admin UX Phase 1.
- Summary: Added the v0.4.1 plan for shared admin shell conventions, route guards, loading/error/empty states, admin API client conventions, and table/detail/action patterns. The phase explicitly avoids backend behavior changes, schema migrations, concrete provider/media/visual/speech business consoles, public reader UI, and daemon or streaming behavior.
- Files changed: `/docs/agent/harness/feature-updates/v0.4.1-admin-ux-foundation-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, task board, and active handoff.
- Follow-up notes: Implementation should start on `feat/admin-ux-foundation` after this docs-only work is committed on `main`.

## v0.4 Admin UX Foundation implementation entry

- Date: 2026-05-13
- Branch: feat/admin-ux-foundation
- Scope: Shared Web admin foundation for v0.4 Operator/Admin UX.
- Summary: Added reusable admin notice, state, section, metric, table, description-list, action-bar components; added a platform-admin route guard helper; added a small admin request helper that preserves CSRF and same-origin fetch conventions; and wired existing platform admin pages through the shared guard without changing backend behavior or adding new business consoles.
- Files changed: `/web/features/admin/admin-foundation.tsx`, `/web/features/admin/admin-route-guard.ts`, `/web/lib/admin/api-client.ts`, `/web/app/admin/**/page.tsx`, `/web/app/globals.css`, `/web/features/admin/*.test.tsx`, `/web/lib/admin/api-client.test.ts`, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: `admin-foundation`, `admin-route-guard`, and `admin/api-client` Web tests; targeted admin tests; full local gate.
- Docs updated: OpenSpec tasks, change journal, file inventory, project index, task board, and active handoff.
- Follow-up notes: Phase 2 should build the provider admin console on top of these shared admin patterns. No backend behavior, migrations, provider adapters, Web reader UI, daemon behavior, streaming, or public media delivery was added.

## v0.4 Provider Admin Console plan entry

- Date: 2026-05-13
- Branch: main
- Scope: Final implementation plan for v0.4 Operator/Admin UX Phase 2.
- Summary: Added the v0.4.2 plan for a world-scoped provider integration admin console at `/worlds/{worldId}/providers`, while leaving the legacy `/admin/providers` provider-profile page unchanged. The plan covers provider integration CRUD, capabilities, health-check history/action, smoke-test action, auth_ref reference display, and restricted visibility handling without backend kernel changes, migrations, resolved secret display, new adapters, public reader provider exposure, or provider boundary changes.
- Files changed: `/docs/agent/harness/feature-updates/v0.4.2-provider-admin-console-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, task board, and active handoff.
- Follow-up notes: Implementation should start on `feat/provider-admin-console` after this docs-only work is committed on `main`.

## v0.4 Provider Admin Console implementation entry

- Date: 2026-05-13
- Branch: feat/provider-admin-console
- Scope: World-scoped Web admin console for Phase 5+ provider integrations.
- Summary: Added `/worlds/{worldId}/providers`, provider integration client helpers, server-side provider admin data loader, and a provider integration admin component for list/detail, create/update/delete, capabilities, health-check history/action, smoke-test action, auth_ref reference display, and restricted visibility notices. The legacy `/admin/providers` provider-profile page remains unchanged.
- Files changed: `/web/app/worlds/[worldId]/providers/page.tsx`, `/web/features/admin/provider-integration-admin.tsx`, `/web/lib/worlds/provider-integrations.ts`, `/web/lib/worlds/server.ts`, `/web/features/workspace/workspace-shell.tsx`, related Web tests, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: Provider integration client tests and provider integration admin component tests.
- Docs updated: OpenSpec tasks, change journal, file inventory, project index, task board, and active handoff.
- Follow-up notes: No backend provider kernel changes, migrations, new provider adapters, resolved secret display, public reader provider exposure, or provider execution boundary changes were added.

## v0.4 Provider Admin Console merge entry

- Date: 2026-05-13
- Branch: main
- Scope: Fast-forward merge completion for v0.4 Operator/Admin UX Phase 2.
- Summary: Fast-forward merged `feat/provider-admin-console` into local `main` after the full local gate passed. OpenSpec Phase 2 tasks now mark full gate and merge complete, and the active handoff points to Phase 3 Media Asset Admin Console.
- Files changed: `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 2 full local gate.
- Docs updated: OpenSpec tasks, change journal, and active handoff.
- Follow-up notes: Start Phase 3 from clean local `main`; do not push unless explicitly requested.

## v0.4 Media Asset Admin Console plan entry

- Date: 2026-05-13
- Branch: main
- Scope: Final implementation plan for v0.4 Operator/Admin UX Phase 3.
- Summary: Added the v0.4.3 plan for a world-scoped media asset admin console at `/worlds/{worldId}/media`. The plan covers asset list/detail, object list/download actions, job list/status, reference browser, upload flow, visibility/status filters, safe metadata summaries, and reuse of existing media APIs without backend media kernel changes.
- Files changed: `/docs/agent/harness/feature-updates/v0.4.3-media-admin-console-plan.md`, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, task board, and active handoff.
- Follow-up notes: Implementation should start on `feat/media-admin-console` after this docs-only work is committed on `main`.

## v0.4 Media Asset Admin Console implementation entry

- Date: 2026-05-13
- Branch: feat/media-admin-console
- Scope: World-scoped Web admin console for media assets, objects, jobs, references, uploads, and safe download actions.
- Summary: Added `/worlds/{worldId}/media`, media client helpers, server-side media admin data loader, and a media admin component for asset list/detail, object list/download actions, job status/actions, reference browsing, upload flow, and filters. The UI summarizes metadata and request JSON without rendering internal object storage references, file paths, raw bytes, base64, raw prompts, or raw outputs.
- Files changed: `/web/app/worlds/[worldId]/media/page.tsx`, `/web/features/admin/media-admin.tsx`, `/web/lib/worlds/media.ts`, `/web/lib/worlds/server.ts`, `/web/features/workspace/workspace-shell.tsx`, related Web tests, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: Media client tests, media admin component tests, and e2e stabilization for slow mock-server action/navigation waits.
- Docs updated: OpenSpec tasks, change journal, file inventory, project index, task board, and active handoff.
- Verification: Targeted tests passed; full local gate passed with backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`88 passed`), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: No backend media kernel behavior, migrations, storage backend, public reader media delivery, provider execution, asset generation, daemon behavior, or `worlds.py` change was added. Fast-forward merge to local `main` remains next.

## v0.4 Media Asset Admin Console merge entry

- Date: 2026-05-13
- Branch: main
- Scope: Fast-forward merge completion for v0.4 Operator/Admin UX Phase 3.
- Summary: Fast-forward merged `feat/media-admin-console` into local `main` after the targeted tests and full local gate passed. OpenSpec Phase 3 tasks now mark the fast-forward merge complete, and the active handoff points to Phase 4 Visual Asset Admin Console planning.
- Files changed: `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 3 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 4 from clean local `main`; do not push unless explicitly requested.

## v0.4 Visual Asset Admin Console plan entry

- Date: 2026-05-13
- Branch: main
- Scope: Final implementation plan for v0.4 Operator/Admin UX Phase 4.
- Summary: Added the v0.4.4 plan for a world-scoped visual asset admin console at `/worlds/{worldId}/visual`. The plan covers strict-worldline sprite sets, sprite variants, scene backgrounds, sprite/background resolver previews, and explicit compose-scene actions using existing visual and media APIs without backend visual behavior changes.
- Files changed: `/docs/agent/harness/feature-updates/v0.4.4-visual-admin-console-plan.md`, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, task board, and active handoff.
- Follow-up notes: Implementation should start on `feat/visual-admin-console` after this docs-only work is committed on `main`.

## v0.4 Visual Asset Admin Console implementation entry

- Date: 2026-05-13
- Branch: feat/visual-admin-console
- Scope: World-scoped Web admin console for strict-worldline sprite sets, sprite variants, scene backgrounds, resolver previews, and explicit compose-scene actions.
- Summary: Added `/worlds/{worldId}/visual`, visual client helpers, server-side visual admin data loader, and a visual admin component for selecting a worldline, managing sprite/background records, running deterministic resolver previews, and explicitly composing scenes through the existing visual compose endpoint. The UI displays safe media identifiers, dimensions, checksums, statuses, visibility, and fallback reasons without rendering storage URIs, filesystem paths, raw bytes, base64 payloads, raw prompts, or raw outputs.
- Files changed: `/web/app/worlds/[worldId]/visual/page.tsx`, `/web/features/admin/visual-admin.tsx`, `/web/lib/worlds/visual.ts`, `/web/lib/worlds/server.ts`, `/web/features/workspace/workspace-shell.tsx`, related Web tests, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: Visual client tests, visual admin component tests, and workspace navigation test.
- Docs updated: OpenSpec tasks, change journal, file inventory, project index, task board, and active handoff.
- Verification: Targeted tests passed with `npm run test -- visual-admin visual workspace-shell` (3 files, 8 tests), plus web lint, web typecheck, and `git diff --check`. Full local gate passed with backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`96 passed` after standalone rerun), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: No backend visual behavior, migrations, automatic sprite/background generation, asset generation orchestration, nullable-worldline visual defaults, public reader delivery, provider execution, daemon behavior, streaming, or `worlds.py` change was added. `web npm run test` timed out once when run concurrently with backend pytest due to Vitest worker startup timeouts; the standalone rerun passed.

## v0.4 Visual Asset Admin Console merge entry

- Date: 2026-05-13
- Branch: main
- Scope: Fast-forward merge completion for v0.4 Operator/Admin UX Phase 4.
- Summary: Fast-forward merged `feat/visual-admin-console` into local `main` after the targeted tests and full local gate passed. OpenSpec Phase 4 tasks now mark the fast-forward merge complete, and the active handoff points to Phase 5 Speech Admin Console planning.
- Files changed: `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 4 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 5 from clean local `main`; do not push unless explicitly requested.

## v0.4 Speech Admin Console plan entry

- Date: 2026-05-13
- Branch: main
- Scope: Final implementation plan for v0.4 Operator/Admin UX Phase 5.
- Summary: Added the v0.4.5 plan for a world-scoped speech admin console at `/worlds/{worldId}/speech`. The plan covers voice profile CRUD, agent voice bindings, style mappings, transcript browsing, and explicit TTS/STT test actions using existing speech, provider, media, and invocation APIs without backend speech behavior changes.
- Files changed: `/docs/agent/harness/feature-updates/v0.4.5-speech-admin-console-plan.md`, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, task board, and active handoff.
- Follow-up notes: Implementation should start on `feat/speech-admin-console` after this docs-only work is committed on `main`.

## v0.4 Speech Admin Console implementation entry

- Date: 2026-05-13
- Branch: feat/speech-admin-console
- Scope: World-scoped Web admin console for voice profiles, agent voice bindings, speech style mappings, transcripts, and explicit TTS/STT test actions.
- Summary: Added `/worlds/{worldId}/speech`, speech client helpers, server-side speech admin data loader, and a speech admin component for managing voice profiles, binding agents to voices, editing style mappings, browsing transcripts, and running explicit TTS/STT tests through existing speech APIs. The UI displays safe media job, media asset/object, transcript, and invocation IDs without rendering storage URIs, filesystem paths, raw bytes, base64 payloads, raw prompts, raw outputs, or resolved secrets.
- Files changed: `/web/app/worlds/[worldId]/speech/page.tsx`, `/web/features/admin/speech-admin.tsx`, `/web/lib/worlds/speech.ts`, `/web/lib/worlds/server.ts`, `/web/features/workspace/workspace-shell.tsx`, related Web tests, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: Speech client tests, speech admin component tests, and workspace navigation test.
- Docs updated: OpenSpec tasks, change journal, file inventory, project index, task board, and active handoff.
- Verification: Targeted tests passed with `npm run test -- speech-admin speech workspace-shell` (3 files, 7 tests). Full local gate passed with backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`102 passed`), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: No backend speech behavior, migrations, realtime voice, streaming, local voice server deployment, automatic STT memory writes, public reader audio delivery, provider adapter changes, daemon behavior, or `worlds.py` change was added.

## v0.4 Speech Admin Console merge entry

- Date: 2026-05-13
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.4 Operator/Admin UX Phase 5.
- Summary: Fast-forward merged `feat/speech-admin-console` into local `main` after the targeted tests and full local gate passed. OpenSpec Phase 5 tasks now mark the full gate, fast-forward merge, and harness update complete, and the active handoff points to Phase 6 Invocation Ledger Browser planning.
- Files changed: `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 5 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 6 from clean local `main`; do not push unless explicitly requested.

## v0.4 Invocation Ledger Browser plan entry

- Date: 2026-05-13
- Branch: main
- Scope: Final implementation plan for v0.4 Operator/Admin UX Phase 6.
- Summary: Added the v0.4.6 plan for a world-scoped invocation ledger browser at `/worlds/{worldId}/invocations`. The plan covers invocation list/detail, prompt snapshot evidence, tag management, redaction actions, visibility, and retention display using existing invocation APIs without backend ledger behavior changes.
- Files changed: `/docs/agent/harness/feature-updates/v0.4.6-invocation-ledger-browser-plan.md`, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, task board, and active handoff.
- Follow-up notes: Implementation should start on `feat/invocation-ledger-browser` after this docs-only work is committed on `main`.

## v0.4 Invocation Ledger Browser implementation entry

- Date: 2026-05-13
- Branch: feat/invocation-ledger-browser
- Scope: World-scoped Web admin console for model invocation ledger records, prompt snapshots, tags, redaction actions, visibility, and retention state.
- Summary: Added `/worlds/{worldId}/invocations`, invocation ledger client helpers, server-side invocation admin data loader, and an invocation ledger browser component for filtering invocations, inspecting selected records, viewing prompt snapshot checksums/evidence, creating/deleting tags, and running explicit redaction actions through existing invocation APIs. The UI recursively redacts secret-like keys, storage URI/path values, and base64-like payloads before rendering evidence summaries.
- Files changed: `/web/app/worlds/[worldId]/invocations/page.tsx`, `/web/features/admin/invocation-ledger-admin.tsx`, `/web/lib/worlds/invocations.ts`, `/web/lib/worlds/server.ts`, `/web/features/workspace/workspace-shell.tsx`, related Web tests, `/web/app/globals.css`, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: Invocation ledger client tests, invocation ledger admin component tests, and workspace navigation test.
- Docs updated: OpenSpec tasks, change journal, file inventory, project index, task board, and active handoff.
- Verification: Targeted tests passed with `npm run test -- invocation-ledger invocation workspace-shell` (3 files, 6 tests). Full local gate passed with backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`107 passed`), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: No backend invocation behavior, migrations, external tracing export, reader/member raw prompt exposure, provider execution changes, daemon behavior, or `worlds.py` change was added.

## v0.4 Invocation Ledger Browser merge entry

- Date: 2026-05-13
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.4 Operator/Admin UX Phase 6.
- Summary: Fast-forward merged `feat/invocation-ledger-browser` into local `main` after the targeted tests and full local gate passed. OpenSpec Phase 6 tasks now mark the full gate, fast-forward merge, and harness update complete, and the active handoff points to Phase 7 Multimodal Diagnostics Dashboard planning.
- Files changed: `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 6 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 7 from clean local `main`; do not push unless explicitly requested.

## v0.4 Multimodal Diagnostics Dashboard plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.4 Operator/Admin UX Phase 7.
- Summary: Added the v0.4.7 plan for a world-scoped multimodal diagnostics dashboard at `/worlds/{worldId}/diagnostics`. The plan covers current diagnostics, blocker/warning summaries, safe evidence references, recent multimodal eval runs, cost/latency summaries, provider/media/invocation/visual/speech status summaries, and an explicit multimodal smoke eval action using existing backend APIs without backend diagnostic rule changes.
- Files changed: `/docs/agent/harness/feature-updates/v0.4.7-multimodal-diagnostics-dashboard-plan.md`, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only change; verify with `git diff --check`.
- Docs updated: project index, file inventory, change journal, task board, and active handoff.
- Follow-up notes: Implementation should start on `feat/multimodal-diagnostics-dashboard` after this docs-only work is committed on `main`.

## v0.4 Multimodal Diagnostics Dashboard implementation entry

- Date: 2026-05-14
- Branch: feat/multimodal-diagnostics-dashboard
- Scope: World-scoped Web admin dashboard for Phase 12 multimodal diagnostics, findings, safe evidence references, metrics, and eval runs.
- Summary: Added `/worlds/{worldId}/diagnostics`, multimodal diagnostics client helpers, server-side diagnostics admin data loader, and a dashboard component for current diagnostic status, blocker/warning tables, recommendations, provider/media/invocation/visual/speech/event summaries, and explicit multimodal smoke eval runs through existing backend APIs.
- Files changed: `/web/app/worlds/[worldId]/diagnostics/page.tsx`, `/web/features/admin/multimodal-diagnostics-admin.tsx`, `/web/lib/worlds/diagnostics.ts`, `/web/lib/worlds/server.ts`, `/web/features/workspace/workspace-shell.tsx`, related Web tests, `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: Multimodal diagnostics client tests, multimodal diagnostics admin component tests, and workspace navigation test.
- Docs updated: OpenSpec tasks, change journal, file inventory, project index, task board, and active handoff.
- Verification: Targeted tests passed with `npm run test -- multimodal-diagnostics diagnostics workspace-shell` (3 files, 6 tests). Full local gate passed with backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`112 passed` after standalone rerun; initial concurrent run with `next build` timed out), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: No backend diagnostic rule changes, migrations, duplicate release/eval framework, public launch gate changes, provider execution changes, daemon behavior, streaming, public reader delivery, or `worlds.py` change was added.

## v0.4 Multimodal Diagnostics Dashboard merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.4 Operator/Admin UX Phase 7.
- Summary: Fast-forward merged `feat/multimodal-diagnostics-dashboard` into local `main` after the targeted tests and full local gate passed. OpenSpec Phase 7 tasks now mark the full gate, fast-forward merge, and harness update complete, completing the v0.4 Operator/Admin UX implementation sequence locally.
- Files changed: `/openspec/changes/v0-4-operator-admin-ux/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 7 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: No push was performed. Archive the OpenSpec v0.4 change only if explicitly requested.

## v0.4 Operator/Admin UX archive entry

- Date: 2026-05-14
- Branch: main
- Scope: OpenSpec archive and release notes for the completed v0.4 Operator/Admin UX sequence.
- Summary: Promoted the seven v0.4 admin capabilities into current OpenSpec specs, archived `v0-4-operator-admin-ux`, and added release notes summarizing the completed operator/admin Web surfaces and validation evidence.
- Files changed: `/openspec/specs/admin-ux-foundation/spec.md`, `/openspec/specs/provider-admin-console/spec.md`, `/openspec/specs/media-admin-console/spec.md`, `/openspec/specs/visual-admin-console/spec.md`, `/openspec/specs/speech-admin-console/spec.md`, `/openspec/specs/invocation-ledger-browser/spec.md`, `/openspec/specs/multimodal-diagnostics-dashboard/spec.md`, `/openspec/changes/archive/2026-05-14-v0-4-operator-admin-ux/**`, `/docs/agent/harness/release-notes/v0.4-operator-admin-ux.md`, `/docs/agent/harness/**`
- Tests added/updated: Documentation/spec-only change; validate with OpenSpec validation and `git diff --check`.
- Docs updated: current OpenSpec specs, release notes, project index, file inventory, task board, change journal, and active handoff.
- Follow-up notes: v0.5 must begin with feasibility review only; no v0.5 implementation should start until its review is accepted.

## v0.5 Authoring subsystem architecture decision entry

- Date: 2026-05-14
- Branch: main
- Scope: OpenSpec planning update for v0.5 Authoring & Import Studio.
- Summary: Updated v0.5 OpenSpec docs to require a dedicated `backend/packages/authoring/` package and `authoring.py` API router, move import run/proposal/review/source-traceability preview/apply foundation into Phase 1, treat legacy authoring templates/jobs and world composition import as compatibility inputs/references, and keep lore/world-bible extraction proposal-only.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/proposal.md`, `/openspec/changes/v0-5-authoring-import-studio/design.md`, `/openspec/changes/v0-5-authoring-import-studio/phase-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/openspec/changes/v0-5-authoring-import-studio/specs/**`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation/spec-only change; validate with OpenSpec validation and `git diff --check`.
- Docs updated: v0.5 OpenSpec proposal, design, phase plan, tasks, capability specs, change journal, and active handoff.
- Follow-up notes: Do not start v0.5 implementation until explicitly requested; Phase 1 should implement only Authoring Import Core.

## v0.5 Authoring Import Core plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.5 Authoring & Import Studio Phase 1.
- Summary: Added the v0.5.1 plan for a dedicated authoring package/router and source registry plus import run/proposal/review/source-traceability preview/apply foundation. The plan explicitly avoids provider-backed extraction, automatic memory writes, direct lore/world-bible apply, new media/provider/memory frameworks, Web UI, and new `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.5.1-authoring-import-core-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, and change journal.
- Follow-up notes: Implementation should start on `feat/authoring-import-core` after this docs-only checkpoint is committed.

## v0.5 Authoring Import Core implementation entry

- Date: 2026-05-14
- Branch: feat/authoring-import-core
- Scope: Dedicated authoring package/router plus source registry and proposal/review/preview/apply foundation.
- Summary: Added `backend/packages/authoring/`, the app-level `/worlds/{world_id}/authoring` router, migration `20260514_0040`, source batch/asset/fragment records, import run/proposal/review decision/source traceability records, safe JSON validation, media same-worldline validation, preview without provider execution, and explicit proposal-kind-gated trace-only apply. Unsupported kinds such as lore remain blocked in Phase 1.
- Files changed: `/backend/packages/authoring/**`, `/backend/services/api/src/noveland/services/api/authoring.py`, `/backend/services/api/src/noveland/services/api/app.py`, `/backend/migrations/versions/20260514_0040_authoring_import_core.py`, backend workspace/config files, `/backend/tests/test_authoring_service.py`, `/backend/tests/test_api_authoring.py`, schema/import/Alembic tests, OpenSpec tasks, and harness docs.
- Tests added/updated: Authoring service/API tests, schema metadata registration, workspace imports, and Alembic latest-revision coverage.
- Docs updated: OpenSpec Phase 1 task status, project index, file inventory, and change journal.
- Verification: Targeted tests passed with `cd backend && uv run pytest tests/test_authoring_service.py tests/test_api_authoring.py tests/test_schema_metadata.py tests/test_alembic_config.py tests/test_workspace_imports.py` (`32 passed`). Full local gate passed with backend ruff, backend mypy, backend pytest (`298 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: No provider-backed extraction, direct lore/world-bible apply, automatic memory writes, new media/provider/memory framework, Web UI, daemon behavior, public reader delivery, streaming, or new `worlds.py` routes were added.

## v0.5 Authoring Import Core merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.5 Authoring & Import Studio Phase 1.
- Summary: Fast-forward merged `feat/authoring-import-core` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 1 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 1 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 2 from clean local `main`; do not push unless explicitly requested.

## v0.5 Script Parser & Dialogue Extractor plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.5 Authoring & Import Studio Phase 2.
- Summary: Added the v0.5.2 plan for deterministic parsing of existing authoring source fragments into reviewable Phase 1 proposals. The plan explicitly avoids provider-backed parsing, new migrations unless required, Web UI, direct canonical mutation, raw full source persistence, world events, and new `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.5.2-script-parser-dialogue-extractor-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, and change journal.
- Follow-up notes: Implementation should start on `feat/script-parser-dialogue-extractor` after this docs-only checkpoint is committed.

## v0.5 Script Parser & Dialogue Extractor implementation entry

- Date: 2026-05-14
- Branch: feat/script-parser-dialogue-extractor
- Scope: Backend-only deterministic script parser and dialogue extractor for v0.5 Authoring & Import Studio Phase 2.
- Summary: Added a deterministic authoring parser that converts existing source fragment excerpts into traceable Phase 1 authoring proposals for dialogue, unresolved quoted dialogue, scenes, choices, routes, and events. Added `parse-script` on the dedicated authoring router. The implementation does not call providers, does not add migrations, does not mutate canonical world state, does not write world events, and does not add Web UI or `worlds.py` routes.
- Files changed: `/backend/packages/authoring/src/noveland/authoring/parser.py`, `/backend/packages/authoring/src/noveland/authoring/contracts.py`, `/backend/packages/authoring/src/noveland/authoring/service.py`, `/backend/services/api/src/noveland/services/api/authoring.py`, `/backend/tests/test_authoring_service.py`, `/backend/tests/test_api_authoring.py`, `/backend/tests/test_workspace_imports.py`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Authoring service parser coverage, authoring API parser endpoint coverage, and workspace import coverage.
- Docs updated: OpenSpec Phase 2 task status, change journal, task board, and file inventory.
- Verification: Targeted tests passed with `cd backend && uv run pytest tests/test_authoring_service.py tests/test_api_authoring.py tests/test_workspace_imports.py tests/test_alembic_config.py` (`10 passed`). Full local gate passed with backend ruff, backend mypy (`233 source files`), backend pytest (`300 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, `git diff --check`, and `openspec validate v0-5-authoring-import-studio --strict --json`.
- Follow-up notes: Fast-forward merge Phase 2 to local `main`, then update merge bookkeeping before starting Phase 3. Do not push unless explicitly requested.

## v0.5 Script Parser & Dialogue Extractor merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.5 Authoring & Import Studio Phase 2.
- Summary: Fast-forward merged `feat/script-parser-dialogue-extractor` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 2 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 2 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 3 from clean local `main`; do not push unless explicitly requested.

## v0.5 Character & Relationship Extractor plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.5 Authoring & Import Studio Phase 3.
- Summary: Added the v0.5.3 plan for deterministic extraction of character, alias, faction, identity, relationship, and emotional-baseline candidates into reviewable Phase 1 authoring proposals. The plan explicitly avoids provider-backed extraction, migrations unless required, Web UI, direct agent/relationship/memory/world-bible mutation, world events, and new `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.5.3-character-relationship-extractor-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, and change journal.
- Follow-up notes: Implementation should start on `feat/character-relationship-extractor` after this docs-only checkpoint is committed.

## v0.5 Character & Relationship Extractor implementation entry

- Date: 2026-05-14
- Branch: feat/character-relationship-extractor
- Scope: Backend-only deterministic character and relationship extractor for v0.5 Authoring & Import Studio Phase 3.
- Summary: Added a deterministic authoring extractor that converts existing source fragment excerpts and optional Phase 2 dialogue speaker proposals into traceable Phase 1 authoring proposals for characters, aliases, factions, identities, relationships, and emotional baselines. Added `extract-characters` on the dedicated authoring router. The implementation does not call providers, does not add migrations, does not mutate canonical agents/relationships/memory/world-bible records, does not write world events, and does not add Web UI or `worlds.py` routes.
- Files changed: `/backend/packages/authoring/src/noveland/authoring/character_extractor.py`, `/backend/packages/authoring/src/noveland/authoring/contracts.py`, `/backend/packages/authoring/src/noveland/authoring/service.py`, `/backend/services/api/src/noveland/services/api/authoring.py`, `/backend/tests/test_authoring_service.py`, `/backend/tests/test_api_authoring.py`, `/backend/tests/test_workspace_imports.py`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Authoring service extractor coverage, authoring API extractor endpoint coverage, and workspace import coverage.
- Docs updated: OpenSpec Phase 3 task status, project index, change journal, and task board.
- Verification: Targeted tests passed with `cd backend && uv run pytest tests/test_authoring_service.py tests/test_api_authoring.py tests/test_workspace_imports.py tests/test_alembic_config.py` (`12 passed`). Full local gate passed with backend ruff, backend mypy (`234 source files`), backend pytest (`302 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, `git diff --check`, and `openspec validate v0-5-authoring-import-studio --strict --json`.
- Follow-up notes: Fast-forward merge Phase 3 to local `main`, then update merge bookkeeping before starting Phase 4. Do not push unless explicitly requested.

## v0.5 Character & Relationship Extractor merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.5 Authoring & Import Studio Phase 3.
- Summary: Fast-forward merged `feat/character-relationship-extractor` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 3 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 3 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 4 from clean local `main`; do not push unless explicitly requested.

## v0.5 World Bible & Lore Extractor plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.5 Authoring & Import Studio Phase 4.
- Summary: Added the v0.5.4 plan for deterministic proposal-only extraction of lore, location, organization, world-rule, secret, and knowledge-boundary candidates into reviewable Phase 1 authoring proposals. The plan explicitly avoids provider-backed extraction, migrations unless required, Web UI, direct `WorldBible` or global canon mutation, world events, and new `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.5.4-world-bible-lore-extractor-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, and change journal.
- Follow-up notes: Implementation should start on `feat/world-bible-lore-extractor` after this docs-only checkpoint is committed.

## v0.5 World Bible & Lore Extractor implementation entry

- Date: 2026-05-14
- Branch: feat/world-bible-lore-extractor
- Scope: Backend-only deterministic proposal-only lore extractor for v0.5 Authoring & Import Studio Phase 4.
- Summary: Added a deterministic authoring lore extractor that converts existing source fragment excerpts into traceable Phase 1 authoring proposals for lore, locations, organizations, world rules, secrets, and knowledge boundaries. Added `extract-lore` on the dedicated authoring router. The implementation does not call providers, does not add migrations, does not mutate `WorldBible` or global canon records, does not write world events, and does not add Web UI or `worlds.py` routes. Lore proposals remain blocked by the existing unsupported proposal-kind apply guardrail.
- Files changed: `/backend/packages/authoring/src/noveland/authoring/lore_extractor.py`, `/backend/packages/authoring/src/noveland/authoring/contracts.py`, `/backend/packages/authoring/src/noveland/authoring/service.py`, `/backend/services/api/src/noveland/services/api/authoring.py`, `/backend/tests/test_authoring_service.py`, `/backend/tests/test_api_authoring.py`, `/backend/tests/test_workspace_imports.py`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Authoring service lore extractor and blocked apply coverage, authoring API lore extractor endpoint coverage, and workspace import coverage.
- Docs updated: OpenSpec Phase 4 task status, project index, change journal, and task board.
- Verification: Targeted tests passed with `cd backend && uv run pytest tests/test_authoring_service.py tests/test_api_authoring.py tests/test_workspace_imports.py tests/test_alembic_config.py` (`14 passed`). Full local gate passed with backend ruff, backend mypy (`235 source files`), backend pytest (`304 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, `git diff --check`, and `openspec validate v0-5-authoring-import-studio --strict --json`.
- Follow-up notes: Fast-forward merge Phase 4 to local `main`, then update merge bookkeeping before starting Phase 5. Do not push unless explicitly requested.

## v0.5 World Bible & Lore Extractor merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.5 Authoring & Import Studio Phase 4.
- Summary: Fast-forward merged `feat/world-bible-lore-extractor` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 4 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 4 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 5 from clean local `main`; do not push unless explicitly requested.

## v0.5 Canon Conflict Review plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.5 Authoring & Import Studio Phase 5.
- Summary: Added the v0.5.5 plan for deterministic conflict review of existing import-run proposals, producing reviewable conflict report proposals for duplicates, relationship/identity/baseline contradictions, uncertain lore, and OOC risk. The plan explicitly avoids provider-backed review, migrations unless required, Web UI, automatic conflict resolution, direct canonical mutation, world events, and new `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.5.5-canon-conflict-review-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, and change journal.
- Follow-up notes: Implementation should start on `feat/canon-conflict-review` after this docs-only checkpoint is committed.

## v0.5 Canon Conflict Review implementation entry

- Date: 2026-05-14
- Branch: feat/canon-conflict-review
- Scope: Backend-only deterministic canon conflict review for v0.5 Authoring & Import Studio Phase 5.
- Summary: Added deterministic conflict review over existing import-run proposals, producing traceable `other` conflict report proposals for duplicate characters/lore/locations/organizations, relationship and identity/baseline contradictions, uncertain canon, and OOC risk. Added `review-conflicts` on the dedicated authoring router. The implementation does not call providers, does not add migrations, does not automatically resolve conflicts, does not mutate canonical records, does not write world events, and does not add Web UI or `worlds.py` routes.
- Files changed: `/backend/packages/authoring/src/noveland/authoring/conflict_review.py`, `/backend/packages/authoring/src/noveland/authoring/contracts.py`, `/backend/packages/authoring/src/noveland/authoring/service.py`, `/backend/services/api/src/noveland/services/api/authoring.py`, `/backend/tests/test_authoring_service.py`, `/backend/tests/test_api_authoring.py`, `/backend/tests/test_workspace_imports.py`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Authoring service conflict report coverage, authoring API conflict review endpoint coverage, and workspace import coverage.
- Docs updated: OpenSpec Phase 5 task status, project index, change journal, and task board.
- Verification: Targeted tests passed with `cd backend && uv run pytest tests/test_authoring_service.py tests/test_api_authoring.py tests/test_workspace_imports.py tests/test_alembic_config.py` (`16 passed`). Full local gate passed with backend ruff, backend mypy (`236 source files`), backend pytest (`306 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, `git diff --check`, and `openspec validate v0-5-authoring-import-studio --strict --json`.
- Follow-up notes: Fast-forward merge Phase 5 to local `main`, then update merge bookkeeping before starting Phase 6. Do not push unless explicitly requested.

## v0.5 Canon Conflict Review merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.5 Authoring & Import Studio Phase 5.
- Summary: Fast-forward merged `feat/canon-conflict-review` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 5 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 5 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 6 from clean local `main`; do not push unless explicitly requested.

## v0.5 Memory Migration Pipeline plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.5 Authoring & Import Studio Phase 6.
- Summary: Added the v0.5.6 plan for deterministic memory migration proposal generation from source fragments and existing import-run proposals. The plan explicitly avoids provider-backed extraction, migrations unless required, Web UI, direct memory writes, memory backend SDK access, direct canonical mutation, world events, and new `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.5.6-memory-migration-pipeline-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, and change journal.
- Follow-up notes: Implementation should start on `feat/memory-migration-pipeline` after this docs-only checkpoint is committed.

## v0.5 Memory Migration Pipeline implementation entry

- Date: 2026-05-14
- Branch: feat/memory-migration-pipeline
- Scope: Backend-only deterministic memory migration proposal generation for v0.5 Authoring & Import Studio Phase 6.
- Summary: Added a deterministic memory migration analyzer that converts source fragments and existing import-run proposals into reviewable fact, episodic, relationship, preference, and style memory proposals. The implementation reuses Phase 1 authoring runs/proposals, blocks direct memory proposal apply, avoids provider execution, avoids memory backend writes, and does not emit world events.
- Files changed: `/backend/packages/authoring/src/noveland/authoring/{__init__,contracts,memory_migration,service}.py`, `/backend/services/api/src/noveland/services/api/authoring.py`, `/backend/tests/test_authoring_service.py`, `/backend/tests/test_api_authoring.py`, `/backend/tests/test_workspace_imports.py`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Authoring service memory migration coverage, authoring API memory migration endpoint coverage, direct memory apply guardrail coverage, and workspace import coverage.
- Docs updated: OpenSpec tasks, project index, task board, active handoff, and change journal.
- Follow-up notes: Phase 6 full local gate passed; fast-forward merge to local `main`, record merge bookkeeping, then continue with Phase 7 Asset Import & Matching.

## v0.5 Memory Migration Pipeline merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.5 Authoring & Import Studio Phase 6.
- Summary: Fast-forward merged `feat/memory-migration-pipeline` into local `main`, marked Phase 6 complete in OpenSpec tasks, and moved harness handoff state to Phase 7 Asset Import & Matching.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: N/A.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 7 from clean local `main`; do not push unless explicitly requested.

## v0.5 Asset Import & Matching plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.5 Authoring & Import Studio Phase 7.
- Summary: Added the v0.5.7 plan for deterministic asset matching proposals that connect imported media-backed source assets to sprite, background, CG, and voice-reference candidates. The plan explicitly avoids provider-backed matching, migrations unless required, Web UI, new upload/media delivery paths, automatic visual/speech binding apply, direct canonical mutation, world events, and new `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.5.7-asset-import-matching-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Implementation should start on `feat/asset-import-matching` after this docs-only checkpoint is committed.

## v0.5 Asset Import & Matching implementation entry

- Date: 2026-05-14
- Branch: feat/asset-import-matching
- Scope: Backend-only deterministic asset matching proposal generation for v0.5 Authoring & Import Studio Phase 7.
- Summary: Added a deterministic asset matcher that turns imported media-backed source assets into reviewable sprite, background, CG, and voice-reference proposals. The implementation reuses Phase 1 authoring runs/proposals, validates same-worldline media assets, suppresses hidden/developer-only media, blocks unsupported canonical apply, avoids provider execution, avoids media job creation, and does not emit world events.
- Files changed: `/backend/packages/authoring/src/noveland/authoring/{__init__,asset_matching,contracts,service}.py`, `/backend/services/api/src/noveland/services/api/authoring.py`, `/backend/tests/test_authoring_service.py`, `/backend/tests/test_api_authoring.py`, `/backend/tests/test_workspace_imports.py`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Authoring service asset matching coverage, cross-worldline rejection coverage, hidden-media suppression coverage, authoring API asset matching endpoint coverage, and workspace import coverage.
- Docs updated: OpenSpec tasks, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Phase 7 full local gate passed; fast-forward merge to local `main`, record merge bookkeeping, then continue with Phase 8 Authoring Regression Fixture.

## v0.5 Asset Import & Matching merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.5 Authoring & Import Studio Phase 7.
- Summary: Fast-forward merged `feat/asset-import-matching` into local `main`, marked Phase 7 complete in OpenSpec tasks, and moved harness handoff state to Phase 8 Authoring Regression Fixture.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: N/A.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 8 from clean local `main`; do not push unless explicitly requested.

## v0.5 Authoring Regression Fixture plan entry

- Date: 2026-05-14
- Branch: main
- Scope: Final implementation plan for v0.5 Authoring & Import Studio Phase 8.
- Summary: Added the v0.5.8 plan for a deterministic galgame import regression fixture covering source registry, script parsing, character extraction, lore proposal extraction, conflict review, memory migration, asset matching, review decisions, and guarded apply behavior. The plan explicitly avoids migrations, Web UI, production seed frameworks, provider-backed work, direct canonical mutation, media jobs, memory write jobs, world events, and new `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.5.8-authoring-regression-fixture-plan.md`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Implementation should start on `feat/authoring-regression-fixture` after this docs-only checkpoint is committed.

## v0.5 Authoring Regression Fixture implementation entry

- Date: 2026-05-14
- Branch: feat/authoring-regression-fixture
- Scope: Backend-only deterministic authoring regression fixture for v0.5 Authoring & Import Studio Phase 8.
- Summary: Added an authoring sample import fixture and regression tests that exercise source registry, script parsing, character extraction, lore proposal extraction, conflict review, memory migration, asset matching, review decisions, and guarded apply behavior. The fixture validates deterministic signatures, strict worldline scope, no provider/media/memory/visual/speech side effects, no world events, and no storage/path/base64/raw prompt or output leaks.
- Files changed: `/backend/tests/fixtures/authoring_sample_import.py`, `/backend/tests/test_authoring_regression_fixture.py`, `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Authoring sample import deterministic signature, worldline scope, pipeline coverage, guarded apply, side-effect, and leak regression tests.
- Docs updated: OpenSpec tasks, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Phase 8 full local gate passed; fast-forward merge to local `main`, record merge bookkeeping, then provide v0.5 closeout status.

## v0.5 Authoring Regression Fixture merge entry

- Date: 2026-05-14
- Branch: main
- Scope: Fast-forward merge bookkeeping and closeout for v0.5 Authoring & Import Studio Phase 8.
- Summary: Fast-forward merged `feat/authoring-regression-fixture` into local `main`, marked Phase 8 and all v0.5 OpenSpec tasks complete, and updated harness state to v0.5 closeout.
- Files changed: `/openspec/changes/v0-5-authoring-import-studio/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: N/A.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: v0.5 is complete locally; OpenSpec archive and release notes remain optional docs-only follow-up if requested. Do not push unless explicitly requested.

## v0.6 Runtime Context Contract v2 implementation entry

- Date: 2026-05-15
- Branch: feat/runtime-context-contract-v2
- Scope: Backend-only v0.6 Runtime Narrative Quality Phase 1 runtime context contract preview.
- Summary: Added the dedicated `narrative_quality` package and app-level narrative quality router with an admin-only context preview endpoint for agent, conversation, GM, narrative, and eval context kinds. The implementation reuses existing living-world context, conversation, GM proposal, narrative artifact, and long-run eval records; validates worldline scope; redacts storage paths, media URIs, base64, raw prompt/output, and secret-like fields; and avoids provider calls, world event writes, migrations, Web dashboard work, and broad `worlds.py` routes.
- Files changed: `/backend/packages/narrative_quality/`, `/backend/services/api/src/noveland/services/api/narrative_quality.py`, `/backend/services/api/src/noveland/services/api/app.py`, `/backend/tests/test_narrative_quality_service.py`, `/backend/tests/test_api_narrative_quality.py`, `/backend/tests/test_workspace_imports.py`, `/backend/pyproject.toml`, `/backend/services/api/pyproject.toml`, `/backend/uv.lock`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`
- Tests added/updated: Narrative quality service context preview coverage, narrative quality API ACL/redaction coverage, and workspace import coverage.
- Docs updated: OpenSpec Phase 1 task status, project index, file inventory, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff, backend mypy, targeted pytest (`10 passed`), OpenSpec strict changes/spec validation, and `git diff --check`. Full local gate passed with backend ruff, backend mypy (`246 source files`), backend pytest (`321 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: Commit Phase 1 implementation, fast-forward merge to local `main`, record merge bookkeeping, then start Phase 2 Provider-backed GM Proposal from clean local `main`. Do not push unless explicitly requested.

## v0.6 Runtime Context Contract v2 merge entry

- Date: 2026-05-15
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.6 Runtime Narrative Quality Phase 1.
- Summary: Fast-forward merged `feat/runtime-context-contract-v2` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 1 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: N/A.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 2 Provider-backed GM Proposal from clean local `main`; do not push unless explicitly requested.

## v0.6 Provider-backed GM Proposal plan entry

- Date: 2026-05-15
- Branch: main
- Scope: Final implementation plan for v0.6 Runtime Narrative Quality Phase 2.
- Summary: Added the Phase 2 plan for admin-only provider-backed GM proposal generation through the dedicated narrative quality boundary. The plan confirms current provider-kernel text generation is available through fake/local-stub execution with ledger evidence, forbids legacy provider profile fallback, keeps provider output behind proposal/review/apply boundaries, and avoids world event mutation, migrations unless proven necessary, broad `worlds.py` routes, Web UI, and new external provider adapters.
- Files changed: `/docs/agent/harness/feature-updates/v0.6.2-provider-backed-gm-proposal-plan.md`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Implementation should start on `feat/provider-backed-gm-proposal` after this docs-only checkpoint is committed.

## v0.6 Provider-backed GM Proposal implementation entry

- Date: 2026-05-15
- Branch: feat/provider-backed-gm-proposal
- Scope: Backend-only v0.6 Runtime Narrative Quality Phase 2 provider-backed GM proposal generation.
- Summary: Added admin-only provider-backed GM proposal generation under the dedicated narrative quality router. The implementation confirms provider-kernel text generation through fake/local-stub `ProviderExecutionService`, writes invocation and prompt snapshot evidence, creates proposed `gm_event_proposals` only after provider execution succeeds, supports dry-run without proposal persistence, stores safe traceability in `source_context`, rejects non-text providers, and avoids world event mutation, migrations, Web UI, broad `worlds.py` routes, and legacy provider profile fallback.
- Files changed: `/backend/packages/narrative_quality/src/noveland/narrative_quality/contracts.py`, `/backend/packages/narrative_quality/src/noveland/narrative_quality/service.py`, `/backend/services/api/src/noveland/services/api/narrative_quality.py`, `/backend/tests/test_narrative_quality_service.py`, `/backend/tests/test_api_narrative_quality.py`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Narrative quality service coverage for provider-backed proposal creation, dry-run behavior, non-text provider rejection, traceability redaction, plus API coverage for creation and ACL.
- Docs updated: OpenSpec Phase 2 task status, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff, backend mypy, targeted pytest (`21 passed`), OpenSpec strict changes/spec validation, and `git diff --check`. Full local gate passed with backend ruff, backend mypy (`246 source files`), backend pytest (`327 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: Commit Phase 2 implementation, fast-forward merge to local `main`, record merge bookkeeping, then start Phase 3 Dialogue Style & OOC Review from clean local `main`. Do not push unless explicitly requested.

## v0.6 Provider-backed GM Proposal merge entry

- Date: 2026-05-15
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.6 Runtime Narrative Quality Phase 2.
- Summary: Fast-forward merged `feat/provider-backed-gm-proposal` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 2 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: N/A.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 3 Dialogue Style & OOC Review from clean local `main`; do not push unless explicitly requested.

## v0.6 Dialogue Style & OOC Review plan entry

- Date: 2026-05-15
- Branch: main
- Scope: Final implementation plan for v0.6 Runtime Narrative Quality Phase 3.
- Summary: Added the Phase 3 plan for API-first deterministic dialogue style and out-of-character review through the narrative quality boundary. The plan reuses conversation turns, agent profiles, relationships, and context helpers; avoids provider-backed review, migrations unless required, Web UI, automatic dialogue blocking, turn mutation, memory writes, world events, and broad `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.6.3-dialogue-style-ooc-review-plan.md`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Implementation should start on `feat/dialogue-style-ooc-review` after this docs-only checkpoint is committed.

## v0.6 Dialogue Style & OOC Review implementation entry

- Date: 2026-05-15
- Branch: feat/dialogue-style-ooc-review
- Scope: Backend-only v0.6 Runtime Narrative Quality Phase 3 deterministic dialogue style and OOC review.
- Summary: Added admin-only dialogue review under the narrative quality router. The implementation reviews existing conversation turns or explicit text samples, validates conversation worldline scope, compares against speaker profile and relationship context, returns structured findings and scores, redacts unsafe operational content, avoids provider calls, avoids turn mutation, avoids memory writes, avoids world events, and keeps diagnostics out of reader/member routes.
- Files changed: `/backend/packages/narrative_quality/src/noveland/narrative_quality/contracts.py`, `/backend/packages/narrative_quality/src/noveland/narrative_quality/service.py`, `/backend/services/api/src/noveland/services/api/narrative_quality.py`, `/backend/tests/test_narrative_quality_service.py`, `/backend/tests/test_api_narrative_quality.py`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Narrative quality service coverage for turn review, unsafe text redaction, cross-worldline rejection, plus API coverage for dialogue review and ACL.
- Docs updated: OpenSpec Phase 3 task status, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff, backend mypy, targeted pytest (`21 passed`), OpenSpec strict changes/spec validation, and `git diff --check`. Full local gate passed with backend ruff, backend mypy (`246 source files`), backend pytest (`332 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed` after rerun), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Flaky notes: The first full Web test run had one isolated `agent-builder.test.tsx` mock-call failure; the individual test passed immediately afterward, and the full Web test/build/e2e sequence passed on rerun.
- Follow-up notes: Commit Phase 3 implementation, fast-forward merge to local `main`, record merge bookkeeping, then start Phase 4 Emotion/Sprite/Voice Alignment from clean local `main`. Do not push unless explicitly requested.

## v0.6 Dialogue Style & OOC Review merge entry

- Date: 2026-05-15
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.6 Runtime Narrative Quality Phase 3.
- Summary: Fast-forward merged `feat/dialogue-style-ooc-review` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 3 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: N/A.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 4 Emotion/Sprite/Voice Alignment from clean local `main`; do not push unless explicitly requested.

## v0.6 Emotion/Sprite/Voice Alignment plan entry

- Date: 2026-05-15
- Branch: main
- Scope: Final implementation plan for v0.6 Runtime Narrative Quality Phase 4.
- Summary: Added the Phase 4 plan for API-first deterministic alignment diagnostics over turn presentation emotion, sprite variant, voice profile, voice binding, and speech style mapping records. The plan requires reuse of presentation, visual, and speech systems and explicitly avoids provider calls, media generation, automatic binding changes, Web UI, migrations unless required, world events, and broad `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.6.4-emotion-sprite-voice-alignment-plan.md`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Implementation should start on `feat/emotion-sprite-voice-alignment` after this docs-only checkpoint is committed.

## v0.6 Emotion/Sprite/Voice Alignment implementation entry

- Date: 2026-05-15
- Branch: feat/emotion-sprite-voice-alignment
- Scope: Backend-only v0.6 Runtime Narrative Quality Phase 4 deterministic emotion/sprite/voice alignment diagnostics.
- Summary: Added admin-only turn presentation alignment diagnostics under the narrative quality router. The implementation validates conversation and presentation worldline scope, checks emotion keys against sprite variant expressions and mood tags, checks sprite set speaker binding, checks voice profile and agent voice binding availability, checks speech style mapping availability, returns structured findings and suggested fixes, and avoids provider calls, media jobs, automatic mutations, world events, Web UI, migrations, and broad `worlds.py` routes.
- Files changed: `/backend/packages/narrative_quality/src/noveland/narrative_quality/contracts.py`, `/backend/packages/narrative_quality/src/noveland/narrative_quality/service.py`, `/backend/services/api/src/noveland/services/api/narrative_quality.py`, `/backend/tests/test_narrative_quality_service.py`, `/backend/tests/test_api_narrative_quality.py`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Narrative quality service coverage for aligned presentations, missing voice bindings, sprite/emotion mismatch, cross-worldline rejection, no event writes, plus API coverage for alignment diagnostics and ACL.
- Docs updated: OpenSpec Phase 4 task status, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff, backend mypy, targeted pytest (`27 passed`), OpenSpec strict changes/spec validation, and `git diff --check`. Full local gate passed with backend ruff, backend mypy (`246 source files`), backend pytest (`338 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: Commit Phase 4 implementation, fast-forward merge to local `main`, record merge bookkeeping, then start Phase 5 Narrative Writer v2 from clean local `main`. Do not push unless explicitly requested.

## v0.6 Emotion/Sprite/Voice Alignment merge entry

- Date: 2026-05-15
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.6 Runtime Narrative Quality Phase 4.
- Summary: Fast-forward merged `feat/emotion-sprite-voice-alignment` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 4 tasks now mark the fast-forward merge complete, and the active handoff points to Phase 5 Narrative Writer v2 planning.
- Files changed: `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 4 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 5 Narrative Writer v2 from clean local `main`; do not push unless explicitly requested.

## v0.6 Long-run Living World Simulation Eval implementation entry

- Date: 2026-05-15
- Branch: feat/long-run-living-world-simulation-eval
- Scope: Backend-only v0.6 Runtime Narrative Quality Phase 9 long-run living world simulation eval.
- Summary: Added admin-only long-run eval run/list/get APIs under the narrative quality router. The implementation reuses `LivingWorldBetaService.run_long_eval()` and `LongRunEvalRun`, returns drift metrics and failure reports, validates worldline scope, rejects sensitive metadata, redacts unsafe operational data, and avoids provider calls, daemon execution, world-event writes, Web UI, migrations, duplicate eval tables, and broad `worlds.py` routes.
- Files changed: `/backend/packages/narrative_quality/src/noveland/narrative_quality/contracts.py`, `/backend/packages/narrative_quality/src/noveland/narrative_quality/service.py`, `/backend/services/api/src/noveland/services/api/narrative_quality.py`, `/backend/tests/test_narrative_quality_service.py`, `/backend/tests/test_api_narrative_quality.py`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Narrative quality service coverage for run/list/get, worldline isolation, sensitive metadata rejection, response sanitization, and no provider/event side effects; API coverage for run/list/get, ACL, CSRF, and sensitive metadata rejection.
- Docs updated: OpenSpec Phase 9 task status, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff, backend mypy, targeted pytest (`63 passed`), OpenSpec strict changes/spec validation, and `git diff --check`. Full local gate passed with backend ruff, backend mypy (`246 source files`), backend pytest (`378 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed` after rerun), docker compose config, and `git diff --check`.
- Flaky notes: The first Web e2e run hit the existing world composition import/export response-body race; the full e2e suite passed on rerun.
- Follow-up notes: Commit Phase 9 implementation, fast-forward merge to local `main`, record merge bookkeeping, then start Phase 10 Narrative Quality Dashboard/API from clean local `main`. Do not push unless explicitly requested.

## v0.6 Long-run Living World Simulation Eval merge entry

- Date: 2026-05-15
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.6 Runtime Narrative Quality Phase 9.
- Summary: Fast-forward merged `feat/long-run-living-world-simulation-eval` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 9 tasks now mark implementation, targeted tests, full local gate, fast-forward merge, and harness update complete.
- Files changed: `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/change-journal.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/task-board.md`
- Tests added/updated: Documentation-only bookkeeping after the already-passing Phase 9 full local gate.
- Docs updated: OpenSpec tasks, change journal, task board, and active handoff.
- Follow-up notes: Start Phase 10 Narrative Quality Dashboard/API from clean local `main`; do not push unless explicitly requested.

## v0.6 Narrative Quality Dashboard/API plan entry

- Date: 2026-05-15
- Branch: main
- Scope: Final implementation plan for v0.6 Runtime Narrative Quality Phase 10.
- Summary: Added the Phase 10 plan for a read-only, admin-only narrative quality dashboard/API summary under the dedicated narrative quality boundary. The plan aggregates existing v0.6 quality signals into safe metrics, blockers, warnings, recommendations, and evidence refs while avoiding Web dashboard work, provider calls, runtime daemon execution, state mutation, migrations, world events, and broad `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.6.10-narrative-quality-dashboard-api-plan.md`, `/docs/agent/harness/**`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`
- Tests added/updated: Documentation-only planning checkpoint; verify with OpenSpec validation and `git diff --check`.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Implementation should start on `feat/narrative-quality-dashboard-api` after this docs-only checkpoint is committed. Do not push unless explicitly requested.

## v0.6 Narrative Quality Dashboard/API implementation entry

- Date: 2026-05-15
- Branch: feat/narrative-quality-dashboard-api
- Scope: Backend-only v0.6 Runtime Narrative Quality Phase 10 read-only narrative quality dashboard/API summary.
- Summary: Added an admin-scoped dashboard summary API under the narrative quality router. The implementation aggregates provider, invocation, proposal, dialogue, presentation, writer, continuity, pacing, progression, long-run eval, and world-event signals into safe blocker/warning/recommendation buckets, validates worldline scope, preserves the architecture freeze boundaries, avoids Web dashboard routes/components/e2e work, avoids provider calls and state mutation, and keeps secrets, raw prompts/outputs, storage paths, bytes, base64, and other unsafe details out of responses.
- Files changed: `/backend/packages/narrative_quality/src/noveland/narrative_quality/contracts.py`, `/backend/packages/narrative_quality/src/noveland/narrative_quality/service.py`, `/backend/services/api/src/noveland/services/api/narrative_quality.py`, `/backend/tests/test_narrative_quality_service.py`, `/backend/tests/test_api_narrative_quality.py`, `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Narrative quality service coverage for dashboard metrics, blocker sanitization, and foreign-worldline rejection; API coverage for admin ACL and foreign-worldline rejection.
- Docs updated: OpenSpec Phase 10 task status, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff, backend mypy, targeted pytest (`68 passed`), OpenSpec strict changes/spec validation, and `git diff --check`. Full local gate passed with backend ruff, backend mypy (`246 source files`), backend pytest (`383 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed` after rerun), docker compose config, and `git diff --check`.
- Flaky notes: The first Web e2e run hit the existing world composition import/export response-body race; the rerun completed cleanly.
- Follow-up notes: Fast-forward merge `feat/narrative-quality-dashboard-api` into local `main`, then update OpenSpec merge bookkeeping and keep `main` clean. Do not push unless explicitly requested.

## v0.6 Narrative Quality Dashboard/API merge entry

- Date: 2026-05-15
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.6 Runtime Narrative Quality Phase 10.
- Summary: Fast-forward merged `feat/narrative-quality-dashboard-api` into local `main` after the implementation commit and the full local gate passed. OpenSpec Phase 10 tasks now mark implementation, API-first diagnostics, package/router use, architecture guardrails, focused tests, targeted tests, and full local gate complete.
- Files changed: `/openspec/changes/v0-6-runtime-narrative-quality/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Follow-up notes: Keep `main` clean and do not push unless explicitly requested.

## v0.7 Production Hardening feasibility review entry

- Date: 2026-05-15
- Branch: main
- Scope: Documentation-only v0.7 planning review and OpenSpec optimization after v0.6 completion.
- Summary: Reviewed the active `v0-7-production-hardening` OpenSpec change against the current v0.4-v0.6 baseline. Tightened the plan around API/test/docs-first hardening, Phase 1 permission matrix and ACL regression baseline, provider secret governance, pre-call cost/rate controls, object storage integrity, deployment profile, observability reuse, consolidated security regressions, and internal readiness evidence. The updated plan avoids broad `worlds.py` growth and records stop conditions for unresolved production-hardening package/router decisions.
- Files changed: `/docs/agent/harness/feature-updates/v0.7-production-hardening-feasibility-review.md`, `/openspec/changes/v0-7-production-hardening/proposal.md`, `/openspec/changes/v0-7-production-hardening/design.md`, `/openspec/changes/v0-7-production-hardening/phase-plan.md`, `/openspec/changes/v0-7-production-hardening/tasks.md`, `/openspec/changes/v0-7-production-hardening/specs/*/spec.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: N/A, documentation-only planning update.
- Docs updated: v0.7 OpenSpec proposal, design, phase plan, task list, capability specs, feature review, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Validate OpenSpec and `git diff --check`, then commit as docs-only. Do not implement v0.7 or push unless explicitly requested.

## v0.7.5 Deployment Profile planning entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.7 Production Hardening Phase 5 planning
- Summary: Added the Phase 5 implementation checkpoint for Deployment Profile and optimized the scope to reuse existing compose, runtime health, provider health, migration, and backup verification commands. The plan remains docs/test focused and does not require a new router or managed-cloud assumptions.
- Files changed: `/docs/agent/harness/feature-updates/v0.7.5-deployment-profile-plan.md`, `/docs/agent/harness/**`, `/openspec/changes/v0-7-production-hardening/tasks.md`
- Tests added/updated: N/A
- Docs updated: project index, file inventory, task board, active handoff, OpenSpec tasks
- Follow-up notes: Implement Deployment Profile as docs-first validation work; stop if implementation would require a new router or persisted deployment state.

## v0.7 Permission Matrix & ACL Regression Baseline plan entry

- Date: 2026-05-15
- Branch: main
- Scope: Final implementation plan for v0.7 Production Hardening Phase 1.
- Summary: Added the Phase 1 plan for API/test/docs-first permission hardening over the existing v0.4-v0.6 route surface. The plan requires a route permission matrix, lower-privilege leak regression coverage, narrow ACL fixes only, and preservation of existing auth/package/router boundaries.
- Files changed: `/docs/agent/harness/feature-updates/v0.7.1-permission-matrix-acl-regression-plan.md`, `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Commit the docs-only checkpoint, then start implementation on `feat/permission-model-hardening` from clean local `main`.

## v0.7 Permission Matrix & ACL Regression Baseline implementation entry

- Date: 2026-05-15
- Branch: feat/permission-model-hardening
- Scope: v0.7 Production Hardening Phase 1 permission matrix and ACL regression baseline.
- Summary: Added a stable permission matrix for platform-admin, world-admin, world-member, reader, and player expectations. Added focused API regression coverage proving lower-privilege actors cannot access high-risk admin-only provider, invocation, authoring, multimodal eval, narrative quality, visual, speech, asset generation, or presentation surfaces, and that denial responses avoid forbidden secret/prompt/storage/raw media tokens.
- Files changed: `/docs/agent/architecture/permission-matrix.md`, `/backend/tests/test_api_permission_matrix.py`, `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: `backend/tests/test_api_permission_matrix.py`.
- Docs updated: permission matrix, OpenSpec Phase 1 task status, project index, file inventory, and change journal.
- Verification: Targeted checks passed with backend ruff, backend mypy, targeted pytest (`3 passed`), OpenSpec strict changes/spec validation, and `git diff --check`. Full local gate passed with backend ruff, backend mypy (`247 source files`), backend pytest (`386 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: Commit Phase 1 implementation, fast-forward merge to local `main`, then record merge bookkeeping.

## v0.7 Permission Matrix & ACL Regression Baseline merge entry

- Date: 2026-05-15
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.7 Production Hardening Phase 1.
- Summary: Fast-forward merged `feat/permission-model-hardening` into local `main` after targeted tests and full local gate passed. OpenSpec Phase 1 tasks now mark implementation, route matrix documentation, lower-privilege leak coverage, focused tests, targeted tests, full local gate, fast-forward merge, and harness updates complete.
- Files changed: `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 2 Secret & Provider Governance from clean local `main`.

## v0.7 Secret & Provider Governance plan entry

- Date: 2026-05-15
- Branch: main
- Scope: Final implementation plan for v0.7 Production Hardening Phase 2.
- Summary: Added the Phase 2 plan for provider governance hardening across existing provider, smoke-test, image, speech, and narrative quality execution boundaries. The plan requires disabled providers to be blocked before external calls, `auth_ref` rotation to remain opaque, safe health/invocation/diagnostic evidence only, and no vault/KMS, marketplace, Web UI, or broad `worlds.py` growth.
- Files changed: `/docs/agent/harness/feature-updates/v0.7.2-secret-provider-governance-plan.md`, `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Commit the docs-only checkpoint, then start implementation on `feat/secret-provider-governance` from clean local `main`.

## v0.7 Secret & Provider Governance implementation entry

- Date: 2026-05-15
- Branch: feat/secret-provider-governance
- Scope: v0.7 Production Hardening Phase 2 provider secret and disabled-provider governance.
- Summary: Hardened provider execution so non-active providers write safe failed invocation/snapshot evidence and stop before adapter execution or secret resolution. Smoke tests, health checks, image generation, speech TTS, and narrative quality provider-backed generation now have focused regressions for disabled-provider blocking. Auth reference rotation remains an opaque reference and secret-like update payloads continue to be rejected.
- Files changed: `/backend/packages/providers/src/noveland/providers/service.py`, `/backend/packages/providers/src/noveland/providers/health.py`, `/backend/packages/providers/src/noveland/providers/registry.py`, `/backend/tests/test_provider_execution_service.py`, `/backend/tests/test_api_providers.py`, `/backend/tests/test_image_service.py`, `/backend/tests/test_speech_service.py`, `/backend/tests/test_narrative_quality_service.py`, `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Disabled provider execution coverage for direct provider execution, smoke/health API, image service, speech service, and narrative quality service; provider API auth_ref rotation regression.
- Docs updated: OpenSpec Phase 2 task status, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff, backend mypy, targeted pytest (`70 passed`), OpenSpec strict changes/spec validation, and `git diff --check`. Full local gate passed with backend ruff, backend mypy (`247 source files`), backend pytest (`391 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: Commit Phase 2 implementation, fast-forward merge to local `main`, then record merge bookkeeping.

## v0.7 Secret & Provider Governance merge entry

- Date: 2026-05-15
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.7 Production Hardening Phase 2.
- Summary: Fast-forward merged `feat/secret-provider-governance` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 2 tasks now mark implementation, disabled provider blocking, auth_ref rotation coverage, architecture guardrails, focused tests, targeted tests, full local gate, fast-forward merge, and harness updates complete.
- Files changed: `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 3 Cost & Rate Control from clean local `main`.

## v0.7 Cost & Rate Control plan entry

- Date: 2026-05-15
- Branch: main
- Scope: Final implementation plan for v0.7 Production Hardening Phase 3.
- Summary: Added the Phase 3 plan for provider-owned budget/rate controls covering world/provider limits, emergency stop, safe quota status, pre-call provider execution blocking, media job failure marking for blocked executions, and reuse of existing asset generation proposal budgets. The plan keeps implementation inside the existing providers boundary and explicitly avoids a new production-hardening router, Web UI, billing marketplace, provider fallback, or broad `worlds.py` growth.
- Files changed: `/docs/agent/harness/feature-updates/v0.7.3-cost-rate-control-plan.md`, `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Commit the docs-only checkpoint, then start implementation on `feat/cost-rate-control` from clean local `main`.

## v0.7 Cost & Rate Control implementation entry

- Date: 2026-05-15
- Branch: feat/cost-rate-control
- Scope: v0.7 Production Hardening Phase 3 provider-owned cost/rate control.
- Summary: Added provider budget policy persistence, admin-only budget policy/quota APIs under the providers router, and a provider execution budget guard that runs before secret resolution and adapter execution. Emergency stop and daily invocation/cost/media-job limits produce safe failed invocation/snapshot evidence, blocked media-backed executions mark non-terminal media jobs failed, and existing asset-generation proposal budget behavior remains in place.
- Files changed: `/backend/packages/providers/src/noveland/providers/budget.py`, `/backend/packages/providers/src/noveland/providers/contracts.py`, `/backend/packages/providers/src/noveland/providers/models.py`, `/backend/packages/providers/src/noveland/providers/service.py`, `/backend/services/api/src/noveland/services/api/providers.py`, `/backend/migrations/versions/20260515_0042_provider_budget_policies.py`, provider/image/speech/narrative quality/API/schema tests, `/web/tests/e2e/auth.spec.ts`, `/openspec/changes/v0-7-production-hardening/tasks.md`, and harness docs.
- Tests added/updated: Direct provider execution emergency stop and daily invocation limit tests; provider budget API smoke/quota test; image, speech, and narrative quality budget block regressions; alembic head update.
- Docs updated: OpenSpec Phase 3 task status, project index, file inventory, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff, backend mypy, targeted pytest (`109 passed`), and `git diff --check`. Full local gate passed with backend ruff, backend mypy (`248 source files`), backend pytest (`397 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed` after stabilizing the import/export response-body assertion), docker compose config, and `git diff --check`.
- Flaky note: one e2e run hit a transient unauthenticated reader redirect 404 during Next dev dynamic route cold start; the isolated test and subsequent full e2e run passed.
- Follow-up notes: Commit Phase 3 implementation, fast-forward merge to local `main`, then record merge bookkeeping.

## v0.7 Cost & Rate Control merge entry

- Date: 2026-05-15
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.7 Production Hardening Phase 3.
- Summary: Fast-forward merged `feat/cost-rate-control` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 3 tasks now mark implementation, budget/quota definition, pre-call blocking, architecture guardrails, focused tests, targeted tests, full local gate, fast-forward merge, and harness updates complete.
- Files changed: `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 4 Object Storage & Backup v2 from clean local `main`.

## v0.7 Object Storage & Backup v2 plan entry

- Date: 2026-05-15
- Branch: main
- Scope: Final implementation plan for v0.7 Production Hardening Phase 4.
- Summary: Added the Phase 4 plan for safe storage integrity auditing and repeatable backup/restore verification. The plan keeps work inside existing storage/media/operator boundaries, expects no migration, avoids S3/GCS implementation, avoids Web UI and public media delivery, and requires audit output to omit raw storage URIs, filesystem paths, bytes, base64, raw prompts, and raw outputs.
- Files changed: `/docs/agent/harness/feature-updates/v0.7.4-object-storage-backup-v2-plan.md`, `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Commit the docs-only checkpoint, then start implementation on `feat/object-storage-backup-v2` from clean local `main`.

## v0.7 Object Storage & Backup v2 implementation entry

- Date: 2026-05-15
- Branch: feat/object-storage-backup-v2
- Scope: v0.7 Production Hardening Phase 4 safe object storage and backup verification.
- Summary: Added `noveland.storage.integrity` for read-only storage integrity auditing across `media_objects` and object-backed `world_snapshots`. Added a platform-admin-only `/runtime/storage-audit` endpoint that returns safe counts and finding refs without raw storage URIs, filesystem paths, bytes, base64, raw prompts, or raw outputs. Updated the backup/restore playbook to include storage audit verification before backup and after restore.
- Files changed: `/backend/packages/storage/src/noveland/storage/integrity.py`, `/backend/packages/storage/src/noveland/storage/__init__.py`, `/backend/services/api/src/noveland/services/api/runtime.py`, `/backend/tests/test_storage_integrity_service.py`, `/backend/tests/test_api_runtime.py`, `/docs/agent/operations/backup-restore.md`, `/openspec/changes/v0-7-production-hardening/tasks.md`, and harness docs.
- Tests added/updated: Storage integrity service tests for matching media/snapshot payloads, missing media object, size mismatch, checksum mismatch, missing snapshot payload, and safe output; runtime API coverage for platform-admin storage audit.
- Docs updated: backup/restore playbook, OpenSpec Phase 4 task status, project index, file inventory, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff, backend mypy, targeted pytest (`38 passed`), OpenSpec strict changes/spec validation, and `git diff --check`. Full local gate passed with backend ruff, backend mypy (`250 source files`), backend pytest (`401 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: Commit Phase 4 implementation, fast-forward merge to local `main`, then record merge bookkeeping.

## v0.7 Object Storage & Backup v2 merge entry

- Date: 2026-05-15
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.7 Production Hardening Phase 4.
- Summary: Fast-forward merged `feat/object-storage-backup-v2` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 4 tasks now mark implementation, storage integrity auditing, backup/restore docs, architecture guardrails, focused tests, targeted tests, full local gate, fast-forward merge, and harness updates complete.
- Files changed: `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 5 Deployment Profile from clean local `main`.

## v0.7 Deployment Profile implementation entry

- Date: 2026-05-15
- Branch: feat/deployment-profile
- Scope: v0.7 Production Hardening Phase 5 deployment profile.
- Summary: Expanded the local/single-host deployment profile into a complete operator guide covering supported components, configuration refs, startup order, health checks, migration procedure, rollback prerequisites, and explicit non-goals. Added a lightweight docs regression test that keeps the deployment profile tied to existing compose, health, migration, backup, and runtime validation commands without adding runtime behavior.
- Files changed: `/docs/agent/operations/deployment-profile.md`, `/backend/tests/test_deployment_profile_docs.py`, `/docs/agent/harness/file-inventory.md`, `/openspec/changes/v0-7-production-hardening/tasks.md`, and harness docs.
- Tests added/updated: `backend/tests/test_deployment_profile_docs.py`.
- Docs updated: deployment profile, OpenSpec Phase 5 task status, file inventory, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff, backend mypy, targeted pytest (`13 passed`), OpenSpec strict changes/spec validation, and `git diff --check`. Full local gate passed with backend ruff, backend mypy (`251 source files`), backend pytest (`404 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: Commit Phase 5 implementation status, fast-forward merge to local `main`, then record merge bookkeeping.

## v0.7 Deployment Profile merge entry

- Date: 2026-05-15
- Branch: main
- Scope: Fast-forward merge bookkeeping for v0.7 Production Hardening Phase 5.
- Summary: Fast-forward merged `feat/deployment-profile` into local `main` after targeted tests and the full local gate passed. OpenSpec Phase 5 tasks now mark implementation, deployment documentation, local validation, architecture guardrails, focused tests, targeted tests, full local gate, fast-forward merge, and harness updates complete.
- Files changed: `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 6 Observability & Incident Diagnostics from clean local `main`.

## v0.7.6 Observability & Incident Diagnostics planning entry

- Date: 2026-05-15
- Branch: main
- Scope: Final implementation plan for v0.7 Production Hardening Phase 6.
- Summary: Added the Phase 6 plan for safe incident diagnostics over existing runtime diagnostics, provider health, model invocation, media job, multimodal eval, budget, and narrative quality evidence. The plan uses `noveland.observability` as the owning package, permits a bounded platform-admin observability router if an API is needed, and explicitly avoids raw prompt/output replay, public incident routes, duplicate diagnostics frameworks, and broad `worlds.py` or runtime route growth.
- Files changed: `/docs/agent/harness/feature-updates/v0.7.6-observability-incident-diagnostics-plan.md`, `/openspec/changes/v0-7-production-hardening/tasks.md`, `/openspec/changes/v0-7-production-hardening/phase-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list, phase plan, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Commit the docs-only checkpoint, then start implementation on `feat/observability-incident-diagnostics` from clean local `main`.

## v0.7.6 Observability & Incident Diagnostics implementation entry

- Date: 2026-05-15
- Branch: feat/observability-incident-diagnostics
- Scope: v0.7 Production Hardening Phase 6 implementation
- Summary: Added a safe incident diagnostics aggregation service under `noveland.observability`, a dedicated platform-admin-only `/observability/incidents/summary` router, and regression coverage that verifies the summary only returns counts, statuses, timestamps, and evidence refs while omitting raw prompts, outputs, storage paths, and secret material.
- Files changed: `/backend/packages/observability/**`, `/backend/services/api/src/noveland/services/api/observability.py`, `/backend/services/api/src/noveland/services/api/app.py`, `/backend/tests/test_observability_incidents.py`, `/docs/agent/harness/{file-inventory,project-index,task-board,handoffs/active-session,change-journal}.md`, `/backend/packages/observability/pyproject.toml`, `/backend/packages/observability/src/noveland/observability/{contracts,services,__init__}.py`
- Tests added/updated: incident summary service/API regression tests for safe evidence aggregation, platform-admin ACL, world filter behavior, and redaction boundaries.
- Docs updated: file inventory, project index, task board, active handoff, and change journal.
- Follow-up notes: Run the full local gate, then fast-forward merge Phase 6 back to local `main` if it stays green.

## v0.7.6 Observability & Incident Diagnostics gate entry

- Date: 2026-05-15
- Branch: feat/observability-incident-diagnostics
- Scope: v0.7 Production Hardening Phase 6 full local gate
- Summary: Recorded the successful full local gate for Phase 6 after the incident diagnostics implementation.
- Files changed: `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, gate bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Follow-up notes: Fast-forward merge `feat/observability-incident-diagnostics` to local `main`, then record merge bookkeeping before starting Phase 7.

## v0.7.6 Observability & Incident Diagnostics merge entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.7 Production Hardening Phase 6 merge bookkeeping
- Summary: Fast-forward merged `feat/observability-incident-diagnostics` into local `main`, marked Phase 6 complete in OpenSpec tasks, and moved harness handoff state to Phase 7 Security Regression Suite planning.
- Files changed: `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 7 from clean local `main`; do not push unless explicitly requested.

## v0.7.7 Security Regression Suite planning entry

- Date: 2026-05-15
- Branch: main
- Scope: Final implementation plan for v0.7 Production Hardening Phase 7.
- Summary: Added the Phase 7 plan for a backend test-focused security regression suite covering forbidden payload leaks, ACL matrix behavior, and cross-worldline isolation across v0.4-v0.7 surfaces. The plan keeps Phase 7 test-only unless regressions expose narrow bugs, and explicitly avoids migrations, new routers, Web UI, SAST/DAST rollout, and broad `worlds.py` refactors.
- Files changed: `/docs/agent/harness/feature-updates/v0.7.7-security-regression-suite-plan.md`, `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Start implementation on `feat/security-regression-suite` from clean local `main`.

## v0.7.7 Security Regression Suite implementation entry

- Date: 2026-05-15
- Branch: feat/security-regression-suite
- Scope: v0.7 Production Hardening Phase 7 security regression suite.
- Summary: Added a consolidated backend regression suite and shared fixture helpers for forbidden secret, prompt/output, storage/path, ACL, and worldline isolation markers across v0.4-v0.7 surfaces. The suite reuses existing permission, provider secret, multimodal sample-world, authoring import, narrative quality, and observability coverage without adding migrations, routers, providers, Web UI, runtime behavior, or broad `worlds.py` changes.
- Files changed: `/backend/tests/fixtures/security_regression.py`, `/backend/tests/test_security_regression_suite.py`, `/openspec/changes/v0-7-production-hardening/tasks.md`, and harness docs.
- Tests added/updated: `backend/tests/test_security_regression_suite.py` and `backend/tests/fixtures/security_regression.py`.
- Docs updated: OpenSpec task status, file inventory, project index, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff for the security regression tests/helpers, backend mypy for the same files, and targeted pytest (`83 passed`).
- Follow-up notes: Run the full local gate, then fast-forward merge Phase 7 back to local `main` if it stays green.

## v0.7.7 Security Regression Suite gate entry

- Date: 2026-05-15
- Branch: feat/security-regression-suite
- Scope: v0.7 Production Hardening Phase 7 full local gate.
- Summary: Recorded the successful full local gate for the security regression suite after the test-only implementation.
- Files changed: `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, gate bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Verification: Full local gate passed with backend ruff, backend mypy (`255 source files`), backend pytest (`411 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: Fast-forward merge `feat/security-regression-suite` to local `main`, then record merge bookkeeping before starting Phase 8.

## v0.7.7 Security Regression Suite merge entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.7 Production Hardening Phase 7 merge bookkeeping.
- Summary: Fast-forward merged `feat/security-regression-suite` into local `main`, marked Phase 7 complete in OpenSpec tasks, and moved harness handoff state to Phase 8 Production Readiness Gate planning.
- Files changed: `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 8 from clean local `main`; do not push unless explicitly requested.

## v0.7.8 Production Readiness Gate planning entry

- Date: 2026-05-15
- Branch: main
- Scope: Final implementation plan for v0.7 Production Hardening Phase 8.
- Summary: Added the Phase 8 plan for a read-only, platform-admin internal production-readiness gate under the existing `noveland.observability` boundary. The plan aggregates existing beta checklist, long-run eval, release profile, provider, budget, storage, runtime diagnostics, incident, multimodal eval, narrative quality, and security regression evidence without adding a duplicate release framework, new schema, public launch semantics, Web UI, or broad `worlds.py`/`runtime.py` route growth.
- Files changed: `/docs/agent/harness/feature-updates/v0.7.8-production-readiness-gate-plan.md`, `/openspec/changes/v0-7-production-hardening/tasks.md`, `/openspec/changes/v0-7-production-hardening/phase-plan.md`, `/docs/agent/harness/project-index.md`, `/docs/agent/harness/file-inventory.md`, `/docs/agent/harness/task-board.md`, `/docs/agent/harness/handoffs/active-session.md`, `/docs/agent/harness/change-journal.md`
- Tests added/updated: Documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list, phase plan, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Commit the docs-only checkpoint, then start implementation on `feat/production-readiness-gate` from clean local `main`.

## v0.7.8 Production Readiness Gate implementation entry

- Date: 2026-05-15
- Branch: feat/production-readiness-gate
- Scope: v0.7 Production Hardening Phase 8 production-readiness aggregation.
- Summary: Added a read-only internal production-readiness report under `noveland.observability`, exposed it through the platform-admin-only `/observability/readiness/production` endpoint, and added regression coverage for safe aggregation, blockers, ACL, redaction, and no duplicate release/eval/readiness persistence framework. The implementation reuses beta checklist, long-run eval, release profile, provider health, budget policy, storage integrity, incident diagnostics, multimodal eval, narrative quality, and security regression evidence without migrations, Web UI, daemon execution, public launch semantics, or broad `worlds.py` growth.
- Files changed: `/backend/packages/observability/src/noveland/observability/{contracts,services,__init__}.py`, `/backend/services/api/src/noveland/services/api/observability.py`, `/backend/tests/test_production_readiness_gate.py`, `/openspec/changes/v0-7-production-hardening/tasks.md`, and harness docs.
- Tests added/updated: `backend/tests/test_production_readiness_gate.py`.
- Docs updated: OpenSpec task status, file inventory, project index, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff for observability readiness code/API/tests, backend mypy for the same files, and targeted pytest (`14 passed`).
- Follow-up notes: Run the full local gate, then fast-forward merge Phase 8 back to local `main` if it stays green.

## v0.7.8 Production Readiness Gate gate entry

- Date: 2026-05-15
- Branch: feat/production-readiness-gate
- Scope: v0.7 Production Hardening Phase 8 full local gate.
- Summary: Recorded the successful full local gate for the internal production-readiness aggregation implementation.
- Files changed: `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, gate bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Verification: Full local gate passed with backend ruff, backend mypy (`256 source files`), backend pytest (`415 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Follow-up notes: Fast-forward merge `feat/production-readiness-gate` to local `main`, then record merge bookkeeping to complete v0.7.

## v0.7.8 Production Readiness Gate merge entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.7 Production Hardening Phase 8 merge bookkeeping.
- Summary: Fast-forward merged `feat/production-readiness-gate` into local `main`, marked Phase 8 complete in OpenSpec tasks, and recorded v0.7 Production Hardening as locally complete.
- Files changed: `/openspec/changes/v0-7-production-hardening/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Follow-up notes: v0.7 is ready for archive/release notes if requested. Do not push unless explicitly requested.

## v0.8 Public Experience & Ecosystem feasibility review entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.7 final acceptance confirmation and v0.8 OpenSpec plan adaptation
- Summary: Confirmed the completed v0.7 Production Hardening local acceptance state, reviewed the proposed v0.8 roadmap against current main, and updated the v0.8 OpenSpec proposal, design, phase plan, tasks, and capability specs to require reader-safe API/media contracts before UI and public launch work.
- Files changed: `/docs/agent/harness/feature-updates/v0.8-public-experience-ecosystem-feasibility-review.md`, `/openspec/changes/v0-8-public-experience-ecosystem/**`, `/docs/agent/harness/**`
- Tests added/updated: N/A, documentation and OpenSpec planning only.
- Docs updated: v0.8 feasibility review, OpenSpec v0.8 change docs/specs, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Archive v0.7 and generate release notes only if requested. Start v0.8 implementation with Phase 1 Reader Media Delivery after resolving the reader media auth/delivery model.

## v0.8.1 Reader Media Delivery planning entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 1 planning
- Summary: Added the Phase 1 reader media delivery checkpoint, confirming authenticated-only application-mediated delivery, dedicated reader delivery package/router boundaries, current admin media/narrative reader route inventory, no migration expectation, and safe descriptor/download visibility policy.
- Files changed: `/docs/agent/harness/feature-updates/v0.8.1-reader-media-delivery-plan.md`, `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A, documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Implement Phase 1 on a feature branch. Do not reuse admin media routes, do not add unauthenticated delivery, and stop if implementation needs a migration or broad `worlds.py` route growth.

## v0.8.1 Reader Media Delivery implementation entry

- Date: 2026-05-15
- Branch: feat/reader-media-delivery
- Scope: v0.8 Public Experience & Ecosystem Phase 1 reader-safe media delivery.
- Summary: Added the dedicated `noveland.reader_delivery` package and app-level `reader_media.py` router for authenticated reader/member/player/admin media descriptors and application-mediated media object download. The service reuses the existing media kernel, requires available reader/player/member-visible media, suppresses hidden/private/developer-only assets, requires reader-visible media references, and keeps storage URIs, paths, base64, raw prompts/outputs, and secrets out of reader responses.
- Files changed: `/backend/packages/reader_delivery/`, `/backend/services/api/src/noveland/services/api/reader_media.py`, `/backend/services/api/src/noveland/services/api/app.py`, backend workspace metadata, `/backend/tests/test_api_reader_media.py`, OpenSpec tasks, and harness docs.
- Tests added/updated: `backend/tests/test_api_reader_media.py`.
- Docs updated: OpenSpec task status, file inventory, project index, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff for reader delivery/API/tests, backend mypy for the same files, and targeted pytest (`5 passed`).
- Follow-up notes: Run the full local gate, then fast-forward merge Phase 1 back to local `main` if it stays green.

## v0.8.1 Reader Media Delivery gate entry

- Date: 2026-05-15
- Branch: feat/reader-media-delivery
- Scope: v0.8 Public Experience & Ecosystem Phase 1 full local gate.
- Summary: Recorded the successful full local gate for the authenticated reader media delivery implementation.
- Files changed: `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, gate bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Verification: Full local gate passed with backend ruff, backend mypy (`261 source files`), backend pytest (`420 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, OpenSpec strict changes/spec validation, and `git diff --check`.
- Follow-up notes: Fast-forward merge `feat/reader-media-delivery` to local `main`, then record merge bookkeeping before starting Phase 2.

## v0.8.1 Reader Media Delivery merge entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 1 merge bookkeeping.
- Summary: Fast-forward merged `feat/reader-media-delivery` into local `main`, marked Phase 1 complete in OpenSpec tasks, and moved harness handoff state to Phase 2 Conversation Playback UI planning.
- Files changed: `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 2 from clean local `main`; use the `impeccable` skill before frontend implementation, and continue using reader-safe media descriptors only.

## v0.8.2 Conversation Playback UI planning entry

- Date: 2026-05-15
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 2 planning.
- Summary: Added the Phase 2 checkpoint for a reader/player-facing conversation playback surface that consumes existing conversation turns, optional turn presentations, and Phase 1 reader media descriptors. The plan keeps this phase Web-focused, avoids migrations and provider execution, and preserves the no admin media DTO/no storage path/no raw prompt-output boundary.
- Files changed: `/docs/agent/harness/feature-updates/v0.8.2-conversation-playback-ui-plan.md`, `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A, documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Implement Phase 2 on `feat/conversation-playback-ui`; use `impeccable` context for the Web UI and reader-safe media descriptor DTOs for playback assets.

## v0.8.2 Conversation Playback UI implementation entry

- Date: 2026-05-15
- Branch: feat/conversation-playback-ui
- Scope: v0.8 Public Experience & Ecosystem Phase 2 reader/player playback UI.
- Summary: Added an authenticated reader playback route under the reader surface, a `ConversationPlayback` component, reader media Web DTO helpers, playback data loading over existing conversation turns/presentations and Phase 1 reader media descriptors, and mock/e2e fixtures for safe image/audio delivery. The UI renders turn text, local playback state, render/emotion metadata, reader-safe image/audio references, and deterministic missing-media fallbacks without exposing admin media DTOs, storage paths, raw prompts/outputs, or secrets.
- Files changed: `/web/app/worlds/[worldId]/reader/conversations/[conversationId]/playback/page.tsx`, `/web/features/worlds/conversation-playback.tsx`, `/web/features/worlds/conversation-playback.test.tsx`, `/web/lib/worlds/{media,server}.ts`, `/web/lib/worlds/types.ts`, `/web/tests/e2e/{auth.spec.ts,start-with-mock-auth.mjs}`, Web CSS, OpenSpec tasks, and harness docs.
- Tests added/updated: `web/features/worlds/conversation-playback.test.tsx`, `web/lib/worlds/media.test.ts`, and playback coverage in `web/tests/e2e/auth.spec.ts`.
- Docs updated: OpenSpec task status, project index, file inventory, task board, active handoff, and change journal.
- Verification: Targeted checks passed with Web lint, Web typecheck, focused Vitest (`2 passed files, 7 passed tests`), focused playback e2e (`1 passed` after selector tightening), OpenSpec strict changes/spec validation, and `git diff --check`.
- Follow-up notes: Run the full local gate, then fast-forward merge Phase 2 back to local `main` if it stays green.

## v0.8.2 Conversation Playback UI gate entry

- Date: 2026-05-16
- Branch: feat/conversation-playback-ui
- Scope: v0.8 Public Experience & Ecosystem Phase 2 full local gate.
- Summary: Fixed the Phase 2 playback e2e blocker by clearing stale Next dev CSS cache before the mock-auth e2e server starts, so the active reader-safe scene media renders visibly in the playback surface.
- Files changed: `/web/tests/e2e/start-with-mock-auth.mjs`, `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, blocker fix and gate bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Verification: Focused playback e2e passed, full Web e2e passed (`14 passed`), and the full local gate passed with backend ruff, backend mypy (`261 source files`), backend pytest (`420 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`36 passed`, `115 passed`), Web build, Web `check:next-env`, Web e2e (`14 passed`), docker compose config, OpenSpec strict changes/spec validation, and `git diff --check`.
- Follow-up notes: Fast-forward merge `feat/conversation-playback-ui` to local `main`, then record merge bookkeeping before starting Phase 3.

## v0.8.2 Conversation Playback UI merge entry

- Date: 2026-05-16
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 2 merge bookkeeping.
- Summary: Fast-forward merged `feat/conversation-playback-ui` into local `main`, marked Phase 2 complete in OpenSpec tasks, and moved harness handoff state to Phase 3 Player Interaction UI planning.
- Files changed: `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 3 from clean local `main`; use the `impeccable` skill before frontend implementation, and reuse existing player choice, intervention, journal, and notification records.

## v0.8.3 Player Interaction UI planning entry

- Date: 2026-05-16
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 3 planning.
- Summary: Added the Phase 3 checkpoint for a player/member-facing interaction surface that reuses existing player choices, interventions, journal entries, notifications, and safe route feedback records without creating a replacement player state model.
- Files changed: `/docs/agent/harness/feature-updates/v0.8.3-player-interaction-ui-plan.md`, `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A, documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Follow-up notes: Implement Phase 3 on a feature branch. Journal, notifications, and interventions are already member-facing; player choice endpoints may need a narrow existing-route ACL adjustment, not broad new `worlds.py` routes.

## v0.8.3 Player Interaction UI implementation entry

- Date: 2026-05-16
- Branch: feat/player-interaction-ui
- Scope: v0.8 Public Experience & Ecosystem Phase 3 player/member interaction UI.
- Summary: Added an authenticated player surface at `/worlds/{world_id}/player`, a `PlayerInteractions` component, server-side player interaction data loading, a workspace Player nav entry, and mock/e2e fixtures for player-owned choices, interventions, journal entries, and notifications. Backend changes are limited to existing player actor and player choice route ACLs/current-user filtering plus safer choice/intervention world event payload summaries.
- Files changed: `/web/app/worlds/[worldId]/player/page.tsx`, `/web/features/worlds/player-interactions.tsx`, `/web/features/worlds/player-interactions.test.tsx`, `/web/lib/worlds/{client,server}.ts`, `/web/features/workspace/workspace-shell.tsx`, Web CSS, `/web/tests/e2e/{auth.spec.ts,start-with-mock-auth.mjs}`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/packages/worlds/src/noveland/worlds/{gm,guardrails}.py`, `/backend/tests/test_api_worlds.py`, OpenSpec tasks, and harness docs.
- Tests added/updated: `web/features/worlds/player-interactions.test.tsx`, player interaction coverage in `web/tests/e2e/auth.spec.ts`, and `test_world_member_can_use_own_player_interaction_records_without_admin_scope` in `backend/tests/test_api_worlds.py`.
- Docs updated: OpenSpec task status, project index, file inventory, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend pytest for the player interaction API/ACL regression, focused Web component tests, Web typecheck, Web lint, focused player interaction e2e, targeted backend ruff for changed Phase 3 backend files, and `git diff --check`.
- Follow-up notes: Run the full local gate, then fast-forward merge Phase 3 back to local `main` if it stays green.

## v0.8.3 Player Interaction UI gate entry

- Date: 2026-05-16
- Branch: feat/player-interaction-ui
- Scope: v0.8 Public Experience & Ecosystem Phase 3 full local gate.
- Summary: Recorded the successful full local gate for the authenticated player interaction UI and member-owned existing player record workflow.
- Files changed: `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, gate bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Verification: Full local gate passed with backend ruff, backend mypy (`261 source files`), backend pytest (`421 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`37 passed files`, `118 passed`), Web build, Web `check:next-env`, Web e2e (`16 passed`), docker compose config, OpenSpec strict changes/spec validation, OpenSpec strict specs validation, and `git diff --check`.
- Follow-up notes: Commit Phase 3 implementation, fast-forward merge `feat/player-interaction-ui` to local `main`, then record merge bookkeeping before starting Phase 4.

## v0.8.3 Player Interaction UI merge entry

- Date: 2026-05-16
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 3 merge bookkeeping.
- Summary: Fast-forward merged `feat/player-interaction-ui` into local `main`, marked Phase 3 complete in OpenSpec tasks, and moved harness handoff state to Phase 4 Worldline Browser planning.
- Files changed: `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 4 from clean local `main`; use the `impeccable` skill before frontend implementation, and keep worldline browsing read-only.

## v0.8.4 Worldline Browser planning entry

- Date: 2026-05-16
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 4 planning.
- Summary: Added the Phase 4 checkpoint for an authenticated read-only worldline browser that reuses existing worldline list and comparison DTOs, keeps fork/rollback/merge/switching out of reader/player UI, and limits comparison output to safe aggregate counts.
- Files changed: `/docs/agent/harness/feature-updates/v0.8.4-worldline-browser-plan.md`, `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A, documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Verification: OpenSpec strict changes validation and `git diff --check`.
- Follow-up notes: Implement Phase 4 on a feature branch. A narrow member-safe worldline compare ACL adjustment is acceptable if required, but no destructive worldline operations or raw event payload display are in scope.

## v0.8.4 Worldline Browser implementation entry

- Date: 2026-05-16
- Branch: feat/worldline-browser
- Scope: v0.8 Public Experience & Ecosystem Phase 4 read-only worldline browser.
- Summary: Added an authenticated `/worlds/{world_id}/worldlines` route, a `WorldlineBrowser` component, server-side worldline browser data loading, a workspace Worldlines nav link, and mock/e2e fixtures for branch comparison. Backend changes are limited to making the existing safe aggregate worldline compare GET member-readable while keeping fork creation admin-only.
- Files changed: `/web/app/worlds/[worldId]/worldlines/page.tsx`, `/web/features/worlds/worldline-browser.tsx`, `/web/features/worlds/worldline-browser.test.tsx`, `/web/lib/worlds/server.ts`, `/web/features/workspace/workspace-shell.tsx`, Web CSS, `/web/tests/e2e/{auth.spec.ts,start-with-mock-auth.mjs}`, `/backend/services/api/src/noveland/services/api/worlds.py`, `/backend/tests/test_api_worlds.py`, OpenSpec tasks, and harness docs.
- Tests added/updated: `web/features/worlds/worldline-browser.test.tsx`, worldline browser coverage in `web/tests/e2e/auth.spec.ts`, and `test_world_member_can_read_safe_worldline_comparison_without_mutation` in `backend/tests/test_api_worlds.py`.
- Docs updated: OpenSpec task status, project index, file inventory, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff and mypy for changed worldline API/test files, focused backend pytest for member-safe comparison, focused Web component tests, Web lint, Web typecheck, focused worldline browser e2e, and `git diff --check`.
- Follow-up notes: Run the full local gate, then fast-forward merge Phase 4 back to local `main` if it stays green.

## v0.8.4 Worldline Browser gate entry

- Date: 2026-05-16
- Branch: feat/worldline-browser
- Scope: v0.8 Public Experience & Ecosystem Phase 4 full local gate.
- Summary: Recorded the successful full local gate for the authenticated read-only worldline browser and member-safe aggregate comparison workflow.
- Files changed: `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, gate bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Verification: Full local gate passed with backend ruff, backend mypy (`261 source files`), backend pytest (`422 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`38 passed files`, `121 passed`), Web build, Web `check:next-env`, Web e2e (`18 passed`), docker compose config, OpenSpec strict changes/spec validation, OpenSpec strict specs validation, and `git diff --check`.
- Follow-up notes: Commit Phase 4 implementation, fast-forward merge `feat/worldline-browser` to local `main`, then record merge bookkeeping before starting Phase 5.

## v0.8.4 Worldline Browser merge entry

- Date: 2026-05-16
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 4 merge bookkeeping.
- Summary: Fast-forward merged `feat/worldline-browser` into local `main`, marked Phase 4 complete in OpenSpec tasks, and moved harness handoff state to Phase 5 Scene View / Galgame View planning.
- Files changed: `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 5 from clean local `main`; use the `impeccable` skill before frontend implementation, and keep scene view on reader-safe media descriptors only.

## v0.8.5 Scene View / Galgame View planning entry

- Date: 2026-05-16
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 5 planning.
- Summary: Added the Phase 5 checkpoint for an authenticated reader/player scene view that reuses Phase 2 playback data and Phase 1 reader-safe media descriptors to render one active turn with image, dialogue, and optional audio without adding a game engine or second media path.
- Files changed: `/docs/agent/harness/feature-updates/v0.8.5-scene-view-galgame-view-plan.md`, `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A, documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Verification: OpenSpec strict changes validation and `git diff --check`.
- Follow-up notes: Implement Phase 5 on a feature branch. Reuse reader-safe media descriptors only; no direct admin media DTOs, public unauthenticated access, or full game engine scope.

## v0.8.5 Scene View / Galgame View implementation entry

- Date: 2026-05-16
- Branch: feat/scene-view-galgame
- Scope: v0.8 Public Experience & Ecosystem Phase 5 reader/player scene view.
- Summary: Added an authenticated scene route at `/worlds/{world_id}/reader/conversations/{conversation_id}/scene`, a `ConversationSceneView` component, shared `playback-media` helpers reused by playback and scene view, a playback-to-scene link, scene-stage CSS, and e2e coverage for safe media, dialogue, audio, and deterministic missing-media fallbacks.
- Files changed: `/web/app/worlds/[worldId]/reader/conversations/[conversationId]/scene/page.tsx`, `/web/features/worlds/{conversation-scene-view,conversation-scene-view.test}.tsx`, `/web/features/worlds/playback-media.ts`, `/web/features/worlds/conversation-playback.tsx`, Web CSS, `/web/tests/e2e/auth.spec.ts`, OpenSpec tasks, and harness docs.
- Tests added/updated: `web/features/worlds/conversation-scene-view.test.tsx`, scene view coverage in `web/tests/e2e/auth.spec.ts`, and playback component coverage for the scene-view link through the shared media helper refactor.
- Docs updated: OpenSpec task status, project index, file inventory, task board, active handoff, and change journal.
- Verification: Targeted checks passed with focused Web component tests for scene view and playback, focused scene view e2e, Web lint, Web typecheck, OpenSpec strict changes validation, and `git diff --check`.
- Follow-up notes: Run the full local gate, then fast-forward merge Phase 5 back to local `main` if it stays green.

## v0.8.5 Scene View / Galgame View gate entry

- Date: 2026-05-16
- Branch: feat/scene-view-galgame
- Scope: v0.8 Public Experience & Ecosystem Phase 5 full local gate.
- Summary: Recorded the successful full local gate for the reader/player scene view and shared reader-safe playback media resolution.
- Files changed: `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, gate bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Verification: Full local gate passed with backend ruff, backend mypy (`261 source files`), backend pytest (`422 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`39 passed files`, `124 passed`), Web build, Web `check:next-env`, Web e2e (`19 passed`), docker compose config, OpenSpec strict changes/spec validation, OpenSpec strict specs validation, and `git diff --check`.
- Follow-up notes: Commit Phase 5 implementation, fast-forward merge `feat/scene-view-galgame` to local `main`, then record merge bookkeeping before starting Phase 6.

## v0.8.5 Scene View / Galgame View merge entry

- Date: 2026-05-16
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 5 merge bookkeeping.
- Summary: Fast-forward merged `feat/scene-view-galgame` into local `main`, marked Phase 5 complete in OpenSpec tasks, and moved harness handoff state to Phase 6 Player Privacy & Data Controls planning.
- Files changed: `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 6 from clean local `main`; preserve shared-world data safeguards and avoid destructive deletion of canonical records.

## v0.8.6 Player Privacy & Data Controls planning entry

- Date: 2026-05-16
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 6 planning.
- Summary: Added the Phase 6 checkpoint for authenticated player data export and reviewable deletion/redaction requests, with shared-world safeguards and no automatic deletion of shared canonical records.
- Files changed: `/docs/agent/harness/feature-updates/v0.8.6-player-privacy-data-controls-plan.md`, `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A, documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Verification: OpenSpec strict changes validation and `git diff --check`.
- Follow-up notes: Implement Phase 6 on a feature branch. Keep privacy controls authenticated, deterministic, reviewable, and free of storage path, raw prompt/output, bytes/base64, or secret leaks.

## v0.8.6 Player Privacy & Data Controls implementation entry

- Date: 2026-05-16
- Branch: feat/player-privacy-controls
- Scope: v0.8 Public Experience & Ecosystem Phase 6 player privacy export and delete-request workflow.
- Summary: Added a dedicated `player_privacy` backend package, `player_privacy.py` router, `player_privacy_requests` migration, sanitized player export preview/export request API, reviewable delete request API, admin review route, player privacy Web page, component tests, and e2e coverage. The workflow records requests and safe summaries only; it does not delete shared world records or write world event payloads.
- Files changed: `/backend/packages/player_privacy/**`, `/backend/services/api/src/noveland/services/api/player_privacy.py`, `/backend/migrations/versions/20260516_0043_player_privacy_requests.py`, `/backend/tests/test_api_player_privacy.py`, `/web/app/worlds/[worldId]/player/privacy/page.tsx`, `/web/features/worlds/player-privacy-controls.tsx`, `/web/features/worlds/player-privacy-controls.test.tsx`, `/web/tests/e2e/{auth.spec.ts,start-with-mock-auth.mjs}`, OpenSpec tasks, and harness docs.
- Tests added/updated: backend privacy API/schema/import tests, `PlayerPrivacyControls` Vitest coverage, and e2e coverage for authenticated player privacy export/delete review workflows and no leak markers.
- Docs updated: OpenSpec task status, project index, file inventory, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff and mypy for player privacy files, backend pytest (`28 passed`), Web lint, Web typecheck, focused privacy component tests (`2 passed`), focused privacy e2e (`1 passed`), and no forbidden storage/prompt/secret markers in tested responses/pages.
- Follow-up notes: Run the full local gate, then fast-forward merge Phase 6 back to local `main` if it stays green.

## v0.8.6 Player Privacy & Data Controls gate entry

- Date: 2026-05-16
- Branch: feat/player-privacy-controls
- Scope: v0.8 Public Experience & Ecosystem Phase 6 full local gate.
- Summary: Recorded the successful full local gate for authenticated player privacy export and reviewable delete-request workflows.
- Files changed: `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, gate bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Verification: Full local gate passed with backend ruff, backend mypy (`267 source files`), backend pytest (`425 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`40 passed files`, `126 passed`), Web build, Web `check:next-env`, Web e2e (`21 passed` after fixing the serial-state privacy count assertion), docker compose config, OpenSpec strict changes/spec validation, OpenSpec strict specs validation, and `git diff --check`.
- Follow-up notes: Commit Phase 6 implementation, fast-forward merge `feat/player-privacy-controls` to local `main`, then record merge bookkeeping before starting Phase 7.

## v0.8.6 Player Privacy & Data Controls merge entry

- Date: 2026-05-16
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 6 merge bookkeeping.
- Summary: Fast-forward merged `feat/player-privacy-controls` into local `main`, marked Phase 6 complete in OpenSpec tasks, and moved harness handoff state to Phase 7 World Packaging planning.
- Files changed: `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/{task-board,handoffs/active-session,change-journal}.md`
- Tests added/updated: N/A, merge bookkeeping only.
- Docs updated: OpenSpec tasks, task board, active handoff, and change journal.
- Follow-up notes: Start Phase 7 from clean local `main`; keep packaging manifest-safe and preview/apply-first, with no secret, storage path, or raw prompt export.

## v0.8.7 World Packaging planning entry

- Date: 2026-05-16
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 7 planning.
- Summary: Added the Phase 7 checkpoint for backend/API-only safe world packaging. The first implementation uses a dedicated packaging package/router, produces portable world/media manifests, validates import preview before mutation, applies only on explicit admin request, and avoids migrations, Web UI, broad `worlds.py` growth, provider execution, marketplace scope, and export of secrets/storage paths/raw prompt data.
- Files changed: `/docs/agent/harness/feature-updates/v0.8.7-world-packaging-plan.md`, `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A, documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Verification: OpenSpec strict changes validation and `git diff --check`.
- Follow-up notes: Implement Phase 7 on a feature branch. Keep package manifests portable and safe; no storage path, secret, bytes/base64, raw prompt/output, provider call, daemon job, or public marketplace scope.

## v0.8.7 World Packaging implementation entry

- Date: 2026-05-16
- Branch: feat/world-packaging
- Scope: v0.8 Public Experience & Ecosystem Phase 7 backend/API world packaging.
- Summary: Added a dedicated `world_packaging` package and `world_packaging.py` router for safe package export preview, import preview, and explicit import apply. The first implementation is response-only/no-migration for preview, creates only safe imported world/worldline/scene/media metadata on apply, and does not copy bytes, expose storage paths, execute providers, write world events, add Web UI, or touch `worlds.py`.
- Files changed: `/backend/packages/world_packaging/**`, `/backend/services/api/src/noveland/services/api/world_packaging.py`, backend workspace metadata, `/backend/tests/test_api_world_packaging.py`, OpenSpec tasks, and harness docs.
- Tests added/updated: package manifest API tests for safe export, preview blockers/no mutation, explicit apply, forbidden marker rejection, router separation, and existing world composition round-trip regression.
- Docs updated: OpenSpec task status, project index, file inventory, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff and mypy for world packaging files, targeted pytest (`7 passed`), broader targeted pytest (`34 passed`), and the full local gate: backend ruff, backend mypy, backend pytest (`430 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`126 passed`), Web build, Web `check:next-env`, Web e2e (`21 passed`), docker compose config, `git diff --check`, and OpenSpec strict changes/specs validation.
- Follow-up notes: Phase 7 fast-forward merged to local `main`; continue with Phase 8 Plugin/Provider Package Contract planning checkpoint from clean `main`.

## v0.8.7 World Packaging merge entry

- Date: 2026-05-16
- Branch: main
- Commit merged: `7d12ef7 feat(v0.8): add world packaging`
- Summary: Fast-forward merged Phase 7 World Packaging to local `main` after full local gate and OpenSpec validation passed.
- Follow-up notes: Start Phase 8 with docs-only planning checkpoint before implementation. Do not push unless explicitly requested.

## v0.8.8 Plugin/Provider Package Contract planning entry

- Date: 2026-05-16
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 8 planning.
- Summary: Added the Phase 8 checkpoint for backend/API-only plugin/provider package contract validation and safe provider config export. The first implementation uses response-only contracts, validates submitted plugin/provider metadata against existing plugin/provider concepts, exports only sanitized provider config summaries, and avoids migrations, Web UI, provider execution, marketplace scope, user-managed secret UI, untrusted-code installation, and broad `worlds.py` growth.
- Files changed: `/docs/agent/harness/feature-updates/v0.8.8-plugin-provider-package-contract-plan.md`, `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A, documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Verification: OpenSpec strict changes validation and `git diff --check`.
- Follow-up notes: Implement Phase 8 on a feature branch. Keep package contracts safe, admin-scoped, response-only, and free of resolved secrets, storage paths, raw prompts/outputs, provider calls, daemon jobs, marketplace behavior, and runtime plugin installation.

## v0.8.8 Plugin/Provider Package Contract implementation entry

- Date: 2026-05-16
- Branch: feat/plugin-provider-package-contract
- Scope: v0.8 Public Experience & Ecosystem Phase 8 backend/API package contract validation.
- Summary: Added a dedicated `package_contracts` package and `package_contracts.py` router for response-only package metadata validation and safe provider config export. The implementation validates plugin declarations against the builtin plugin registry, validates provider declarations against provider adapter/capability concepts, exports only sanitized provider config summaries with opaque `auth_ref`, and does not persist package reviews, install plugins, execute providers, create marketplace state, add Web UI, or touch `worlds.py`.
- Files changed: `/backend/packages/package_contracts/**`, `/backend/services/api/src/noveland/services/api/package_contracts.py`, backend workspace metadata, `/backend/tests/test_api_package_contracts.py`, OpenSpec tasks, and harness docs.
- Tests added/updated: package contract API tests for valid metadata, registry/secret issues, safe provider config export, ACL, existing provider route compatibility, and workspace imports.
- Docs updated: OpenSpec task status, task board, active handoff, file inventory, project index, and change journal.
- Verification: Targeted checks passed with backend ruff and mypy for package contract files, targeted pytest (`37 passed`), and the full local gate: backend ruff, backend mypy (`277 source files`), backend pytest (`435 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`126 passed`), Web build, Web `check:next-env`, Web e2e (`21 passed`), docker compose config, `git diff --check`, and OpenSpec strict changes/specs validation.
- Follow-up notes: Phase 8 fast-forward merged to local `main`; continue with Phase 9 Sample World Release Package planning checkpoint from clean `main`.

## v0.8.8 Plugin/Provider Package Contract merge entry

- Date: 2026-05-16
- Branch: main
- Commit merged: `cf0a511 feat(v0.8): add plugin provider package contracts`
- Summary: Fast-forward merged Phase 8 Plugin/Provider Package Contract to local `main` after full local gate and OpenSpec validation passed.
- Follow-up notes: Start Phase 9 with docs-only planning checkpoint before implementation. Do not push unless explicitly requested.

## v0.8.9 Sample World Release Package planning entry

- Date: 2026-05-16
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 9 planning.
- Summary: Added the Phase 9 checkpoint for a deterministic sample world release package tied to the Phase 13 multimodal sample-world fixture and Phase 7 world packaging. The first implementation stays in tests/docs, builds a safe manifest with rights/visibility/fixture linkage metadata, validates preview/apply through `WorldPackagingService`, and avoids migrations, Web UI, provider execution, daemon jobs, marketplace scope, byte copying, and production seed framework behavior.
- Files changed: `/docs/agent/harness/feature-updates/v0.8.9-sample-world-release-package-plan.md`, `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/docs/agent/harness/**`
- Tests added/updated: N/A, documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list, project index, file inventory, task board, active handoff, and change journal.
- Verification: OpenSpec strict changes validation and `git diff --check`.
- Follow-up notes: Implement Phase 9 on a feature branch. Keep the sample package deterministic, fixture-linked, manifest-safe, and free of storage paths, raw prompt/output, bytes/base64, resolved secrets, provider calls, daemon jobs, marketplace behavior, and production seed framework scope.

## v0.8.9 Sample World Release Package implementation entry

- Date: 2026-05-16
- Branch: feat/sample-world-release-package
- Scope: v0.8 Public Experience & Ecosystem Phase 9 deterministic sample world release package.
- Summary: Added a test/docs-only sample release package helper that builds a safe `WorldPackageManifest` from the Phase 13 multimodal sample-world fixture, records fixture linkage, expected counts, rights/source/visibility metadata, reader playback/scene media roles, and diagnostics evidence refs, then validates preview/apply through `WorldPackagingService`. No runtime API, migration, provider execution, byte copy, production seed framework, marketplace behavior, or Web UI was added.
- Files changed: `/backend/tests/fixtures/sample_world_release_package.py`, `/backend/tests/test_sample_world_release_package.py`, `/docs/agent/fixtures/sample-world-release-package.md`, OpenSpec tasks, and harness docs.
- Tests added/updated: sample release package determinism, rights/visibility/reader-media roles, import preview/apply safety, diagnostics linkage, no-leak assertions, existing multimodal fixture regression, world packaging API regression, security regression, and workspace imports.
- Docs updated: fixture docs, OpenSpec task status, project index, file inventory, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff and mypy for sample release package files, targeted pytest (`19 passed`), and the full local gate: backend ruff, backend mypy (`279 source files`), backend pytest (`439 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`126 passed`), Web build, Web `check:next-env`, Web e2e (`21 passed`), docker compose config, `git diff --check`, and OpenSpec strict changes/specs validation.
- Follow-up notes: Fast-forward merge Phase 9 back to local `main` if the branch remains clean.

## v0.8.9 Sample World Release Package merge entry

- Date: 2026-05-16
- Branch: main
- Commit merged: `2949acb feat(v0.8): add sample world release package`
- Summary: Fast-forward merged Phase 9 Sample World Release Package to local `main` after targeted checks, full local gate, and OpenSpec validation passed.
- Follow-up notes: Start Phase 10 Moderation & Incident Workflow with a docs-only planning checkpoint before implementation. Do not push unless explicitly requested.

## v0.8.10 Moderation & Incident Workflow planning entry

- Date: 2026-05-16
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 10 planning.
- Summary: Added the Phase 10 checkpoint and resolved schema/router ownership to a dedicated `moderation` package and `moderation.py` router for persisted public reports, moderation actions, and incident workflow records. The plan reuses v0.7 observability evidence concepts but keeps observability as derived diagnostics/readiness, not workflow ownership.
- Files changed: `/docs/agent/harness/feature-updates/v0.8.10-moderation-incident-workflow-plan.md`, `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/openspec/changes/v0-8-public-experience-ecosystem/design.md`, `/openspec/changes/v0-8-public-experience-ecosystem/phase-plan.md`, and harness docs.
- Tests added/updated: N/A, documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list/design/phase plan, project index, file inventory, task board, active handoff, and change journal.
- Verification: OpenSpec strict changes validation and `git diff --check`.
- Follow-up notes: Implement Phase 10 on a feature branch. Do not add Web UI, automatic moderation, provider calls, daemon work, public unauthenticated access, duplicate observability/readiness framework, or broad `worlds.py` routes.

## v0.8.10 Moderation & Incident Workflow implementation entry

- Date: 2026-05-16
- Branch: feat/moderation-incident-workflow
- Scope: v0.8 Public Experience & Ecosystem Phase 10 backend/API moderation workflow.
- Summary: Added a dedicated `moderation` package, `moderation.py` router, and migration `20260516_0044_moderation_incident_workflow.py` for persisted reports, actions, and incident workflow records. The implementation supports reader/member report creation, admin report review, bounded action audit records, incident grouping/review, safe evidence refs, and reader-delivery suppression for explicitly applied media/world takedown actions. It does not mutate provider/media rows for disable actions, write world events, execute providers, run daemons, add Web UI, or add routes to `worlds.py`.
- Files changed: `/backend/packages/moderation/**`, `/backend/services/api/src/noveland/services/api/moderation.py`, `/backend/migrations/versions/20260516_0044_moderation_incident_workflow.py`, backend workspace metadata, reader delivery suppression hook, `/backend/tests/test_api_moderation.py`, schema/Alembic tests, OpenSpec tasks, and harness docs.
- Tests added/updated: moderation API coverage for report creation/review, ACL, cross-worldline rejection, evidence/metadata redaction, provider action audit, incident grouping, reader-media takedown suppression, reader media compatibility, schema metadata, Alembic head, and workspace imports.
- Docs updated: OpenSpec task status, project index, file inventory, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff and mypy for moderation/API/reader-delivery/schema files, targeted pytest (`41 passed`), and the full local gate: backend ruff, backend mypy (`285 source files`), backend pytest (`444 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`126 passed`), Web build, Web `check:next-env`, Web e2e (`21 passed`), docker compose config, `git diff --check`, and OpenSpec strict changes/specs validation.
- Follow-up notes: Commit Phase 10 implementation and fast-forward merge to local `main` if the branch remains clean. Keep Phase 10 backend/API-only; no Web UI, automatic moderation, provider execution, daemon work, public unauthenticated access, duplicate readiness framework, or broad `worlds.py` routes.

## v1.0.8 Private Beta Gate planning entry

- Date: 2026-05-20
- Branch: feature/v1.0-8-private-beta-gate
- Scope: v1.0 Phase 8 planning checkpoint before implementation.
- Summary: Added the Phase 8 checkpoint for private beta gate ownership. The plan keeps the gate under existing observability/readiness, adds a platform-admin read-only report with `readiness_kind=private_beta_gate`, reuses setup/onboarding/session/quota/feedback/QA/repair/self-use evidence, adds no migration, Web UI, duplicate readiness framework, provider calls, public launch signoff, or broad `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v1.0.8-private-beta-gate-plan.md`, `/openspec/changes/v1-0-private-beta-mvp/{design.md,phase-plan.md,tasks.md}`, `/openspec/changes/v1-0-private-beta-mvp/specs/private-beta-gate/spec.md`, and harness docs.
- Tests added/updated: N/A for planning checkpoint.
- Verification: pending with Phase 8 implementation gate.
- Follow-up notes: Implement the backend/API gate in `backend/packages/observability/` and the app-level observability router. Do not add gate tables, Web UI, provider execution, or public launch semantics.

## v1.0.8 Private Beta Gate implementation entry

- Date: 2026-05-20
- Branch: feature/v1.0-8-private-beta-gate
- Scope: v1.0 Phase 8 backend/API private beta readiness gate.
- Summary: Extended observability/readiness with `PrivateBetaGateReport`, `ProductionReadinessGateService.private_beta_gate_report()`, and platform-admin `GET /observability/readiness/private-beta`. The report reuses private beta setup readiness, checks feedback path evidence, memory/persona QA confirmation, beta repair-loop traceability, manual 1-2 hour tester-session checklist items, and world-event leak checks. It keeps `public_launch_ready=false` and adds no migration, Web UI, duplicate readiness framework, provider execution, public launch semantics, tester-visible diagnostics, or broad `worlds.py` routes.
- Files changed: `/backend/packages/observability/src/noveland/observability/{contracts.py,services.py,__init__.py}`, `/backend/packages/observability/pyproject.toml`, `/backend/services/api/src/noveland/services/api/observability.py`, `/backend/tests/test_production_readiness_gate.py`, `/backend/uv.lock`, OpenSpec tasks/spec docs, and harness docs.
- Tests added/updated: private beta gate pass/fail coverage for setup/feedback/QA/repair/manual evidence, leak fixture blocking, platform-admin-only endpoint ACL, public-launch distinction, no duplicate gate tables, response redaction, and workspace import smoke.
- Verification: Targeted ruff/mypy passed for observability/API/test files; targeted pytest passed for readiness gate (`22 passed`) and workspace import smoke (`1 passed`). Full backend/OpenSpec gate passed: backend ruff, backend mypy (`321 source files`), backend pytest (`529 passed, 8 skipped`), OpenSpec strict changes/specs validation, and `git diff --check`.
- Follow-up notes: Commit Phase 8, fast-forward merge to local `main`, and stop without archiving v1.0 unless explicitly instructed. No Web gate was run because Phase 8 touched no Web files.

## v1.0.8 Private Beta Gate merge entry

- Date: 2026-05-20
- Branch: main
- Commit merged: `6f370ba feat(v1.0): add private beta readiness gate`
- Summary: Fast-forward merged Phase 8 Private Beta Gate to local `main` after targeted checks, full backend/OpenSpec gate, OpenSpec validation, and `git diff --check` passed.
- Follow-up notes: v1.0 implementation phases are complete locally. Do not archive v1.0 or push unless explicitly requested.

## v1.0.7 Beta Content Iteration Loop planning entry

- Date: 2026-05-20
- Branch: feature/v1.0-7-beta-content-iteration
- Scope: v1.0 Phase 7 planning checkpoint before implementation.
- Summary: Added the Phase 7 checkpoint for beta content repair proposal ownership. The plan keeps repair ownership inside the existing authoring proposal/review/apply boundary, uses `beta_feedback_reports.repair_proposal_refs` for safe feedback linkage, adds no new repair package, migration, Web UI, or broad `worlds.py` routes, and maps first-version repair kinds onto existing persona, memory, asset-match, visual-generation-profile, and trace-only authoring proposal targets.
- Files changed: `/docs/agent/harness/feature-updates/v1.0.7-beta-content-iteration-loop-plan.md`, `/openspec/changes/v1-0-private-beta-mvp/{design.md,phase-plan.md,tasks.md}`, `/openspec/changes/v1-0-private-beta-mvp/specs/beta-content-iteration-loop/spec.md`, and harness docs.
- Tests added/updated: N/A for planning checkpoint.
- Verification: pending with Phase 7 implementation gate.
- Follow-up notes: Implement the backend/API repair bridge through the existing authoring router. Do not add duplicate repair tables, automatic mutation, Web UI, or provider calls.

## v1.0.7 Beta Content Iteration Loop implementation entry

- Date: 2026-05-20
- Branch: feature/v1.0-7-beta-content-iteration
- Scope: v1.0 Phase 7 backend/API beta content repair bridge.
- Summary: Added authoring beta content repair contracts, service logic, and an admin-only `POST /worlds/{world_id}/authoring/beta-content-repairs` endpoint. The endpoint creates a preview authoring import run plus proposed repair records, maps persona/memory/sprite/voice/background/visual-generation/provider/dialogue-style repairs onto existing authoring proposal targets, links beta feedback reports to safe repair proposal refs, and keeps review/apply as the only mutation path. Phase 7 adds no migration, Web UI, provider execution, duplicate repair package, broad `worlds.py` routes, or world-event writes.
- Files changed: `/backend/packages/authoring/src/noveland/authoring/{contracts.py,service.py,__init__.py}`, `/backend/packages/beta_feedback/src/noveland/beta_feedback/service.py`, `/backend/services/api/src/noveland/services/api/authoring.py`, `/backend/tests/test_authoring_service.py`, `/backend/tests/test_api_authoring.py`, OpenSpec tasks/spec docs, and harness docs.
- Tests added/updated: service tests for proposal-only persona/provider-profile repair and reviewed persona/memory apply; API tests for admin-only repair creation, feedback repair-link persistence, no pre-apply mutation, reviewed apply, and cross-worldline feedback rejection.
- Verification: Targeted ruff passed for modified backend files; targeted pytest passed for authoring/API (`34 passed`) and beta feedback/import smoke (`5 passed`); targeted mypy passed (`18 source files`). Full backend/OpenSpec gate passed: backend ruff, backend mypy (`321 source files`), backend pytest (`524 passed, 8 skipped`), OpenSpec strict changes/specs validation, and `git diff --check`.
- Follow-up notes: Commit Phase 7, fast-forward merge to local `main`, then start Phase 8 Private Beta Gate from clean `main`. No Web gate was run because Phase 7 touched no Web files.

## v1.0.7 Beta Content Iteration Loop merge entry

- Date: 2026-05-20
- Branch: main
- Commit merged: `fb77ee2 feat(v1.0): add beta content iteration loop`
- Summary: Fast-forward merged Phase 7 Beta Content Iteration Loop to local `main` after targeted checks, full backend/OpenSpec gate, OpenSpec validation, and `git diff --check` passed.
- Follow-up notes: Start Phase 8 Private Beta Gate from clean local `main` on `feature/v1.0-8-private-beta-gate`. Do not archive v1.0 or push until Phase 8 is complete and accepted.

## v0.8.10 Moderation & Incident Workflow merge entry

- Date: 2026-05-16
- Branch: main
- Commit merged: `50e843b feat(v0.8): add moderation incident workflow`
- Summary: Fast-forward merged Phase 10 Moderation & Incident Workflow to local `main` after targeted checks, full local gate, and OpenSpec validation passed.
- Follow-up notes: Start Phase 11 Public Launch Gate with a docs-only planning checkpoint before implementation. Do not push unless explicitly requested.

## v0.8.11 Public Launch Gate planning entry

- Date: 2026-05-16
- Branch: main
- Scope: v0.8 Public Experience & Ecosystem Phase 11 planning.
- Summary: Added the Phase 11 checkpoint for platform-admin-only public launch readiness aggregation under the existing observability/readiness boundary. The plan reuses v0.7 `ProductionReadinessGateService`, adds v0.8 public-surface evidence and explicit signoff flags, and avoids migrations, duplicate readiness/release tables, Web UI, automatic launch, public unauthenticated access, provider execution, daemon work, and broad `worlds.py` routes.
- Files changed: `/docs/agent/harness/feature-updates/v0.8.11-public-launch-gate-plan.md`, `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, `/openspec/changes/v0-8-public-experience-ecosystem/phase-plan.md`, and harness docs.
- Tests added/updated: N/A, documentation-only planning checkpoint.
- Docs updated: feature plan, OpenSpec task list/phase plan, project index, file inventory, task board, active handoff, and change journal.
- Verification: OpenSpec strict changes validation and `git diff --check`.
- Follow-up notes: Implement Phase 11 on a feature branch. Keep it read-only/admin-only and do not duplicate v0.7 readiness or release frameworks.

## v0.8.11 Public Launch Gate implementation entry

- Date: 2026-05-16
- Branch: feat/public-launch-gate
- Scope: v0.8 Public Experience & Ecosystem Phase 11 public launch readiness aggregation.
- Summary: Extended the existing `noveland.observability` readiness boundary with `PublicLaunchReadinessReport`, `ProductionReadinessGateService.public_launch_report()`, and the platform-admin-only `/observability/readiness/public-launch` endpoint. The report reuses v0.7 internal production readiness, aggregates v0.8 reader media, conversation presentation, privacy, moderation, sample package/eval, plugin/provider safety, and public DTO security evidence, requires explicit signoff flags, keeps `auto_launch_enabled=false`, and does not add migrations, duplicate readiness/release tables, Web UI, provider execution, daemon work, public unauthenticated access, or broad `worlds.py` routes.
- Files changed: `/backend/packages/observability/src/noveland/observability/{contracts,services,__init__}.py`, `/backend/services/api/src/noveland/services/api/observability.py`, `/backend/tests/test_production_readiness_gate.py`, `/openspec/changes/v0-8-public-experience-ecosystem/tasks.md`, and harness docs.
- Tests added/updated: public launch readiness tests for internal-readiness blocker propagation, explicit signoff blockers, successful evidence/signoff aggregation, platform-admin-only endpoint ACL, response redaction, and no duplicate readiness framework tables.
- Docs updated: OpenSpec task status, project index, task board, active handoff, and change journal.
- Verification: Targeted checks passed with backend ruff and mypy for observability/API/test files and targeted pytest (`70 passed`). Full local gate passed: backend ruff, backend mypy (`285 source files`), backend pytest (`449 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`126 passed`), Web build, Web `check:next-env`, Web e2e (`21 passed`), docker compose config, `git diff --check`, and OpenSpec strict changes/specs validation.
- Follow-up notes: Fast-forward merged Phase 11 back to local `main`; v0.8 Public Experience & Ecosystem is locally complete. Do not push unless explicitly requested.

## v0.8.11 Public Launch Gate merge entry

- Date: 2026-05-16
- Branch: main
- Commit merged: `283433d feat(v0.8): add public launch readiness gate`
- Summary: Fast-forward merged Phase 11 Public Launch Gate to local `main` after targeted checks, full local gate, and OpenSpec validation passed.
- Follow-up notes: v0.8 Public Experience & Ecosystem is complete locally and ready for archive/release-note work if requested. No push performed.

## v0.9 Self-use MVP Demo World Cut feasibility review entry

- Date: 2026-05-16
- Branch: main
- Scope: v0.9 feasibility review only; no backend/Web implementation, migrations, API behavior, runtime behavior, or push.
- Summary: Added the v0.9 feasibility review after reading the active v0.9 OpenSpec and current provider, media, authoring, memory/persona, visual, speech, asset-generation, packaging, and readiness boundaries. The review concludes v0.9 can proceed as one change after review acceptance, but Phase 1 must confirm provider text adapter/model discovery/template ownership and Phase 2 must confirm a dedicated `visual_generation` package/router/schema boundary before implementation.
- Files changed: `/docs/agent/harness/feature-updates/v0.9-self-use-mvp-demo-world-cut-feasibility-review.md`, `/openspec/changes/v0-9-self-use-mvp-demo-world-cut/tasks.md`, and harness docs.
- Tests added/updated: N/A, documentation-only feasibility review.
- Verification: OpenSpec strict changes validation, OpenSpec strict specs validation, and `git diff --check`.
- Follow-up notes: Start v0.9 Phase 1 only after accepting the feasibility review and writing the Phase 1 planning checkpoint. Do not push unless explicitly requested.

## v0.9.1 MVP Provider Settings & Model Lab planning entry

- Date: 2026-05-16
- Branch: feat/v0.9-provider-settings-model-lab
- Scope: v0.9 Phase 1 planning checkpoint before implementation.
- Summary: Added the Phase 1 checkpoint for provider settings/model lab. The phase will use static/code-owned provider templates over the existing provider registry, add server-side redacted model discovery with manual fallback, align OpenAI-compatible and Anthropic-compatible text execution through `ProviderExecutionService`, keep real provider tests opt-in, and preserve `auth_ref`/secret-only handling. No Visual Generation Control Plane, galgame intake, script parsing, memory distillation, or demo assembly work is included.
- Files changed: `/docs/agent/harness/feature-updates/v0.9.1-mvp-provider-settings-model-lab-plan.md`, `/openspec/changes/v0-9-self-use-mvp-demo-world-cut/tasks.md`, and harness docs.
- Tests added/updated: N/A, documentation-only planning checkpoint.
- Verification: pending docs-only OpenSpec validation and `git diff --check` before phase implementation commit.
- Follow-up notes: Implement Phase 1 backend/API/UI on the feature branch. Use existing provider package/router/UI surfaces only; do not add persistent provider-template tables or broad `worlds.py` routes.

## v0.9.1 MVP Provider Settings & Model Lab implementation entry

- Date: 2026-05-16
- Branch: feat/v0.9-provider-settings-model-lab
- Scope: v0.9 Phase 1 backend/API/Web provider settings and model lab only.
- Summary: Added static provider templates, redacted server-side model discovery, manual model-name fallback, OpenAI-compatible and Anthropic-compatible text adapters in `ProviderExecutionService`, and an operator-grade provider admin model lab UI. Phase 1 adds no migrations, no persistent provider-template tables, no Visual Generation Control Plane, no galgame intake, no reader/player provider routes, no broad `worlds.py` routes, and no default real provider tests.
- Files changed: provider templates/discovery/text adapters/contracts/service/API, provider API/execution tests, provider Web client/server helpers, provider admin UI/tests, OpenSpec tasks, Phase 1 checkpoint, and harness docs.
- Tests added/updated: provider template/discovery ACL and leak tests, model discovery failure/manual fallback tests, OpenAI/Anthropic-compatible dry-run ledger tests, Web provider client tests, and provider admin model lab UI tests.
- Verification: Targeted backend tests passed (`21 passed`), targeted Web tests passed (`9 passed`), full backend ruff/mypy/pytest passed (`453 passed, 7 skipped`), full Web lint/typecheck/unit/build/check:next-env passed (`128 unit tests`), Web e2e passed on rerun (`21 passed`), docker compose config passed, OpenSpec strict changes/specs validation passed, and `git diff --check` passed.
- Flaky notes: The first full Web e2e run timed out on the existing broad `world admin manages workspace pages and conversations` scenario while waiting for participant save. The isolated scenario passed immediately, and the subsequent full e2e run passed.
- Follow-up notes: Fast-forward merge Phase 1 to local `main`. Next accepted v0.9 work is Phase 2 Visual Generation Control Plane planning; do not start Phase 2 until explicitly requested.

## Post-v1.1 RC Audit and Hardening preflight entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: OpenSpec-governed post-v1.1 release-candidate audit setup and initial handoff only.
- Summary: Reconfirmed realtime git/OpenSpec/service/test-entry status from the server, read current harness/architecture/v0.9-v1.1 archive and release-note context, created `openspec/changes/audit-and-hardening-post-v1-1-rc/`, and defined the audit/hardening proposal, design, spec delta, and task plan. No implementation files were changed.
- Files changed: `openspec/changes/audit-and-hardening-post-v1-1-rc/**`, `docs/agent/harness/{project-index.md,file-inventory.md,task-board.md,handoffs/active-session.md,change-journal.md}`.
- Tests added/updated: N/A, planning and audit setup only.
- Verification: `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; initial baseline had `openspec validate --specs --strict` passing 76 specs and no active changes before this branch.
- Follow-up notes: Start backend security audit first. Record concrete findings before implementation fixes. Do not push.

## Post-v1.1 RC Audit and Hardening backend CSRF batch entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend security audit batch 1, focused on CSRF coverage for persisted cookie-authenticated mutations.
- Finding: F-001 found moderation report/review/action/incident mutations, player privacy export/delete/review mutations, and world package import apply lacked CSRF protection while relying on browser session cookies.
- Summary: Added OpenSpec deltas for moderation, player privacy, and world packaging CSRF expectations; added decorator-level Depends(require_csrf) on persisted mutation routes; preserved non-persisting login, validate, resolve, memory search, and package preview POST behavior for later policy review.
- Files changed: backend/services/api/src/noveland/services/api/moderation.py, backend/services/api/src/noveland/services/api/player_privacy.py, backend/services/api/src/noveland/services/api/world_packaging.py, backend/tests/test_api_moderation.py, backend/tests/test_api_player_privacy.py, backend/tests/test_api_world_packaging.py, openspec/changes/audit-and-hardening-post-v1-1-rc/**, and harness docs.
- Tests added/updated: Missing-CSRF regression assertions for moderation report create/review, player privacy export/delete/review, and world package import apply.
- Verification: uv run pytest tests/test_api_moderation.py tests/test_api_player_privacy.py tests/test_api_world_packaging.py passed with 18 passed; uv run ruff check on the six touched backend/test files passed; uv run mypy on the same six files passed.
- Follow-up notes: Continue backend audit with worldline isolation, provider spend/secret boundaries, forbidden response/event data, and the remaining non-persisting POST policy review. Do not push unless explicitly requested.


## Post-v1.1 RC Audit and Hardening provider boundary finding entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend provider spend/secret boundary read-only audit.
- Finding: F-002 found legacy ProviderProfileService execution paths that can call provider plugins/httpx directly from provider-profile test calls, runtime agent runs, conversation advancement, and narrative generation without ProviderExecutionService.
- Summary: Added OpenSpec deltas for provider-system and cost-quota-enforcement requiring legacy profile execution to route through ProviderExecutionService or be blocked/degraded before external spend. No business code was changed in this finding-only batch.
- Files changed: openspec/changes/audit-and-hardening-post-v1-1-rc/specs/provider-system/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/cost-quota-enforcement/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: N/A, finding/spec-record batch only.
- Verification: pending OpenSpec strict validation and git diff --check before commit.
- Follow-up notes: Next implementation batch should choose a compatibility strategy for legacy provider profiles and add regression tests proving no legacy path executes hidden provider spend outside ProviderExecutionService. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening provider boundary remediation entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend provider spend/secret boundary remediation for F-002.
- Finding: F-002 found legacy ProviderProfileService execution paths that could call provider plugins/httpx directly without ProviderExecutionService, quota checks, safe auth metadata, or centralized provider execution failure handling.
- Summary: Blocked legacy ProviderProfileService.invoke_profile before API key lookup, rate-limit accounting, plugin provider creation, or HTTP transport. Provider profile test calls now persist a failed configuration result with a safe migration message instead of executing hidden external spend. Direct provider adapter unit tests remain available for adapter behavior, while service-level legacy execution is disabled/degraded until migrated to ProviderExecutionService.
- Files changed: backend/packages/adapters/src/noveland/adapters/model_provider.py, backend/tests/test_model_provider.py, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Service-level regression tests proving legacy execution is blocked before mock transport execution and before missing secret-ref disclosure, plus provider test-call state coverage for failed/degraded legacy execution.
- Verification: uv run pytest tests/test_model_provider.py tests/test_api_runtime.py tests/test_runtime_daemon.py passed with 20 passed; uv run ruff check packages/adapters/src/noveland/adapters/model_provider.py tests/test_model_provider.py passed; uv run mypy packages/adapters/src/noveland/adapters/model_provider.py tests/test_model_provider.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; git diff --check passed.
- Follow-up notes: Future migration should map or replace platform provider profiles with world-scoped ProviderExecutionService provider integrations. Continue backend audit with worldline isolation and forbidden-data exposure paths. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening member media storage reference remediation entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-003.
- Finding: F-003 found member media asset list/search/get routes using get_world_member_context but returning MediaAssetRecord, whose storage_uri, preview_uri, and thumbnail_uri fields were copied directly from media assets.
- Summary: Added an architecture-contracts OpenSpec delta for member media asset storage-reference redaction, then redacted asset-level storage_uri, preview_uri, and thumbnail_uri from non-admin member media asset list/search/get responses. World admins and platform admins retain the internal storage reference fields for media management.
- Files changed: backend/services/api/src/noveland/services/api/media.py, backend/tests/test_api_media.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Media API member visibility regression now seeds a member-visible asset with internal storage references and asserts list/search/get redact them for members while preserving them for world admins.
- Verification: uv run pytest tests/test_api_media.py tests/test_api_reader_media.py passed with 12 passed; uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py passed; uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; git diff --check passed.
- Follow-up notes: Continue forbidden-data audit for member-facing media metadata, media contexts/inputs/references, world event payloads, reader/player DTOs, and worldline isolation paths. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening media job admin boundary remediation entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-004.
- Finding: F-004 found member media job list/detail routes using get_world_member_context while returning MediaJobRecord, which includes provider_config_json, request_json, result_json, error_text, and created_by_actor_ref.
- Summary: Added an architecture-contracts OpenSpec delta requiring media job execution diagnostics to stay out of member responses, then made media job list/detail admin-only via the existing world admin dependency. Admin media management keeps job internals for operator diagnosis.
- Files changed: backend/services/api/src/noveland/services/api/media.py, backend/tests/test_api_media.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added a Media API regression that seeds provider config, raw prompt-like request JSON, storage_uri, bytes/base64 marker, raw output-like result JSON, and error_text; ordinary world members now receive 403 on list/detail while world admins retain diagnostics.
- Verification: uv run pytest tests/test_api_media.py tests/test_api_reader_media.py passed with 13 passed; uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py passed; uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; git diff --check passed before commit.
- Follow-up notes: Continue forbidden-data audit for member-facing media lineage related_assets, metadata-bearing contexts/inputs/references/collections/tags, world event payloads, reader/player DTOs, and worldline isolation paths. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening media lineage related asset redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-005.
- Finding: F-005 found member media lineage responses returning related_assets from MediaLineageService.lineage without API-layer member redaction, leaving storage_uri, preview_uri, and thumbnail_uri visible on nested MediaAssetRecord values.
- Summary: Added an architecture-contracts OpenSpec delta for member media lineage related asset redaction, then shaped MediaAssetLineage.related_assets through the existing media asset context redaction helper. World admins retain related asset storage references for media management.
- Files changed: backend/services/api/src/noveland/services/api/media.py, backend/tests/test_api_media.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended the visible fork lineage regression to seed related asset storage references and assert member lineage redacts storage_uri, preview_uri, and thumbnail_uri while admin lineage preserves them.
- Verification: uv run pytest tests/test_api_media.py tests/test_api_reader_media.py passed with 13 passed; uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py passed; uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; git diff --check passed before commit.
- Follow-up notes: Continue forbidden-data audit for metadata-bearing media contexts/inputs/references/collections/tags, world event payloads, reader/player DTOs, and worldline isolation paths. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening member media metadata redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-006.
- Finding: F-006 found member-readable media asset, context, input, tag, collection, item, references, and lineage DTOs carrying admin-authored arbitrary metadata without response sanitization.
- Summary: Added an architecture-contracts OpenSpec delta for member media metadata-bearing DTO redaction, then added API-layer recursive member metadata sanitization. Member responses now omit sensitive metadata keys and leak-pattern values such as storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, and base64 while retaining safe metadata. Admin responses preserve full metadata.
- Files changed: backend/services/api/src/noveland/services/api/media.py, backend/tests/test_api_media.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added a Media API regression that writes leaky metadata through visible asset/context/input/tag/collection/item records, verifies member top-level and nested metadata is sanitized, and verifies admin asset/reference metadata preserves internal fields.
- Verification: uv run pytest tests/test_api_media.py tests/test_api_reader_media.py passed with 14 passed; uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py passed; uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for world event payloads, reader/player DTOs, and worldline isolation paths, then move to Web/e2e security. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening realtime member stream redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-007.
- Finding: F-007 found member-authenticated realtime world and conversation streams exposing admin diagnostics, agent run prompt/response text, run diagnostics, hidden/unpublished narrative artifacts, and conversation policy/writer internals.
- Summary: Added an architecture-contracts OpenSpec delta for member realtime stream shaping, then made world and conversation stream payloads role-aware. World admins retain operator diagnostics and execution details; ordinary members receive safe clock, reader-visible published narrative artifacts, safe conversation updates, and no diagnostic/run internals. Conversation live snapshots now apply the same member-safe shaping.
- Files changed: backend/services/api/src/noveland/services/api/realtime.py, backend/tests/test_api_realtime.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Realtime API regressions compare admin vs member world stream payloads, member vs admin conversation stream payloads, and member WebSocket live snapshots.
- Verification: uv run pytest tests/test_api_realtime.py passed with 6 passed; uv run ruff check services/api/src/noveland/services/api/realtime.py tests/test_api_realtime.py passed; uv run mypy services/api/src/noveland/services/api/realtime.py tests/test_api_realtime.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for non-realtime reader/player DTOs, worldline isolation, and Web/e2e security. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening agent run list redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-008.
- Finding: F-008 found the member-readable agent run list REST API exposing run prompt_text, response_text, provider_profile_id, and diagnostics to ordinary world members.
- Summary: Added an architecture-contracts OpenSpec delta for member agent runtime run list shaping, then made list_agent_runs role-aware. World admins retain operator run internals; ordinary members receive safe run identifiers, status/source linkage, and timing fields with prompt, response, provider, and diagnostics redacted.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded agent run API regression coverage to compare admin run list internals with member redacted run list payloads while preserving worldline filtering coverage.
- Verification: uv run pytest tests/test_api_worlds.py::test_agent_runs_and_narrative_artifacts_api tests/test_api_worlds.py::test_agent_run_apis_filter_by_worldline passed with 2 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for remaining non-realtime reader/player/member DTOs and worldline isolation, then Web/e2e security. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening agent catalog redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-009.
- Finding: F-009 found the member-readable agent catalog REST API exposing provider_profile_id and full agent config to ordinary world members.
- Summary: Added an architecture-contracts OpenSpec delta for member agent catalog shaping, then made list_agents role-aware. World admins retain provider/config details; ordinary members receive safe public agent identity and characterization fields with provider refs and config redacted.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded agent preset/materialization API coverage to compare admin agent catalog provider/config visibility against member-redacted catalog payloads.
- Verification: uv run pytest tests/test_api_worlds.py::test_create_agent_from_preset_materializes_persona_calendar_and_provider_mapping tests/test_api_worlds.py::test_world_admin_manages_scenes_agents_and_conflicts tests/test_api_worlds.py::test_agent_runs_and_narrative_artifacts_api passed with 3 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for remaining member-readable worlds.py DTOs, reader/player DTOs, and worldline isolation. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening world profile redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-010.
- Finding: F-010 found member-readable world profile/list REST APIs exposing rules_config, memory backend profile refs, memory plugin config, world rules plugin identifiers, and plugin config to ordinary world members.
- Summary: Added an architecture-contracts OpenSpec delta for member world profile shaping, then made world list/get responses role-aware. Platform/world admins retain world configuration details; ordinary members receive safe public world identity fields with rules, plugin identifiers/config, and backend profile refs redacted.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded member world read regression coverage to compare admin world profile config visibility against member list/get redaction.
- Verification: uv run pytest tests/test_api_worlds.py::test_world_member_can_read_but_not_mutate_and_non_member_is_hidden tests/test_api_worlds.py::test_platform_admin_can_create_list_and_update_worlds passed with 2 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for remaining member-readable worlds.py DTOs, reader/player DTOs, and worldline isolation. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening schedule rule redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-011.
- Finding: F-011 found the member-readable schedule rule list REST API exposing WorldScheduleRule config to ordinary world members.
- Summary: Added an architecture-contracts OpenSpec delta for member schedule rule shaping, then made list_schedule_rules role-aware. World admins retain full rule config; ordinary members receive safe rule identity, kind, and enabled state with config redacted.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded calendar/schedule API coverage to compare admin schedule rule config visibility against member-redacted rule list payloads.
- Verification: uv run pytest tests/test_api_worlds.py::test_world_admin_manages_calendar_entries_and_schedule_rules tests/test_api_worlds.py::test_world_composition_export_and_import_round_trip passed with 2 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for remaining member-readable worlds.py DTO metadata/source fields, reader/player DTOs, and worldline isolation. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening narrative artifact REST redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-012.
- Finding: F-012 found member-readable narrative artifact list/detail REST APIs exposing source_run_id, artifact metadata, continuity metadata/status, publication metadata, source_draft_id, published_by_user_id, and publication_gate to ordinary world members.
- Summary: Added an architecture-contracts OpenSpec delta for member narrative artifact REST shaping, then made narrative artifact list/detail responses role-aware. World admins retain artifact metadata and publication review evidence; ordinary members receive safe published artifact content, identity, conversation linkage, publication status, reader visibility, and timing with operator internals redacted.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded narrative reader API coverage to compare member-redacted artifact/publication internals against admin-preserved source run, metadata, continuity, and publication gate fields while retaining publication visibility behavior.
- Verification: uv run pytest tests/test_api_worlds.py::test_narrative_reader_api_supports_filters_and_detail_for_world_members tests/test_api_worlds.py::test_narrative_publication_workflow_filters_reader_visibility tests/test_api_realtime.py::test_world_stream_hides_admin_evidence_for_member_payloads passed with 3 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py tests/test_api_realtime.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py tests/test_api_realtime.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs.
- Follow-up notes: Continue backend audit for remaining member-readable worlds.py DTO metadata/source fields, player/reader DTOs, and worldline isolation. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening organization list redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-013.
- Finding: F-013 found the member-readable organization list REST API exposing hidden_summary and arbitrary organization metadata to ordinary world members.
- Summary: Added an architecture-contracts OpenSpec delta for member organization list shaping, then made organization list responses role-aware. World admins retain hidden summaries and metadata; ordinary members receive safe public organization identity, description, public_summary, active state, and timing with hidden internals redacted.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded organization membership/faction track API coverage to compare admin organization hidden_summary/metadata preservation against member-redacted organization list payloads.
- Verification: uv run pytest tests/test_api_worlds.py::test_organization_memberships_and_faction_tracks_append_events passed with 1 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs.
- Follow-up notes: Continue backend audit for remaining organization membership/faction track metadata, player/reader DTOs, and worldline isolation. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening journal/notification/intervention redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-019.
- Finding: F-019 found member-readable player journal, in-world notification, and player intervention REST APIs exposing source evidence refs, intervention prompt text, choice/event linkage, and arbitrary metadata to ordinary world members.
- Summary: Added an architecture-contracts OpenSpec delta for member journal, notification, and intervention response shaping, then made the relevant worlds API helpers role-aware. World admins retain source refs, prompt text, choice/event linkage, and metadata; ordinary members receive safe title/body/status/target/timing fields with internals redacted.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded guardrail/player interaction API coverage to compare admin-preserved journal/notification/intervention internals against member-redacted payloads for source refs, prompt text, choice/event linkage, and metadata.
- Verification: uv run pytest tests/test_api_worlds.py::test_knowledge_player_guardrail_apis_and_acceptance_gap_fixes passed; uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for member-readable agent relationship metadata, calendar metadata, remaining source/evidence DTOs, and broader worldline isolation. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening relationship/calendar metadata redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-020.
- Finding: F-020 found member-readable agent relationship list and agent calendar list REST APIs exposing arbitrary relationship/scheduling metadata to ordinary world members.
- Summary: Added an architecture-contracts OpenSpec delta for member relationship and calendar metadata shaping, then made the relevant worlds API list responses role-aware. World admins retain relationship/calendar metadata; ordinary members receive safe relationship identity/score fields and calendar title/time/status fields with metadata redacted.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded relationship graph and calendar/schedule API coverage to compare admin-preserved metadata against member-redacted relationship/calendar list payloads.
- Verification: uv run pytest tests/test_api_worlds.py::test_agent_relationship_graph_enforces_world_scope_and_updates_edges tests/test_api_worlds.py::test_world_admin_manages_calendar_entries_and_schedule_rules passed with 2 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for remaining member-readable source/evidence refs, worldline isolation checks, and forbidden-data paths before moving to Web/e2e security. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening latest snapshot redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-021.
- Finding: F-021 found the member-readable latest snapshot REST API exposing snapshot payload, payload_uri, payload_location, and metadata to ordinary world members.
- Summary: Added an architecture-contracts OpenSpec delta for member latest snapshot shaping, then made the latest snapshot response role-aware. World admins retain snapshot payload/storage diagnostics; ordinary members receive safe snapshot identity, worldline, sequence coverage, schema/status, created-by event ref, and creation time with payload, payload_uri, payload_location, and metadata redacted.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded replay/snapshot API coverage to compare admin-preserved latest snapshot storage metadata against ordinary member-redacted latest snapshot payloads.
- Verification: uv run pytest tests/test_api_worlds.py::test_replay_and_snapshot_api_reads_state_and_creates_snapshot passed with 1 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for remaining member-readable source/evidence refs, release profile/world bible/presence DTOs, worldline isolation checks, and forbidden-data paths before moving to Web/e2e security. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening release profile redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-022.
- Finding: F-022 found the member-readable release profile REST API exposing release policies, checklist gate evidence, and metadata to ordinary world members.
- Summary: Added an architecture-contracts OpenSpec delta for member release profile shaping, then made the release profile response role-aware. World admins retain policies, checklist, gate decision, and metadata; ordinary members receive safe profile identity, status, and timing fields with branch_policy, backup_policy, content_review_policy, player_permission_policy, worldline_policy, checklist, and metadata redacted to empty objects.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded beta release readiness API coverage to compare admin-preserved release profile gate evidence against ordinary member-redacted release profile fields.
- Verification: uv run pytest tests/test_api_worlds.py::test_beta_release_readiness_apis_cover_routes_evals_authoring_and_checklist passed with 1 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for remaining member-readable source/evidence refs, world bible, presence/scheduled movement DTOs, worldline isolation checks, and forbidden-data paths before moving to Web/e2e security. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening world bible redaction entry

- Date: 2026-06-08
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-023.
- Finding: F-023 found the member-readable world bible REST API exposing raw source material/import notes, continuity config, and metadata to ordinary world members.
- Summary: Added an architecture-contracts OpenSpec delta for member world bible shaping, then made the world bible response role-aware. World admins retain source material, continuity config, and metadata; ordinary members receive safe canon timeline, setting rules, forbidden changes, sequel boundaries, continuity status, identity, and timing fields with source_material blanked and continuity_config/metadata redacted to empty objects.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded world bible API coverage to compare admin-preserved source/config/metadata fields against ordinary member-redacted world bible payloads while preserving continuity status.
- Verification: uv run pytest tests/test_api_worlds.py::test_world_bible_api_preserves_continuity_contract_and_access passed with 1 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for remaining member-readable source/evidence refs, presence/scheduled movement DTOs, worldline isolation checks, and forbidden-data paths before moving to Web/e2e security. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening agent presence redaction entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-024.
- Finding: F-024 found the member-readable agent presence REST API exposing scheduled_movement and last_event_id to ordinary world members.
- Summary: Added an architecture-contracts OpenSpec delta for member agent presence shaping, then made get_agent_presence role-aware. World admins retain scheduled movement plans and last event linkage; ordinary members receive safe current scene, visibility, encounter eligibility, identity, worldline, and timing fields with scheduling internals redacted.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded location graph and agent presence API coverage to compare admin-preserved scheduled movement and last event linkage against ordinary member-redacted presence payloads while preserving safe current-scene and visibility fields.
- Verification: uv run pytest tests/test_api_worlds.py::test_location_graph_and_agent_presence_enforce_world_scope passed with 1 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for remaining member-readable source/evidence refs, worldline isolation checks, and forbidden-data paths before moving to Web/e2e security. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening conversation session redaction entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-025.
- Finding: F-025 found member-readable conversation session list/detail REST APIs exposing objective text, opening prompts, policy, writer/provider/plugin config, memory config, and group context to ordinary world members.
- Summary: Added an architecture-contracts OpenSpec delta for member conversation session shaping, then made conversation list/detail responses role-aware. World admins retain conversation orchestration internals; ordinary members receive safe session identity, worldline, scene, title, scope, mode, status, turn counters, terminal state, and timing fields with orchestration internals redacted.
- Files changed: backend/services/api/src/noveland/services/api/conversations.py, backend/tests/test_api_conversations.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded conversation API access coverage to compare admin-preserved objective/opening prompt, policy, writer config, memory config, and group context against ordinary member-redacted list/detail payloads while preserving safe session fields and turn access.
- Verification: uv run pytest tests/test_api_conversations.py::test_conversation_api_enforces_access_and_manual_advance passed with 1 passed; uv run ruff check services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py passed; uv run mypy services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for remaining conversation narrative artifact metadata/source refs, other member-readable DTOs, worldline isolation checks, and forbidden-data paths before moving to Web/e2e security. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening conversation narrative artifact redaction entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-026.
- Finding: F-026 found the member-readable conversation-scoped narrative artifact list REST API exposing draft/unpublished/non-reader-visible conversation artifacts plus source_run_id and arbitrary metadata to ordinary world members.
- Summary: Added an architecture-contracts OpenSpec delta for member conversation narrative artifact list shaping, then made the conversation narrative list role-aware. World admins retain full draft visibility, source refs, and metadata; ordinary members receive only published reader-visible artifacts for that conversation with source_run_id and metadata redacted.
- Files changed: backend/services/api/src/noveland/services/api/conversations.py, backend/tests/test_api_conversations.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added conversation narrative list coverage that seeds published, draft, and non-reader-visible artifacts, then compares member filtered/redacted output against admin-preserved output.
- Verification: uv run pytest tests/test_api_conversations.py::test_conversation_narrative_listing_redacts_member_evidence tests/test_api_conversations.py::test_conversation_narrative_generation_and_listing passed with 2 passed; uv run ruff check services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py passed; uv run mypy services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for remaining member-readable DTOs, worldline isolation checks, and forbidden-data paths before moving to Web/e2e security. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening player privacy export evidence redaction entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-027.
- Finding: F-027 found the member-readable player privacy export REST API exposing journal/notification source refs and intervention choice/event linkage to ordinary world members, bypassing the F-019 player/member redaction boundary.
- Summary: Added architecture-contracts and player-privacy OpenSpec deltas for privacy export evidence shaping, then redacted journal and notification source_ref plus intervention choice_id/event_id from player privacy export payloads. Safe player-owned titles, bodies, choices, statuses, target identity fields, counts, and timing remain exported.
- Files changed: backend/packages/player_privacy/src/noveland/player_privacy/service.py, backend/tests/test_api_player_privacy.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/player-privacy-data-controls/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded player privacy export API coverage to seed journal source refs, notification source refs, and intervention choice/event linkage, then assert exported values are redacted to null while existing forbidden marker checks still pass.
- Verification: uv run pytest tests/test_api_player_privacy.py::test_player_privacy_export_is_player_scoped_and_redacted passed with 1 passed; uv run ruff check packages/player_privacy/src/noveland/player_privacy/service.py tests/test_api_player_privacy.py passed; uv run mypy packages/player_privacy/src/noveland/player_privacy/service.py tests/test_api_player_privacy.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for remaining member-readable DTOs, worldline isolation checks, and forbidden-data paths before moving to Web/e2e security. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening scene/location rule redaction entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-028.
- Finding: F-028 found member-readable scene and location graph REST APIs exposing scene opening_rules and location traversal_rules to ordinary world members.
- Summary: Added an architecture-contracts OpenSpec delta for member scene/location graph rule shaping, then made scene and location-edge list responses role-aware. World admins retain opening/traversal rule config; ordinary members receive safe scene/location identity, public descriptions, region/location tags, travel labels, active state, and timing fields with rule config redacted.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded location graph and agent presence API coverage to seed opening/traversal rule configs with forbidden markers, then compare admin-preserved scene/location graph output against ordinary member-redacted output.
- Verification: uv run pytest tests/test_api_worlds.py::test_location_graph_and_agent_presence_enforce_world_scope passed with 1 passed; uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for remaining member-readable DTOs, worldline isolation checks, and forbidden-data paths before moving to Web/e2e security. Do not push unless explicitly requested.


## Post-v1.1 RC Audit and Hardening conversation turn redaction entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: backend forbidden-data exposure remediation for F-029.
- Finding: F-029 found member-readable conversation turn REST responses exposing runtime run_id and provider/plugin error_text to ordinary world members.
- Summary: Added an architecture-contracts OpenSpec delta for member conversation turn shaping, then made turn list responses role-aware. World admins retain run IDs and error text; ordinary members receive safe turn identity, speaker, transcript text, status, and timing fields with runtime evidence redacted.
- Files changed: backend/services/api/src/noveland/services/api/conversations.py, backend/tests/test_api_conversations.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded conversation API access coverage to assert admin advance responses preserve run evidence while ordinary member turn list responses redact run_id and error_text.
- Verification: uv run pytest tests/test_api_conversations.py::test_conversation_api_enforces_access_and_manual_advance passed with 1 passed; uv run ruff check services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py passed; uv run mypy services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py passed; openspec validate audit-and-hardening-post-v1-1-rc --strict passed; openspec validate --specs --strict passed with 76 specs; git diff --check passed before commit.
- Follow-up notes: Continue backend audit for remaining member-readable DTOs, worldline isolation checks, and forbidden-data paths before moving to Web/e2e security. Do not push unless explicitly requested.


## Post-v1.1 RC Audit and Hardening Web daily-life/offscreen client path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web/e2e security remediation for F-044.
- Finding: F-044 found browser-side daily-life preview/generation/candidate and offscreen event create/list/resolve helpers appending decoded world identifiers directly into same-origin API paths.
- Summary: Added an architecture-contracts OpenSpec delta for daily-life/offscreen client route-boundary preservation, then encoded the scoped world path segment in the affected helpers while keeping query filters in URLSearchParams.
- Files changed: web/lib/worlds/client.ts, web/lib/worlds/client.test.ts, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added focused worlds client coverage proving reserved characters in daily-life/offscreen world identifiers stay inside encoded same-origin path segments and worldline filters remain query data.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 29 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 152 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue Web/e2e audit for remaining living-world helper groups in web/lib/worlds/client.ts, plus Next route handlers, CSRF forwarding, method exposure, response header behavior, client-side data leaks, XSS-prone rendering sinks, and admin/player/member boundary leaks. Do not push unless explicitly requested.


## Post-v1.1 RC Audit and Hardening Web story/route client path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web/e2e security remediation for F-045.
- Finding: F-045 found browser-side story hook, plot thread, route affinity, route milestone, ending candidate, long-run eval, authoring template, release profile, and beta checklist helpers appending decoded world and nested identifiers directly into same-origin API paths.
- Summary: Added an architecture-contracts OpenSpec delta for story/route/ending/authoring/release/beta client route-boundary preservation, then encoded the scoped world, ending, authoring template, and checklist run path segments while keeping query filters in URLSearchParams/worldlineSuffix.
- Files changed: web/lib/worlds/client.ts, web/lib/worlds/client.test.ts, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added focused worlds client coverage proving reserved characters in story/route world, worldline, agent, ending, authoring template, and beta checklist run identifiers stay inside encoded same-origin path segments and query filters remain query data.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 30 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 153 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue Web/e2e audit for remaining living-world helper groups in web/lib/worlds/client.ts, especially event trigger conditions, scene beats, daily episodes, group interactions, relationship suggestions, organization conflicts, rumors, knowledge, secrets, emotional states, relationship repairs, player journal/notifications/interventions, reviews, agent memory/persona/observations/runs, narrative artifacts, membership/member candidates, and diagnostics. Do not push unless explicitly requested.


## Post-v1.1 RC Audit and Hardening Web knowledge/review client path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web/e2e security remediation for F-047.
- Finding: F-047 found browser-side knowledge, secret, emotional state, relationship repair, player journal, notification, intervention, player privacy, GM style review, and narrative continuity review helpers appending decoded world and nested identifiers directly into same-origin API paths.
- Summary: Added an architecture-contracts OpenSpec delta for knowledge/secret/player/privacy/review client route-boundary preservation, then encoded the scoped world, secret, and relationship repair path segments while keeping query filters in URLSearchParams/searchSuffix.
- Files changed: web/lib/worlds/client.ts, web/lib/worlds/client.test.ts, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added focused worlds client coverage proving reserved characters in knowledge/review world, worldline, agent, user, secret, and relationship repair identifiers stay inside encoded same-origin path segments and query filters remain query data.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 32 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 155 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import.
- Follow-up notes: Continue Web/e2e audit for remaining helper groups in web/lib/worlds/client.ts, especially agent memory/persona/observations/runs, narrative artifacts, memberships, member candidates, and diagnostics, plus Next route handlers, proxy CSRF forwarding, response header behavior, and client-side rendering sinks. Do not push unless explicitly requested.


## Post-v1.1 RC Audit and Hardening Web agent/narrative client path boundary entry

- Date: 2026-06-09
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web/e2e security remediation for F-048.
- Finding: F-048 found browser-side agent memory, memory profile snapshot, agent run, agent persona, agent observation, manual agent run, narrative artifact, publish/unpublish, agent update, and agent deactivate helpers appending decoded world and nested identifiers directly into same-origin API paths.
- Summary: Added an architecture-contracts OpenSpec delta for agent memory/run/persona/observation/narrative client route-boundary preservation, then encoded the scoped world, agent, run, and narrative artifact path segments while keeping narrative artifact filters in URLSearchParams.
- Files changed: web/lib/worlds/client.ts, web/lib/worlds/client.test.ts, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added focused worlds client coverage proving reserved characters in agent/narrative world, agent, run, artifact, and source conversation identifiers stay inside encoded same-origin path segments and query filters remain query data.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 33 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 156 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import.
- Follow-up notes: Continue Web/e2e audit for remaining helper groups in web/lib/worlds/client.ts, especially memberships, member candidates, diagnostics, and any residual raw same-origin path construction, plus Next route handlers, proxy CSRF forwarding, response header behavior, and client-side rendering sinks. Do not push unless explicitly requested.


## Post-v1.1 RC Audit and Hardening Web membership/diagnostics client path boundary entry

- Date: 2026-06-10
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web/e2e security remediation for F-049.
- Finding: F-049 found browser-side membership list/upsert/delete, member candidate search, and world diagnostics helpers appending decoded world and user identifiers directly into same-origin API paths.
- Summary: Added an architecture-contracts OpenSpec delta for membership/candidate/diagnostics client route-boundary preservation, then encoded the scoped world and membership user path segments while keeping member candidate filters in URLSearchParams.
- Files changed: web/lib/worlds/client.ts, web/lib/worlds/client.test.ts, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added focused worlds client coverage proving reserved characters in membership/diagnostics world and user identifiers stay inside encoded same-origin path segments and candidate search text remains query data.
- Verification: `npm run test -- lib/worlds/client.test.ts` passed with 34 passed; `npm run typecheck` passed; `npm run lint` passed; full `npm run test` passed with 45 files and 157 tests, with existing runtime-admin React act warnings; `npm run build` passed; `npm run test:e2e` passed with 21 passed; `npm run check:next-env` initially failed after e2e/dev regenerated `next-env.d.ts` to `.next/dev/types/routes.d.ts`, then passed after restoring the expected `.next/types/routes.d.ts` import.
- Follow-up notes: Browser-side `web/lib/worlds/client.ts` no longer has raw `/api/worlds/${worldId}` path construction. Continue Web/e2e audit for other client/proxy modules and Next route handlers, especially CSRF forwarding, response header behavior, role boundary, evidence redaction, and client-side rendering sinks. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web EventSource route boundary entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web/e2e security remediation for F-060.
- Finding: F-060 found browser-side world and conversation EventSource subscriptions constructing same-origin stream URLs from decoded world and conversation identifiers without encoding dynamic path segments before the browser requested the Next API route.
- Summary: Added an architecture-contracts OpenSpec scenario for EventSource route-boundary preservation, introduced `worldEventStreamPath()` and `conversationEventStreamPath()` in the realtime helper, and routed world overview, narrative workspace, narrative reader, and conversation detail stream subscriptions through those helpers.
- Files changed: web/lib/realtime.ts, web/lib/realtime.test.ts, web/features/worlds/world-overview.tsx, web/features/worlds/world-overview.test.tsx, web/features/worlds/narrative-workspace.tsx, web/features/worlds/narrative-workspace.test.tsx, web/features/worlds/narrative-reader.tsx, web/features/worlds/narrative-reader.test.tsx, web/features/conversations/conversation-detail.tsx, web/features/conversations/conversation-detail.test.tsx, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added realtime helper coverage plus component assertions proving reserved world and conversation identifiers stay encoded inside EventSource route path segments.
- Verification: `cd web && npm run test -- lib/realtime.test.ts features/conversations/conversation-detail.test.tsx features/worlds/world-overview.test.tsx features/worlds/narrative-workspace.test.tsx features/worlds/narrative-reader.test.tsx` passed with 5 files and 18 tests; `cd web && npm run lint` passed; `cd web && npm run typecheck` passed; full `cd web && npm run test` passed with 51 files and 184 tests, with existing RuntimeAdmin React act warnings; `cd web && npm run build` passed; `cd web && npm run test:e2e -- --grep publication blockers` passed after one initial full-suite transient miss on that test; rerun full `cd web && npm run test:e2e` passed with 21 tests; `cd web && npm run check:next-env` passed after restoring the expected `.next/types/routes.d.ts` import; `openspec validate audit-and-hardening-post-v1-1-rc --strict` passed; `openspec validate --changes --strict` passed with 1 passed; `openspec validate --specs --strict` passed with 76 specs; `git diff --check` passed.
- Follow-up notes: Continue Web/e2e audit for remaining route handlers, client-side data leaks, role boundary/evidence redaction, and product normal-use flow drift. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening Web beta feedback server-loader route boundary entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web/e2e security remediation for F-061.
- Finding: F-061 found `web/lib/beta-feedback/server.ts` constructing backend worldline, feedback report, and membership fetch paths from decoded Next route world identifiers.
- Summary: Added an architecture-contracts OpenSpec scenario for beta feedback server-loader route-boundary preservation, encoded the world segment once in `getBetaFeedbackData()`, and added focused server-loader coverage for reserved world identifiers.
- Files changed: web/lib/beta-feedback/server.ts, web/lib/beta-feedback/server.test.ts, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added `web/lib/beta-feedback/server.test.ts` to assert backend URLs keep reserved world identifier characters encoded inside the world path segment.
- Verification: `cd web && npm run test -- lib/beta-feedback/server.test.ts lib/beta-feedback/client.test.ts features/private-beta/beta-feedback-panel.test.tsx` passed with 3 files and 6 tests; `cd web && npm run lint` passed; `cd web && npm run typecheck` passed; full `cd web && npm run test` passed with 52 files and 185 tests, with existing RuntimeAdmin React act warnings; `cd web && npm run build` passed; `cd web && npm run test:e2e` passed with 21 tests; `cd web && npm run check:next-env` passed after restoring the expected `.next/types/routes.d.ts` import; OpenSpec validation passed and `git diff --check` passed.
- Follow-up notes: Continue Web/e2e audit for remaining server loaders outside `web/lib/worlds/server.ts`, route handlers, role boundary/evidence redaction, and product normal-use flow drift. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening Reader media worldline-scoped download entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend/Web security remediation for F-062.
- Finding: F-062 found reader media object download URLs and the default backend download route omitted worldline scope, allowing same-world reader-visible object bytes from another fork to be served when the object UUID was known.
- Summary: Added an architecture-contracts OpenSpec scenario for scoped reader media object delivery, generated reader media descriptor download URLs with worldline path scope, rejected unscoped legacy reader media object downloads before storage reads, and tightened Web reader media URL validation to exact UUID world/worldline/object download paths.
- Files changed: backend/packages/reader_delivery/src/noveland/reader_delivery/service.py, backend/services/api/src/noveland/services/api/reader_media.py, backend/tests/test_api_reader_media.py, backend/tests/test_api_moderation.py, web/lib/worlds/media.ts, web/lib/worlds/media.test.ts, web/features/worlds/conversation-playback.test.tsx, web/features/worlds/conversation-scene-view.test.tsx, web/tests/e2e/start-with-mock-auth.mjs, web/tests/e2e/auth.spec.ts, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added backend reader media assertions for scoped download success, unscoped legacy download 404, and cross-worldline scoped path rejection; updated Web helper/component/e2e expectations for worldline-scoped reader media paths.
- Verification: `cd backend && uv run pytest tests/test_api_moderation.py::test_applied_moderation_takedown_hides_reader_media_without_admin_route_change tests/test_api_reader_media.py` passed with 6 tests; focused backend ruff/mypy passed; full `cd backend && uv run pytest` passed with 563 passed and 8 skipped; focused Web reader media tests passed with 3 files and 13 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, full `cd web && npm run test`, `cd web && npm run build`, focused and full `cd web && npm run test:e2e`, `cd web && npm run check:next-env`, OpenSpec strict validations, and `git diff --check` passed.
- Follow-up notes: Continue backend worldline isolation audit for provider smoke/fallback/test invocation routes, observability readiness, visual/speech generation services, and product normal-use/spec drift. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening Speech voice profile reference boundary entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-063.
- Finding: F-063 found world-level voice profiles could carry `reference_asset_id` values pointing at fork-scoped audio assets because validation skipped exact worldline matching whenever the profile's `worldline_id` was null.
- Summary: Added an architecture-contracts OpenSpec scenario for world-level voice profile media-reference isolation, rejected reference media on world-level voice profiles, and preserved same-worldline audio reference validation for scoped voice profiles.
- Files changed: backend/packages/speech/src/noveland/speech/voice_profiles.py, backend/tests/test_voice_profiles.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added a voice profile service regression proving a world-level profile cannot reference a worldline-scoped audio media asset.
- Verification: `cd backend && uv run pytest tests/test_voice_profiles.py` passed with 4 tests; `cd backend && uv run pytest tests/test_speech_service.py tests/test_api_speech.py tests/test_voice_profiles.py` passed with 11 tests; focused backend ruff/mypy passed; full `cd backend && uv run pytest` passed with 564 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue backend worldline isolation and forbidden-evidence audits for remaining speech service/API outputs, memory, player sessions, beta feedback, moderation, observability, and product/spec drift. Do not push unless explicitly requested after this batch commit.


## Post-v1.1 RC Audit and Hardening Beta feedback reporter triage evidence entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-064.
- Finding: F-064 found reporter-owned beta feedback reads returned full admin triage evidence after operator triage, including admin-set media job/invocation evidence refs, repair proposal refs, moderation refs, actor refs, and metadata.
- Summary: Added an architecture-contracts OpenSpec scenario for beta feedback reporter/admin evidence separation, made `BetaFeedbackService._read()` role-aware, preserved full evidence for admin reads, and restricted reporter reads to safe report status/severity plus reporter-safe evidence kinds with metadata stripped.
- Files changed: backend/packages/beta_feedback/src/noveland/beta_feedback/service.py, backend/tests/test_api_beta_feedback.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended beta feedback API coverage so admin triage can attach media job/invocation evidence and repair refs, while reporter detail reads after triage hide admin-only fields.
- Verification: `cd backend && uv run pytest tests/test_api_beta_feedback.py` passed with 4 tests; `cd backend && uv run pytest tests/test_api_moderation.py tests/test_api_authoring.py` passed with 19 tests; focused backend ruff/mypy passed; OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue backend forbidden-evidence audits for moderation, observability, privacy export contents, speech/API output, and remaining member/player DTOs. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening Observability diagnostics redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-065.
- Finding: F-065 found runtime diagnostics only redacted details by sensitive key, while event_type/message and safe-key detail values could preserve secret-looking values, storage locators, filesystem paths, raw prompt/output markers, bytes, or base64. Focused observability tests also exposed a package import cycle through conversations importing the top-level observability package during observability service import.
- Summary: Added an observability OpenSpec scenario for diagnostic text/value redaction, broke the conversations-to-observability package import cycle with a lazy diagnostics service lookup, redacted sensitive marker values before diagnostic persistence, and reapplied redaction on read for historical records.
- Files changed: backend/packages/observability/src/noveland/observability/services.py, backend/packages/conversations/src/noveland/conversations/services.py, backend/tests/test_observability.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/observability-incident-diagnostics/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded observability unit coverage for value-level redaction in diagnostic details and for event_type/message/details redaction through RuntimeDiagnosticsService record/list paths.
- Verification: `cd backend && uv run pytest tests/test_observability.py tests/test_observability_incidents.py -q` passed with 6 tests; `cd backend && uv run pytest tests/test_api_conversations.py tests/test_api_realtime.py tests/test_api_worlds.py::test_world_diagnostics_require_world_admin -q` passed with 13 tests; focused backend ruff/mypy passed; full `cd backend && uv run pytest` passed with 564 passed and 8 skipped; full `cd backend && uv run ruff check .` and `cd backend && uv run mypy .` passed.
- Follow-up notes: Continue backend forbidden-evidence audits for privacy export contents, speech/API output, remaining player/member DTOs, and then resume Web/e2e/product/spec-history batches. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening Speech safe response entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-066.
- Finding: F-066 found `POST /worlds/{world_id}/speech/tts` returning `output_asset.storage_uri` and `output_objects[].storage_uri` internal `media://...` locators plus raw invocation text in the speech test response.
- Summary: Added a speech-admin-console OpenSpec scenario for safe TTS/STT test responses, introduced speech-specific API response DTOs, and shaped TTS/STT responses to preserve safe IDs, world/worldline scope, status, MIME/checksum metadata, transcript text, and invocation IDs while omitting media storage locators, media job request/result internals, and raw invocation text/json/error fields.
- Files changed: backend/services/api/src/noveland/services/api/speech.py, backend/tests/test_api_speech.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/speech-admin-console/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Expanded the speech API integration test to assert TTS/STT responses do not contain `storage_uri`, `media://`, media job request/result/config fields, or raw invocation payload fields.
- Verification: `cd backend && uv run pytest tests/test_api_speech.py -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_speech.py tests/test_speech_service.py tests/test_voice_profiles.py -q` passed with 11 tests; focused backend ruff/mypy passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 564 passed and 8 skipped.
- Follow-up notes: Continue backend forbidden-evidence audits for privacy export contents, remaining player/member DTOs, and worldline isolation edge cases, then continue Web/e2e route-handler and product normal-use audits. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening Player actor profile redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-067.
- Finding: F-067 found member-readable player actor bind/list responses returning arbitrary `PlayerActorProfile.profile_json`, allowing storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, or base64-looking values to reach ordinary world members when profile metadata was admin-authored or historically dirty.
- Summary: Added an architecture-contracts OpenSpec scenario for member player actor profile redaction, sanitized profile JSON on player actor bind before persistence, and sanitized profile JSON again in `_player_actor_response()` for historical records.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended the member player interaction API test to prove dirty bind profiles persist only safe fields and simulated historical dirty profiles are redacted on member list responses.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 38 tests; focused backend ruff/mypy passed for `worlds.py` and `test_api_worlds.py`; full backend ruff, mypy, and pytest passed with 564 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue backend forbidden-evidence audits for remaining member/player DTOs, player privacy export contents, worldline isolation edge cases, and then continue Web/e2e route-handler and product normal-use audits. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening Agent character profile redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-068.
- Finding: F-068 found the member-readable agent catalog returning arbitrary `Agent.character_profile` JSON even after F-009 redacted provider profile IDs and config for members. Dynamic API verification showed a world admin could create an agent with `character_profile.storage_uri=media://private/agent-profile` and nested `raw_prompt=operator prompt`, and an ordinary member `GET /agents` response returned those forbidden values verbatim.
- Summary: Added an architecture-contracts OpenSpec scenario for member agent character profile redaction, generalized the public profile sanitizer from player actor profiles, applied it to non-admin agent catalog responses, and left admin authoring/list responses unchanged.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended agent preset/materialization API coverage so admin agent responses retain full dirty character profile metadata while member agent catalog responses retain only safe public characterization fields.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_create_agent_from_preset_materializes_persona_calendar_and_provider_mapping -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope tests/test_api_worlds.py::test_create_agent_from_preset_materializes_persona_calendar_and_provider_mapping -q` passed with 2 tests; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 38 tests; focused backend ruff/mypy passed for `worlds.py` and `test_api_worlds.py`; full backend ruff, mypy, and pytest passed with 564 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue backend forbidden-evidence audits for remaining member/player DTOs, player privacy export contents, worldline isolation edge cases, and then continue Web/e2e route-handler and product normal-use audits. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening Player choice metadata redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-069.
- Finding: F-069 found member-readable player choice create/list responses redacting prompt text but returning arbitrary `PlayerChoiceRecord.context_json` and `consequence_preview` JSON. Dynamic API verification showed an ordinary member choice with `context.storage_uri=media://private/choice`, nested `raw_prompt=operator prompt`, and `effects.offscreen_events[].raw_output=provider output` returned those forbidden values on both create and list responses.
- Summary: Added an architecture-contracts OpenSpec scenario for member player choice metadata redaction, generalized the public sanitizer to member-facing JSON payloads, sanitized non-admin choice context and consequence preview responses, and blanked sensitive-looking selected-option text for non-admin reads while preserving full admin review metadata.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended member player interaction API coverage so member choice create/list responses retain safe context and diagnostics while omitting storage refs, filesystem paths, raw prompt/output markers, and unsafe values; admin choice list responses retain full dirty review metadata.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope tests/test_api_worlds.py::test_create_agent_from_preset_materializes_persona_calendar_and_provider_mapping -q` passed with 2 tests; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 38 tests; focused backend ruff/mypy passed for `worlds.py` and `test_api_worlds.py`; full backend ruff, mypy, and pytest passed with 564 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue backend forbidden-evidence audits for remaining member/player DTOs, player privacy export contents, worldline isolation edge cases, and then continue Web/e2e route-handler and product normal-use audits. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening Journal and notification text redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-070.
- Finding: F-070 found member-readable player journal and notification list responses hiding source refs and metadata but returning title/body text verbatim. Dynamic API verification showed admin-created member journal/notification records containing `raw_prompt`, `media://`, and `raw_output` markers in title/body text were returned to the ordinary member.
- Summary: Added an architecture-contracts OpenSpec scenario for journal/notification text redaction and applied the shared public text sanitizer to non-admin journal and notification title/body fields while preserving admin review responses.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended guardrail API coverage so admin reads retain raw journal/notification text and metadata while member reads blank sensitive-looking body/title text and omit source refs/metadata.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_knowledge_player_guardrail_apis_and_acceptance_gap_fixes -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 38 tests; focused backend ruff/mypy passed for `worlds.py` and `test_api_worlds.py`; full backend ruff, mypy, and pytest passed with 564 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue backend forbidden-evidence audits for remaining member/player DTOs, player privacy export contents, worldline isolation edge cases, and then continue Web/e2e route-handler and product normal-use audits. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening Player choice preview effect redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-071.
- Finding: F-071 found member-readable player choice preview responses hiding diagnostics but returning arbitrary `relationship_updates`, `faction_updates`, and `offscreen_events` effect JSON verbatim. Focused regression first reproduced an ordinary member preview response echoing `raw_prompt`, `media://`, `storage_uri`, `raw_output`, and `/root/` markers from request effect JSON.
- Summary: Added an architecture-contracts OpenSpec scenario for member player choice preview effect metadata redaction, introduced `_sanitize_public_json_list()`, and applied it to non-admin preview relationship, faction, and offscreen effect lists while preserving admin preview diagnostics and full effect metadata.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended the member player interaction API test so member preview responses keep safe effect fields while omitting forbidden markers and admin preview responses retain full dirty effect metadata.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope -q` passed with 1 test after first reproducing the raw `raw_prompt` preview leak; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 38 tests; focused backend `uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; focused backend `uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 564 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue auditing remaining member/player preview and dry-run surfaces for arbitrary JSON or text copied from request/admin metadata. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening Offscreen event payload persistence redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-072.
- Finding: F-072 found offscreen event resolution copying `OffscreenEventQueueItem.payload_json` directly into `WorldEventAppend(payload=...)`. Queue payloads can originate from admin offscreen creation, GM macro plans, player choice effects, or forked queue state, so unsafe storage refs, raw prompt/output markers, filesystem paths, secret/auth refs, bytes, or base64-like values could become persisted `world_events.payload` evidence.
- Summary: Added an architecture-contracts OpenSpec scenario for safe offscreen resolution payloads and introduced a domain-layer sanitizer in `LivingWorldAutonomyService.resolve_due_offscreen_events()` so historical or newly queued dirty payload JSON is filtered immediately before world event persistence while preserving safe event context fields.
- Files changed: backend/packages/worlds/src/noveland/worlds/autonomous.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added `test_offscreen_resolution_sanitizes_persisted_world_event_payload`, which creates a dirty due offscreen queue payload, resolves it, and asserts the persisted `WorldEventModel.payload` keeps safe summary/context fields while omitting forbidden keys and values.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_offscreen_resolution_sanitizes_persisted_world_event_payload -q` first failed on unredacted `storage_uri` persisted in `WorldEventModel.payload`, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 39 tests; focused backend `uv run ruff check packages/worlds/src/noveland/worlds/autonomous.py tests/test_api_worlds.py` passed; focused backend `uv run mypy packages/worlds/src/noveland/worlds/autonomous.py tests/test_api_worlds.py` passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 565 passed and 8 skipped. `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.
- Follow-up notes: Continue backend audits for remaining historical dirty content paths, provider/quota/worldline isolation edge cases, and then resume Web/e2e route-handler and product normal-use audits. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening GM proposal payload persistence redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-073.
- Finding: F-073 found GM proposal resolution copying arbitrary `GMEventProposal.proposed_payload` directly into `WorldEventAppend(payload=...)` when a proposal is reviewed as resolved. Proposed payload JSON can originate from admin input, macro planning, or provider-backed planning evidence, so unsafe storage refs, raw prompt/output markers, filesystem paths, secret/auth refs, bytes, or base64-like values could become persisted `world_events.payload` evidence.
- Summary: Added an architecture-contracts OpenSpec scenario for safe GM proposal resolution payloads, moved the F-072 offscreen event sanitizer into shared `noveland.worlds.sanitization.sanitize_world_event_payload()`, and applied it to both offscreen resolution and GM proposal resolution at the domain persistence boundary.
- Files changed: backend/packages/worlds/src/noveland/worlds/sanitization.py, backend/packages/worlds/src/noveland/worlds/autonomous.py, backend/packages/worlds/src/noveland/worlds/gm.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added `test_gm_proposal_resolution_sanitizes_persisted_world_event_payload`, which creates a dirty GM proposal payload, resolves it, and asserts the persisted `WorldEventModel.payload` keeps safe beat/context/proposal fields while omitting forbidden keys and values; reran the F-072 offscreen payload regression to cover the shared helper.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_gm_proposal_resolution_sanitizes_persisted_world_event_payload -q` first failed on unredacted `storage_uri` persisted in `WorldEventModel.payload`, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_worlds.py::test_offscreen_resolution_sanitizes_persisted_world_event_payload tests/test_api_worlds.py::test_gm_proposal_resolution_sanitizes_persisted_world_event_payload -q` passed with 2 tests; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 40 tests; focused backend ruff/mypy passed for `sanitization.py`, `autonomous.py`, `gm.py`, and `test_api_worlds.py`; full backend ruff, mypy, and pytest passed with 566 passed and 8 skipped. `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.
- Follow-up notes: Continue auditing remaining world event producers, especially secret reveal/consequence metadata and other historical dirty event payload paths, then resume Web/e2e route-handler and product normal-use audits. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening Event store payload safety enforcement entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-074.
- Finding: F-074 found `WorldEventStore.append_event()` persisted `event_input.payload` directly. F-072/F-073 protected offscreen and GM proposal producers, but other producers such as `LivingWorldGuardrailService.reveal_secret()` could still write arbitrary admin-authored metadata into `world_events.payload`.
- Summary: Added an architecture-contracts OpenSpec scenario requiring event-store-level payload safety, moved shared sanitization into `noveland.events.sanitization.sanitize_world_event_payload()`, enforced it in `WorldEventStore.append_event()`, and removed the temporary worlds-domain sanitizer plus producer-level calls.
- Files changed: backend/packages/events/src/noveland/events/sanitization.py, backend/packages/events/src/noveland/events/event_store.py, backend/packages/worlds/src/noveland/worlds/autonomous.py, backend/packages/worlds/src/noveland/worlds/gm.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added `test_event_store_sanitizes_secret_reveal_event_payload`, which creates a dirty secret consequence metadata payload, reveals the secret, and asserts the persisted `WorldEventModel.payload` keeps safe secret/consequence fields while omitting storage refs, filesystem paths, raw prompt/output markers, bytes, and base64-like values; reran F-072/F-073 regressions to prove the event-store enforcement covers those producers after removing producer-level calls.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_event_store_sanitizes_secret_reveal_event_payload -q` first failed on unredacted `storage_uri` persisted in `WorldEventModel.payload`, then passed after remediation; `cd backend && uv run pytest tests/test_api_worlds.py::test_offscreen_resolution_sanitizes_persisted_world_event_payload tests/test_api_worlds.py::test_gm_proposal_resolution_sanitizes_persisted_world_event_payload tests/test_api_worlds.py::test_event_store_sanitizes_secret_reveal_event_payload -q` passed with 3 tests; `cd backend && uv run pytest tests/test_api_worlds.py tests/test_event_contracts.py -q` passed with 49 tests; focused backend ruff/mypy passed for touched event/world/test files; full backend ruff, mypy, and pytest passed with 567 passed and 8 skipped. `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.
- Follow-up notes: Continue auditing non-event persistence and reader/member/Web exposure paths; Web was not changed in this batch, so Web gates were not run. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening World bible public canon JSON redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-075.
- Finding: F-075 found member-readable world bible responses hiding `source_material`, `continuity_config`, and `metadata` but still returning arbitrary public canon JSON fields (`canon_timeline`, `setting_rules`, `forbidden_changes`, and `sequel_boundaries`) verbatim. Admin-authored public canon JSON can contain storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, base64, or other operator-only canon-management evidence.
- Summary: Updated the architecture-contracts OpenSpec scenario for member world bible reads, applied the existing public JSON sanitizer to non-admin world bible public canon JSON fields, and preserved full unsanitized canon-management JSON for admin responses.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended `test_world_bible_api_preserves_continuity_contract_and_access` so admin reads retain dirty public canon JSON while member reads keep safe canon fields and remove storage refs, filesystem paths, raw prompt/output markers, secret refs, and base64 markers.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_world_bible_api_preserves_continuity_contract_and_access -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests; focused backend ruff/mypy passed for `worlds.py` and `test_api_worlds.py`; full backend ruff, mypy, and pytest passed with 567 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue auditing remaining member-readable replay/state and other public narrative/canon surfaces for arbitrary JSON/text, then resume Web/e2e route-handler and product normal-use audits. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening Conversation turn transcript text redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-076.
- Finding: F-076 found member-readable conversation turn list responses hiding runtime run IDs and error text but returning `input_text` and `output_text` verbatim. Admin seed text and provider-backed agent output can contain storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, base64, or other operator-only execution evidence.
- Summary: Updated the architecture-contracts OpenSpec conversation-turn scenario, added a conversation API member transcript text sanitizer, and applied it only to non-admin turn responses while preserving admin transcript text.
- Files changed: backend/services/api/src/noveland/services/api/conversations.py, backend/tests/test_api_conversations.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended `test_conversation_api_enforces_access_and_manual_advance` so admin seed/advance responses retain dirty transcript text while member turn list responses blank sensitive-looking input/output text and still hide run/error fields.
- Verification: `cd backend && uv run pytest tests/test_api_conversations.py::test_conversation_api_enforces_access_and_manual_advance -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_conversations.py -q` passed with 6 tests; focused backend ruff/mypy passed for `conversations.py` and `test_api_conversations.py`; full backend ruff, mypy, and pytest passed with 567 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue auditing reader/player presentation and playback DTO text/media references for comparable forbidden-evidence exposure, then resume Web/e2e route-handler and product normal-use audits. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening Media catalog provenance redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-077.
- Finding: F-077 found member-readable media asset catalog/search/detail/lineage responses redacting storage URIs and metadata but still exposing internal provider/source IDs, provider kind, actor refs, and lineage source job IDs; member source/provider filters could also infer internal provenance.
- Summary: Updated the architecture-contracts OpenSpec media catalog scenarios, blanked internal provenance fields in non-admin media response shaping, and rejected member source/provider catalog filters while preserving admin media management responses.
- Files changed: backend/services/api/src/noveland/services/api/media.py, backend/tests/test_api_media.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended `test_media_api_member_visibility_acl_and_csrf` and `test_media_api_member_metadata_redaction_across_visible_records` for member/admin provenance field boundaries and internal filter rejection.
- Verification: `cd backend && uv run pytest tests/test_api_media.py::test_media_api_member_visibility_acl_and_csrf tests/test_api_media.py::test_media_api_member_metadata_redaction_across_visible_records -q` passed with 2 tests. Focused backend ruff/mypy passed for `media.py` and `test_api_media.py`; `cd backend && uv run pytest tests/test_api_media.py -q` passed with 9 tests; full backend ruff, mypy, and pytest passed with 567 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue auditing reader/player playback DTOs and Web route handlers for comparable internal provenance or provider leakage. Do not push unless explicitly requested after this batch commit.


## Post-v1.1 RC Audit and Hardening Member presentation playback DTO entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security/product remediation for F-078.
- Finding: F-078 found `web/lib/worlds/server.ts:getConversationPlaybackData()` fetching conversation turn presentations for playback while the backend GET route was world-admin-only. The canonical presentation record can also include internal sprite/voice/transcript authoring refs and generated `presentation_json` provenance such as media job or model invocation IDs.
- Summary: Added an architecture-contracts OpenSpec scenario for member-safe presentation GET, changed only the presentation GET dependency to member context, and shaped non-admin responses so ordinary members keep playback-safe speaker/emotion/render/media asset fields while `sprite_set_id`, `sprite_variant_id`, `voice_profile_id`, `transcript_id`, and forbidden `presentation_json` evidence are removed. PUT/PATCH/render-visual/render-speech/transcribe-audio remain admin-only, and admin GET responses preserve the full record.
- Files changed: backend/services/api/src/noveland/services/api/conversation_presentations.py, backend/tests/test_api_conversation_presentations.py, backend/tests/test_api_permission_matrix.py, backend/tests/test_security_regression_suite.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended conversation presentation API coverage for member GET safe DTO shaping, dirty historical `presentation_json` redaction, admin GET preservation, and member mutation/render denial; updated permission/security regression matrices so presentation GET is no longer treated as admin-only while mutation/render routes remain denied to ordinary members.
- Verification: `cd backend && uv run pytest tests/test_api_conversation_presentations.py -q` passed with 2 tests; `cd backend && uv run pytest tests/test_api_permission_matrix.py tests/test_security_regression_suite.py tests/test_api_conversation_presentations.py -q` passed with 9 tests; focused backend ruff/mypy passed for touched backend/test files; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 567 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue auditing reader/player playback DTO media visibility edge cases, Web route handlers/proxies, and product normal-use drift. Do not push unless explicitly requested after this batch commit.


## Post-v1.1 RC Audit and Hardening Member presentation media visibility entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security/product remediation for F-079.
- Finding: F-079 found that F-078 member-safe presentation GET still returned `background_asset_id`, `composite_scene_asset_id`, and `tts_media_asset_id` directly from canonical presentation records. Rendering and admin upsert paths can store world-admin/private/hidden, suppressed, unreferenced, or otherwise non-reader-deliverable media asset IDs there even though Reader Media Delivery would not return descriptors or bytes for those assets.
- Summary: Extended the architecture-contracts OpenSpec presentation scenario, reused `ReaderMediaDeliveryService.get_media()` inside non-admin presentation response shaping, and now nulls member presentation media IDs unless the same asset is reader-deliverable for the presentation worldline. Admin presentation GET still preserves full media IDs and mutation/render routes remain admin-only.
- Files changed: backend/services/api/src/noveland/services/api/conversation_presentations.py, backend/tests/test_api_conversation_presentations.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added focused presentation API coverage proving admin-only/private/hidden media IDs are preserved for admin GET but nulled for member GET, while reader-visible same-worldline assets with reader-visible turn references remain present in the member presentation DTO.
- Verification: `cd backend && uv run pytest tests/test_api_conversation_presentations.py -q` passed with 3 tests; `cd backend && uv run pytest tests/test_api_permission_matrix.py tests/test_security_regression_suite.py tests/test_api_conversation_presentations.py -q` passed with 10 tests; focused backend ruff/mypy passed for `conversation_presentations.py` and `test_api_conversation_presentations.py`; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue Web/e2e audits for playback server loaders/components, Next route handlers, proxy response shaping, and client-side rendering sinks. Do not push unless explicitly requested after this batch commit.


## Post-v1.1 RC Audit and Hardening Dashboard world query navigation entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web/e2e security remediation for F-080.
- Finding: F-080 found `web/features/dashboard/world-management-dashboard.tsx` constructing local dashboard navigation as `/?world=${nextWorldId}` for selection and `/?world=${world.id}` after create. A world identifier containing `&`, `?`, or `#` could escape the intended `world` query parameter into extra local query data or a fragment.
- Summary: Added an architecture-contracts OpenSpec scenario for dashboard query-boundary preservation, introduced a `worldQueryPath()` helper, and routed both selected-world and newly-created-world navigation through encoded query values.
- Files changed: web/features/dashboard/world-management-dashboard.tsx, web/features/dashboard/world-management-dashboard.test.tsx, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended dashboard component coverage so world IDs containing `/`, `?`, and `#` are encoded in `router.replace()` for both selector changes and create-world success navigation.
- Verification: `cd web && npm run test -- features/dashboard/world-management-dashboard.test.tsx` passed with 6 tests; `cd web && npm run lint` passed; `cd web && npm run typecheck` passed; full `cd web && npm run test` passed with 52 files and 187 tests, with existing RuntimeAdmin React act warnings; `cd web && npm run build` passed; `cd web && npm run check:next-env` passed after restoring the expected `.next/types/routes.d.ts` import regenerated by e2e/dev; `cd web && npm run test:e2e` passed with 21 tests; OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue Web/e2e audit for remaining local query navigation, route handlers, proxy method exposure, response shaping, and client-side rendering sinks. Do not push unless explicitly requested after this batch commit.

## Post-v1.1 RC Audit and Hardening Agent run source evidence redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-081.
- Finding: F-081 found member-readable agent runtime run list responses already hiding prompt text, response text, provider profile refs, and diagnostics, but still returning `source_calendar_entry_id`, `source_schedule_rule_id`, and `created_event_id` to ordinary world members.
- Summary: Updated the architecture-contracts OpenSpec scenario for member agent runtime runs, redacted source calendar/schedule/event refs from non-admin `_agent_run_response()` output, and preserved admin source evidence for diagnosis.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended agent runtime API coverage so admin run list responses retain source calendar/schedule/event refs while member run list responses receive `null` for those fields.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_agent_runs_and_narrative_artifacts_api -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_worlds.py::test_agent_runs_and_narrative_artifacts_api tests/test_api_worlds.py::test_agent_run_apis_filter_by_worldline -q` passed with 2 tests; focused backend ruff/mypy passed for `worlds.py` and `test_api_worlds.py`; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped.
- Follow-up notes: Continue backend/Web audits for remaining member/reader/player DTO source evidence, route-handler method exposure, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Replay state source evidence redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-082.
- Finding: F-082 found member-readable replay state responses returning `clock.last_event_id` and `clock.last_event_sequence`, allowing ordinary world members to correlate reconstructed clock state to internal world event evidence even though event audit and clock transition audit routes are admin-only.
- Summary: Added an architecture-contracts OpenSpec scenario for member replay state source evidence, shaped replay state responses by caller role, and redacted clock source event refs for ordinary members while preserving admin replay diagnostics.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended replay/snapshot API coverage so member replay state hides clock source refs and admin replay state retains them.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_replay_and_snapshot_api_reads_state_and_creates_snapshot -q` passed with 1 test; `cd backend && uv run pytest tests/test_api_worlds.py::test_replay_and_snapshot_api_reads_state_and_creates_snapshot tests/test_api_worlds.py::test_world_event_audit_requires_admin_and_filters_events -q` passed with 2 tests; focused backend ruff/mypy passed for `worlds.py` and `test_api_worlds.py`; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped.
- Follow-up notes: Continue backend/Web audits for remaining member/reader/player DTO source evidence, route-handler method exposure, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Agent catalog source preset provenance redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-083.
- Finding: F-083 found member-readable agent catalog responses already hiding provider profile IDs, execution config, and unsafe character profile JSON, but still returning `source_preset_id` and `source_preset_version` to ordinary world members.
- Summary: Updated the architecture-contracts OpenSpec member-agent scenario, gated `_agent_response()` source preset provenance behind `include_admin_fields`, and preserved admin create/update/list source preset diagnostics.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended `test_create_agent_from_preset_materializes_persona_calendar_and_provider_mapping` so admin list responses retain source preset ID/version while member list responses receive `null` for both fields.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_create_agent_from_preset_materializes_persona_calendar_and_provider_mapping -q` first failed on unredacted `source_preset_id`, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests; focused backend ruff/mypy passed for `worlds.py` and `test_api_worlds.py`; full backend ruff, mypy, and pytest passed with 568 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue backend/Web audits for remaining member/reader/player DTO source evidence, route-handler method exposure, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Snapshot source evidence redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-084.
- Finding: F-084 found member-readable latest snapshot responses already hiding snapshot payload, payload URI/location, and metadata, but still returning `created_by_event_id` to ordinary world members.
- Summary: Updated the architecture-contracts OpenSpec latest snapshot scenario, made `WorldSnapshotResponse.created_by_event_id` nullable, and redacted the created-by event ref from non-admin `_snapshot_response()` output while preserving admin replay diagnostics.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended `test_replay_and_snapshot_api_reads_state_and_creates_snapshot` so admin latest snapshot responses retain `created_by_event_id` while member latest snapshot responses receive `null`.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_replay_and_snapshot_api_reads_state_and_creates_snapshot -q` first failed on unredacted `created_by_event_id`, then passed with 1 test after remediation; adjacent replay/event audit coverage passed with 2 tests; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests; focused backend ruff/mypy passed for `worlds.py` and `test_api_worlds.py`; full backend ruff, mypy, and pytest passed with 568 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue backend/Web audits for remaining member/reader/player DTO source evidence, route-handler method exposure, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Player choice event evidence redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-085.
- Finding: F-085 found member-readable player choice create/list responses already hiding prompt text and sanitizing context/consequence preview JSON, but still returning `applied_event_id` even though `record_player_choice()` always appends a `player.choice_recorded` world event.
- Summary: Updated the architecture-contracts OpenSpec player-choice scenario and gated `_player_choice_response()` applied event refs behind `include_admin_fields`, preserving admin review/event correlation while ordinary members receive safe choice status and sanitized metadata only.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended `test_world_member_can_use_own_player_interaction_records_without_admin_scope` so member choice create/list responses get `null` for `applied_event_id`, while admin list responses retain the real `player.choice_recorded` event id.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope -q` first failed on unredacted `applied_event_id`, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests; focused backend ruff/mypy passed for `worlds.py` and `test_api_worlds.py`; full backend ruff, mypy, and pytest passed with 568 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue backend/Web audits for remaining member/reader/player DTO source evidence, route-handler method exposure, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Player privacy choice event evidence redaction entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-086.
- Finding: F-086 found player privacy exports already hiding prompts, context, consequence preview, journal/notification source refs, and intervention choice/event linkage, but still exporting player choice `applied_event_id`.
- Summary: Updated the architecture-contracts OpenSpec privacy export scenario and redacted choice applied event refs from `PlayerPrivacyService._build_export_payload()` while preserving safe player-owned choice fields.
- Files changed: backend/packages/player_privacy/src/noveland/player_privacy/service.py, backend/tests/test_api_player_privacy.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended `test_player_privacy_export_is_player_scoped_and_redacted` so seeded player choices carry an internal applied event ID and member exports return `null` for it.
- Verification: `cd backend && uv run pytest tests/test_api_player_privacy.py::test_player_privacy_export_is_player_scoped_and_redacted -q` first failed on unredacted choice `applied_event_id`, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_player_privacy.py -q` passed with 3 tests; focused backend ruff/mypy passed for `player_privacy/service.py` and `test_api_player_privacy.py`; full backend ruff, mypy, and pytest passed with 568 passed and 8 skipped; OpenSpec strict validations and `git diff --check` passed.
- Follow-up notes: Continue backend/Web audits for remaining member/reader/player DTO source evidence, route-handler method exposure, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Member-owned JSON sensitive-key normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-087.
- Finding: F-087 found player session resume state and beta feedback metadata sanitizers recognized snake_case sensitive keys but missed common camelCase/compact variants such as `rawPrompt`, `rawOutput`, `storageUri`, and `promptSnapshotId` when values were otherwise safe-looking strings.
- Summary: Updated the architecture-contracts OpenSpec member-owned state JSON scenario, normalized sensitive JSON keys before comparison in player session and beta feedback services, and expanded value marker matching for compact/camelCase raw prompt/output, prompt snapshot, storage URI, and path variants.
- Files changed: backend/packages/player_sessions/src/noveland/player_sessions/service.py, backend/packages/beta_feedback/src/noveland/beta_feedback/service.py, backend/tests/test_api_player_sessions.py, backend/tests/test_api_beta_feedback.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended player session resume round-trip and beta feedback triage coverage to submit camelCase/compact sensitive keys and assert only safe state/metadata remains.
- Verification: `cd backend && uv run pytest tests/test_api_player_sessions.py::test_player_session_resume_round_trip_is_player_safe tests/test_api_beta_feedback.py::test_tester_creates_own_feedback_and_admin_triages_without_leaks -q` first failed on unredacted camelCase sensitive keys, then passed with 2 tests after remediation; `cd backend && uv run pytest tests/test_api_player_sessions.py tests/test_api_beta_feedback.py -q` passed with 7 tests; focused backend ruff/mypy passed for `player_sessions/service.py`, `beta_feedback/service.py`, and their API tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue backend/Web audits for remaining member-owned metadata sanitizers, route-handler method exposure, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Remaining JSON sensitive-key normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-088.
- Finding: F-088 found private beta invite metadata, player privacy export/request JSON, and moderation report/review metadata sanitizers still recognized only snake_case or exact lower-case sensitive keys, allowing camelCase/compact `rawPrompt`, `rawOutput`, `storageUri`, and `promptSnapshotId` keys to persist and return.
- Summary: Updated the architecture-contracts OpenSpec review/onboarding metadata scenario, normalized sensitive JSON keys before comparison in private beta, player privacy, and moderation services, and expanded value marker matching for compact/camelCase raw prompt/output, prompt snapshot, storage URI, and path variants.
- Files changed: backend/packages/private_beta/src/noveland/private_beta/service.py, backend/packages/player_privacy/src/noveland/player_privacy/service.py, backend/packages/moderation/src/noveland/moderation/service.py, backend/tests/test_api_private_beta.py, backend/tests/test_api_player_privacy.py, backend/tests/test_api_moderation.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended private beta invite, player privacy export, and moderation report coverage to submit or seed camelCase/compact sensitive keys and assert only safe metadata remains.
- Verification: `cd backend && uv run pytest tests/test_api_private_beta.py::test_admin_invite_lifecycle_redeem_and_profile_bootstrap_are_safe tests/test_api_player_privacy.py::test_player_privacy_export_is_player_scoped_and_redacted tests/test_api_moderation.py::test_reader_can_create_report_and_admin_can_review_without_leaks -q` first failed on unredacted camelCase sensitive keys, then passed with 3 tests after remediation; `cd backend && uv run pytest tests/test_api_private_beta.py tests/test_api_player_privacy.py tests/test_api_moderation.py -q` passed with 12 tests; focused backend ruff/mypy passed for `private_beta/service.py`, `player_privacy/service.py`, `moderation/service.py`, and their API tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue backend/Web audits for remaining package-local metadata sanitizers, route-handler method exposure, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Event payload key normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-089.
- Finding: F-089 found the global world event payload sanitizer still checked forbidden keys using exact snake_case names, allowing camelCase/compact keys such as `rawPrompt`, `rawOutput`, `storageUri`, and `promptSnapshotId` to persist in `world_events.payload`.
- Summary: Updated the architecture-contracts OpenSpec event-store normalized-key scenario, normalized forbidden world event payload keys before comparison, expanded forbidden value markers for compact/camelCase URI/path/prompt terms, and kept safe domain event context fields such as `secret_id` and `secret_key` intact.
- Files changed: backend/packages/events/src/noveland/events/sanitization.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended secret reveal event-store payload coverage with camelCase/compact forbidden keys and assertions that persisted world event payloads omit them.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_event_store_sanitizes_secret_reveal_event_payload -q` first failed on unredacted `rawPrompt` in `world_events.payload`, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_worlds.py::test_offscreen_resolution_sanitizes_persisted_world_event_payload tests/test_api_worlds.py::test_gm_proposal_resolution_sanitizes_persisted_world_event_payload tests/test_api_worlds.py::test_event_store_sanitizes_secret_reveal_event_payload tests/test_event_contracts.py -q` passed with 11 tests; focused backend ruff/mypy passed for `events/sanitization.py`, `test_api_worlds.py`, and `test_event_contracts.py`; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue backend/Web audits for remaining package-local metadata sanitizers, member DTO redaction helpers, route-handler method exposure, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Member media and presentation JSON key normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-090.
- Finding: F-090 found member-readable media metadata DTOs and conversation presentation JSON already removed snake_case sensitive keys, but still returned camelCase/compact keys such as `rawPrompt`, `rawOutput`, `storageUri`, and `promptSnapshotId` when values were otherwise safe-looking strings.
- Summary: Updated the architecture-contracts OpenSpec member media/presentation JSON scenario, normalized member media metadata and presentation JSON keys before comparison, and expanded forbidden value markers for compact/camelCase URI/path/prompt/provider/job/invocation terms.
- Files changed: backend/services/api/src/noveland/services/api/media.py, backend/services/api/src/noveland/services/api/conversation_presentations.py, backend/tests/test_api_media.py, backend/tests/test_api_conversation_presentations.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended media metadata redaction and member presentation GET coverage with camelCase/compact forbidden keys and assertions that ordinary member responses omit them while retaining safe fields.
- Verification: `cd backend && uv run pytest tests/test_api_media.py::test_media_api_member_metadata_redaction_across_visible_records tests/test_api_conversation_presentations.py::test_conversation_presentation_api_renders_visual_speech_and_transcript -q` first failed on unredacted camelCase sensitive keys, then passed with 2 tests after remediation; `cd backend && uv run pytest tests/test_api_media.py tests/test_api_conversation_presentations.py -q` passed with 12 tests; focused backend ruff/mypy passed for `media.py`, `conversation_presentations.py`, and their API tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue backend/Web audits for remaining package-local metadata sanitizers, member DTO redaction helpers, route-handler method exposure, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Provider secret-key normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-091.
- Finding: F-091 found provider secret-key detection normalized keys with exact lower-case matching, so `clientSecret`, `bearerToken`, `privateKey`, and `secretKey` could bypass provider config/default-param rejection and persistence redaction even though equivalent snake_case keys were forbidden.
- Summary: Updated the architecture-contracts OpenSpec provider secret-bearing JSON scenario, centralized normalized provider sensitive-key detection in `providers.secrets`, reused it for package provider validation/export, multimodal diagnostic secret checks, and narrative quality dashboard sanitization, and kept budget metadata covered through the shared reject path.
- Files changed: backend/packages/providers/src/noveland/providers/secrets.py, backend/packages/package_contracts/src/noveland/package_contracts/service.py, backend/packages/multimodal_eval/src/noveland/multimodal_eval/service.py, backend/packages/narrative_quality/src/noveland/narrative_quality/service.py, backend/tests/test_provider_registry_service.py, backend/tests/test_api_package_contracts.py, backend/tests/test_provider_execution_service.py, backend/tests/test_multimodal_eval_service.py, backend/tests/test_narrative_quality_service.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added/updated provider registry, package contract validate/export, provider budget metadata, multimodal eval, and narrative quality dashboard coverage for camelCase/compact provider secret keys.
- Verification: `cd backend && uv run pytest tests/test_provider_registry_service.py::test_registry_rejects_sensitive_provider_config_recursively tests/test_provider_registry_service.py::test_sanitizer_redacts_nested_sensitive_keys tests/test_api_package_contracts.py::test_package_contract_reports_registry_and_secret_issues tests/test_api_package_contracts.py::test_provider_config_export_is_sanitized_and_does_not_resolve_secret tests/test_provider_execution_service.py::test_budget_policy_rejects_camel_case_secret_metadata tests/test_multimodal_eval_service.py::test_multimodal_eval_detects_integrity_and_leak_failures -q` first failed with 6 failures on unblocked/unredacted camelCase secret keys, then passed with 6 tests after remediation; `cd backend && uv run pytest tests/test_narrative_quality_service.py::test_narrative_quality_dashboard_detects_blockers_and_sanitizes_evidence -q` passed with 1 test after switching provider health metadata coverage to `clientSecret`; `cd backend && uv run pytest tests/test_provider_registry_service.py tests/test_api_package_contracts.py tests/test_provider_execution_service.py tests/test_multimodal_eval_service.py tests/test_narrative_quality_service.py -q` passed with 79 tests; focused backend ruff/mypy passed for provider secrets, package contracts, multimodal eval, narrative quality, and their updated tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 569 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue backend/Web audits for remaining package-local storage/prompt key normalization, route-handler method exposure, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Budget and diagnostics leaky-key normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-092.
- Finding: F-092 found provider budget policy JSON, multimodal prompt snapshot diagnostics, and narrative quality dashboard evidence checks still matched storage/prompt/path keys with exact lower-case names, so `storageUri`, `rawPrompt`, and `promptSnapshotId` could be accepted, under-reported, or returned where equivalent snake_case keys were rejected or flagged.
- Summary: Updated the architecture-contracts OpenSpec budget/diagnostics JSON scenario, normalized leaky key comparisons in provider budget validation, multimodal diagnostics, and narrative quality dashboard sanitization, and expanded marker sets for storage URI, prompt snapshot, raw prompt/output, filesystem/object paths, bytes, and base64 forms.
- Files changed: backend/packages/providers/src/noveland/providers/budget.py, backend/packages/multimodal_eval/src/noveland/multimodal_eval/service.py, backend/packages/narrative_quality/src/noveland/narrative_quality/service.py, backend/tests/test_provider_execution_service.py, backend/tests/test_multimodal_eval_service.py, backend/tests/test_narrative_quality_service.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added provider budget rejection coverage for camelCase storage/prompt metadata, multimodal prompt snapshot leak detection coverage for camelCase storage/prompt/prompt-snapshot keys, and narrative quality dashboard coverage for camelCase provider health evidence sanitization.
- Verification: `cd backend && uv run pytest tests/test_provider_execution_service.py::test_budget_policy_rejects_camel_case_leaky_metadata tests/test_multimodal_eval_service.py::test_multimodal_eval_detects_camel_case_prompt_snapshot_leaks tests/test_narrative_quality_service.py::test_narrative_quality_dashboard_detects_camel_case_leaky_metadata -q` first failed with 3 failures on unblocked/unflagged camelCase leaky keys, then passed with 3 tests after remediation; `cd backend && uv run pytest tests/test_provider_execution_service.py tests/test_multimodal_eval_service.py tests/test_narrative_quality_service.py -q` passed with 72 tests; focused backend ruff/mypy passed for provider budget, multimodal eval, narrative quality, and their updated tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 572 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue backend/Web audits for remaining package-local import/export validators, Web route handlers, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Package and authoring leaky-key normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend security remediation for F-093.
- Finding: F-093 found world package manifest validation, authoring source metadata/config contracts, and asset generation policy/proposal contracts rejected snake_case forbidden keys such as `storage_uri` and `raw_prompt`, but accepted equivalent camelCase/compact keys including `storageUri`, `rawPrompt`, `promptSnapshotId`, and `filesystemPath`.
- Summary: Updated the architecture-contracts OpenSpec package/authoring validator scenario, normalized forbidden key comparisons in world packaging, authoring, and asset generation contract validators, and expanded marker sets for storage URI, prompt snapshot, raw prompt/output, filesystem/object paths, bytes, and base64 forms.
- Files changed: backend/packages/world_packaging/src/noveland/world_packaging/contracts.py, backend/packages/authoring/src/noveland/authoring/contracts.py, backend/packages/asset_generation/src/noveland/asset_generation/contracts.py, backend/tests/test_api_world_packaging.py, backend/tests/test_authoring_service.py, backend/tests/test_asset_generation_service.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Updated world package import, authoring JSON, and asset generation policy validation tests to cover camelCase/compact forbidden key variants while retaining safe metadata behavior.
- Verification: `cd backend && uv run pytest tests/test_api_world_packaging.py::test_world_package_import_rejects_forbidden_manifest_values tests/test_authoring_service.py::test_authoring_json_rejects_leaky_values tests/test_asset_generation_service.py::test_policy_rejects_leaky_json_and_preview_validates_worldline -q` first failed with 3 failures on accepted camelCase leaky keys, then passed with 3 tests after remediation; `cd backend && uv run pytest tests/test_api_world_packaging.py tests/test_authoring_service.py tests/test_asset_generation_service.py tests/test_api_asset_generation.py tests/test_authoring_regression_fixture.py -q` passed with 39 tests; focused backend ruff/mypy passed for world packaging, authoring, asset generation contracts, and their updated tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 572 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue Web/e2e audits for route handlers, client-side rendering sinks, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web invocation ledger evidence key normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web admin security remediation for F-094.
- Finding: F-094 found the Web invocation ledger admin evidence renderer redacted snake_case storage/path/secret/base64 keys, but rendered camelCase or compact evidence keys such as `storageUri`, `rawPrompt`, and `promptSnapshotId` when their values were otherwise safe-looking strings.
- Summary: Updated the architecture-contracts OpenSpec invocation-ledger evidence scenario, normalized evidence keys before redaction in `InvocationLedgerAdmin`, expanded forbidden markers for storage/path/bytes/base64/raw prompt/output/prompt snapshot/auth variants, and replaced sensitive rendered keys with `redacted_N` placeholders so key names do not leak.
- Files changed: web/features/admin/invocation-ledger-admin.tsx, web/features/admin/invocation-ledger-admin.test.tsx, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended invocation ledger admin rendering coverage with camelCase storage/prompt/snapshot evidence keys, assertions that sensitive key names and values are absent, and assertions that safe evidence fields remain visible.
- Verification: `cd web && npm run test -- features/admin/invocation-ledger-admin.test.tsx` first failed on rendered `storageUri` and `rawPrompt`, then passed with 3 tests after remediation; `cd web && npm run test -- features/admin/invocation-ledger-admin.test.tsx lib/worlds/invocations.test.ts` passed with 6 tests; Web lint, typecheck, `check:next-env`, full unit test suite, build, and Playwright e2e passed before commit. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue Web/e2e audits for route handlers, client-side rendering sinks, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web provider admin JSON normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web admin security remediation for F-095.
- Finding: F-095 found the Web provider integration admin rendered provider config JSON, default params JSON, capability JSON, and health metadata summaries directly, so dirty legacy/API responses with `clientSecret`, `bearerToken`, `rawPrompt`, `storageUri`, or `promptSnapshotId` could expose sensitive key names and values in editable admin panels.
- Summary: Updated the architecture-contracts OpenSpec provider-admin scenario, added normalized provider JSON display sanitization in `ProviderIntegrationAdmin`, sanitized create/update payloads parsed from those panels, filtered health metadata summaries, and preserved legitimate provider config fields such as `model_discovery_path`, `chat_completions_path`, `endpoint`, and `temperature`.
- Files changed: web/features/admin/provider-integration-admin.tsx, web/features/admin/provider-integration-admin.test.tsx, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended provider admin rendering coverage with dirty camelCase/compact provider secret, prompt, storage, path, snapshot, and capability metadata keys while asserting safe provider configuration keys remain visible.
- Verification: `cd web && npm run test -- features/admin/provider-integration-admin.test.tsx` first failed with 2 failures on rendered dirty provider JSON, then passed with 5 tests after remediation; `cd web && npm run test -- features/admin/provider-integration-admin.test.tsx lib/worlds/provider-integrations.test.ts` passed with 10 tests; Web lint, typecheck, `check:next-env`, full unit test suite, build, and Playwright e2e passed before commit. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue Web/e2e audits for remaining route handlers, memory/runtime admin JSON panels, client-side rendering sinks, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web memory admin JSON normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web admin security remediation for F-096.
- Finding: F-096 found the Web memory backend admin rendered profile config JSON, `secret_refs`, health details, and write/retrieval log summaries directly, so dirty legacy/API responses with `clientSecret`, `bearerToken`, `rawPrompt`, `storageUri`, or `promptSnapshotId` could expose sensitive key names and values in editable admin panels and diagnostic summaries.
- Summary: Updated the architecture-contracts OpenSpec memory-admin scenario, added normalized memory JSON display sanitization in `MemoryBackendAdmin`, filtered unsafe `secret_refs` values while preserving safe `env:` references, sanitized create/update payloads parsed from those panels, and sanitized the health/log/job JSON diagnostic block.
- Files changed: web/features/admin/memory-backend-admin.tsx, web/features/admin/memory-backend-admin.test.tsx, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended memory admin rendering coverage with dirty camelCase/compact memory secret, prompt, storage, path, and snapshot keys while asserting safe memory config and safe `env:MEMORY_OPENAI_API_KEY` references remain visible.
- Verification: `cd web && npm run test -- features/admin/memory-backend-admin.test.tsx` first failed on rendered dirty memory JSON, then passed with 1 test after remediation; `cd web && npm run test -- features/admin/memory-backend-admin.test.tsx lib/worlds/client.test.ts` passed with 36 tests; Web lint, typecheck, `check:next-env`, full unit test suite, build, and Playwright e2e passed before commit. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue Web/e2e audits for runtime admin diagnostics, remaining route handlers, client-side rendering sinks, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web runtime admin diagnostics text normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web admin security remediation for F-097.
- Finding: F-097 found the Web runtime admin rendered runtime health reasons, external tool policy messages/lists, scale readiness summaries, and runtime diagnostic component/message strings directly, so dirty legacy API or SSE payloads with `media://`, filesystem paths, local model paths, bearer tokens, `sk-` keys, raw prompt/output markers, prompt snapshot refs, bytes, or base64 markers could be displayed.
- Summary: Updated the architecture-contracts OpenSpec runtime-admin scenario, added defensive runtime text sanitization in `RuntimeAdmin`, applied it to runtime notices, external tool policy compact lists, scale readiness text, and diagnostic rows, and preserved safe operational strings.
- Files changed: web/features/admin/runtime-admin.tsx, web/features/admin/runtime-admin.test.tsx, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added runtime admin rendering coverage for dirty loader data and SSE diagnostic payloads while asserting safe deny reasons, audit fields, readiness areas, and recommendations remain visible.
- Verification: `cd web && npm run test -- features/admin/runtime-admin.test.tsx` first failed against the unpatched component with dirty runtime strings visible in the failure DOM, then passed with 3 tests after remediation; `cd web && npm run test -- features/admin/runtime-admin.test.tsx lib/worlds/client.test.ts` passed with 38 tests; Web lint, typecheck, `check:next-env`, full unit test suite, build, and Playwright e2e passed before commit, with `next-env.d.ts` restored after e2e regenerated the dev route reference. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue Web/e2e audits for remaining route handlers, client-side rendering sinks, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web dashboard JSON normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web admin security remediation for F-098.
- Finding: F-098 found the Web world management dashboard rendered agent config, schedule rule config, provider profile capabilities, and persona behavior policy through direct `JSON.stringify(...)`, and parsed dashboard JSON form submissions with raw `jsonObject(...)`, so dirty legacy API data or user-edited values with `clientSecret`, `bearerToken`, `rawPrompt`, `storageUri`, `promptSnapshotId`, filesystem paths, bytes, or base64 markers could display and echo back through dashboard helpers.
- Summary: Updated the architecture-contracts OpenSpec dashboard JSON scenario, added normalized dashboard JSON display and submit sanitization in `WorldManagementDashboard`, applied it to agent config, schedule rule config, provider capabilities, persona behavior policy, observation metadata, and narrative artifact metadata, and preserved safe dashboard config fields.
- Files changed: web/features/dashboard/world-management-dashboard.tsx, web/features/dashboard/world-management-dashboard.test.tsx, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added dashboard rendering coverage for dirty JSON panels while asserting safe agent config, schedule hours, provider capability flags, and persona behavior fields remain visible.
- Verification: `cd web && npm run test -- features/dashboard/world-management-dashboard.test.tsx` first failed against the unpatched component with dirty dashboard JSON visible in editable textareas, then passed with 7 tests after remediation; `cd web && npm run test -- features/dashboard/world-management-dashboard.test.tsx lib/worlds/client.test.ts` passed with 42 tests; Web lint, typecheck, `check:next-env`, full unit test suite, build, and Playwright e2e passed before commit, with full unit tests passing on rerun after one unrelated `media-admin` timing miss passed in isolation. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue Web/e2e audits for remaining route handlers, client-side rendering sinks, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web agent builder evidence normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web agent security remediation for F-099.
- Finding: F-099 found the Web agent builder rendered agent character profile/config JSON, relationship metadata, persona policy/config JSON, selected run diagnostics, and run prompt/response summary text directly, and parsed agent-builder JSON form submissions with raw `jsonObject(...)`. Dirty legacy API data or edited form values containing `clientSecret`, `bearerToken`, `rawPrompt`, `storageUri`, `promptSnapshotId`, filesystem paths, bytes, or base64 markers could therefore display in agent builder panels and be echoed back through update helpers.
- Summary: Updated the architecture-contracts OpenSpec agent-builder scenario, added normalized agent-builder JSON display and submit sanitization in `AgentBuilder`, applied it to agent profile/config, relationship metadata, persona policy/config, selected run diagnostics, and run summary text, and preserved safe characterization, relationship, persona, and operational fields.
- Files changed: web/features/agents/agent-builder.tsx, web/features/agents/agent-builder.test.tsx, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added agent builder rendering coverage for dirty JSON panels and dirty run text while asserting safe agent profile, config, relationship, persona, and diagnostic fields remain visible.
- Verification: `cd web && npm run test -- features/agents/agent-builder.test.tsx` first failed against the unpatched component with dirty agent builder JSON and run text visible, then passed with 2 tests after remediation; `cd web && npm run test -- features/agents/agent-builder.test.tsx lib/worlds/client.test.ts` passed with 37 tests; Web lint, typecheck, `check:next-env`, full unit test suite, build, and Playwright e2e passed before commit, with `next-env.d.ts` restored after build/e2e checks.
- Follow-up notes: Continue Web/e2e audits for remaining route handlers, client-side rendering sinks, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web preset admin JSON normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web platform admin security remediation for F-100.
- Finding: F-100 found the Web preset admin rendered preset behavior policy, calendar blueprint entries/metadata, and advanced config through direct `JSON.stringify(...)`, and parsed preset create/update JSON submissions with raw `jsonObject(...)` or `JSON.parse(...)`. Dirty legacy API data or edited form values containing `clientSecret`, `bearerToken`, `rawPrompt`, `storageUri`, `promptSnapshotId`, filesystem paths, bytes, or base64 markers could display in preset panels and be echoed into reusable preset templates.
- Summary: Updated the architecture-contracts OpenSpec preset-admin scenario, added normalized preset JSON display and submit sanitization in `PresetAdmin`, applied it to behavior policy, calendar blueprint arrays, nested calendar metadata, and advanced config, and preserved safe preset behavior, schedule, metadata, and operational fields.
- Files changed: web/features/admin/preset-admin.tsx, web/features/admin/preset-admin.test.tsx, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added preset admin coverage for dirty existing preset JSON panels plus dirty create/update submit payloads while asserting safe behavior, calendar, metadata, and config fields remain visible or submitted.
- Verification: `cd web && npm run test -- features/admin/preset-admin.test.tsx` first failed against the unpatched component with dirty preset JSON visible in editable textareas, then passed with 4 tests after remediation; `cd web && npm run test -- features/admin/preset-admin.test.tsx lib/worlds/client.test.ts` passed with 39 tests; Web lint, typecheck, `check:next-env`, full unit test suite, build, and Playwright e2e passed before commit, with `next-env.d.ts` restored after build/e2e checks.
- Follow-up notes: Continue Web/e2e audits for remaining world overview/conversation/narrative/plugin JSON rendering sinks, route handlers, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web world overview JSON normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web world admin security remediation for F-101.
- Finding: F-101 found the Web world overview rendered world memory/rules plugin config, world bible JSON, release profile policies/checklists/metadata, composition rules config, and event audit payload summaries through direct `JSON.stringify(...)`, and parsed matching submissions with raw `jsonObject(...)`, `jsonObjectArray(...)`, or `JSON.parse(...)`. Dirty legacy API data or edited values containing `clientSecret`, `bearerToken`, `rawPrompt`, `storageUri`, `promptSnapshotId`, filesystem paths, bytes, or base64 markers could display on the central overview page and echo into update/validate/import helpers.
- Summary: Updated the architecture-contracts OpenSpec world-overview scenario, added normalized world-overview JSON display and submit sanitization in `WorldOverview`, applied it to world plugin config, world bible JSON arrays/objects, release profile policies/checklists/metadata, composition rules config, and event payload summaries, and preserved safe world config, continuity, release, composition, and audit fields.
- Files changed: web/features/worlds/world-overview.tsx, web/features/worlds/world-overview.test.tsx, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added world overview coverage for dirty JSON panels, dirty event payload summaries, and dirty update/world-bible/release/validate/import submit payloads while asserting safe fields remain visible or submitted.
- Verification: `cd web && npm run test -- features/worlds/world-overview.test.tsx` first failed against the unpatched component with dirty world overview JSON/event payload visible, then passed with 5 tests after remediation; `cd web && npm run test -- features/worlds/world-overview.test.tsx lib/worlds/client.test.ts` passed with 40 tests; Web lint, typecheck, `check:next-env`, full unit test suite, build, and Playwright e2e passed before commit, with `next-env.d.ts` restored after build/e2e checks.
- Follow-up notes: Continue Web/e2e audits for remaining conversation detail, narrative reader, plugin config, route handlers, local query construction, product normal-use flows, and spec/history drift. Do not push unless explicitly requested.

## Post-v1.1 RC Audit and Hardening Web narrative JSON normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web narrative security remediation for F-102.
- Finding: F-102 found the Web conversation detail rendered `writer_config.writer_plugin_config` directly and submitted it with raw `jsonObject(...)`, while the reader artifact detail rendered `artifact.metadata` directly. Dirty legacy/API data or edited values containing `clientSecret`, `bearerToken`, `rawPrompt`, `rawOutput`, `storageUri`, `promptSnapshotId`, filesystem/object paths, bytes, or base64 markers could display in admin writer config panels, echo through writer config updates, or leak on reader-visible published artifact pages.
- Summary: Updated the architecture-contracts OpenSpec narrative scenario, added normalized writer-config JSON display and submit sanitization in `ConversationDetail`, added normalized reader artifact metadata rendering in `NarrativeReaderDetail`, omitted sensitive key variants, redacted sensitive-looking string values, and preserved safe writer options and reader-facing artifact metadata.
- Files changed: web/features/conversations/conversation-detail.tsx, web/features/conversations/conversation-detail.test.tsx, web/features/worlds/narrative-reader.tsx, web/features/worlds/narrative-reader.test.tsx, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added conversation detail coverage for dirty writer plugin config display and submit payloads, plus reader detail coverage for dirty artifact metadata, asserting sensitive key/value variants are absent while safe labels and metadata remain visible or submitted.
- Verification: `cd web && npm run test -- features/conversations/conversation-detail.test.tsx features/worlds/narrative-reader.test.tsx` first failed with 2 failures on rendered dirty writer config and reader metadata, then passed with 10 tests after remediation; `cd web && npm run test -- features/conversations/conversation-detail.test.tsx features/worlds/narrative-reader.test.tsx lib/worlds/client.test.ts` passed with 45 tests; Web lint, typecheck, `check:next-env`, full unit test suite, and build passed. The first Playwright e2e run hit an unrelated agent-create navigation timeout after 11 tests passed; the immediate rerun passed with 21 tests and `next-env.d.ts` remained clean after restoration. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue Web/e2e audits for remaining plugin config surfaces, route handlers, proxy method exposure, response shaping, role boundary, client-side rendering sinks, local query construction, product normal-use flows, and spec/history drift. Push after successful commits unless the user changes that instruction.

## Post-v1.1 RC Audit and Hardening Web provider profile admin JSON normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web provider profile admin security remediation for F-103.
- Finding: F-103 found the legacy Web provider profile admin parsed `plugin_config` and `capabilities` with raw `jsonObject(...)`, rendered capabilities with direct `JSON.stringify(...)`, and rendered provider plugin config through schema-derived values plus a raw JSON fallback. Dirty legacy/API data or edited values containing `clientSecret`, `bearerToken`, `rawPrompt`, `rawOutput`, `storageUri`, `promptSnapshotId`, local model paths, filesystem paths, bytes, or base64 markers could display in provider profile admin panels and echo through create/update helpers.
- Summary: Updated the architecture-contracts OpenSpec provider admin scenario, added normalized provider profile JSON display and submit sanitization in `ProviderAdmin`, passed sanitized plugin config into schema-derived `PluginConfigFields`, sanitized capabilities rendering, and preserved safe provider options such as endpoint, `json_mode`, `max_tokens`, and ordinary capability flags.
- Files changed: web/features/admin/provider-admin.tsx, web/features/admin/provider-admin.test.tsx, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added provider admin coverage for dirty plugin config schema fields, raw plugin config JSON, capabilities JSON, and update submit payloads while asserting sensitive key/value variants are absent and safe provider options remain visible/submitted.
- Verification: `cd web && npm run test -- features/admin/provider-admin.test.tsx` first failed with 1 failure on rendered dirty provider plugin config, then passed with 2 tests after remediation; `cd web && npm run test -- features/admin/provider-admin.test.tsx lib/worlds/client.test.ts` passed with 37 tests; Web lint, typecheck, `check:next-env`, full unit test suite, build, and Playwright e2e passed before commit, with `next-env.d.ts` restored and checked after build/e2e. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue Web/e2e audits for remaining route handlers, proxy method exposure, response shaping, role boundary, client-side rendering sinks, local query construction, product normal-use flows, and spec/history drift. Push after successful commits unless the user changes that instruction.

## Post-v1.1 RC Audit and Hardening Web visual resolver CSRF entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web visual admin security remediation for F-104.
- Finding: F-104 found `resolveSprite` and `resolveBackground` in `web/lib/worlds/visual.ts` issued admin POST requests without `csrf: true`, while adjacent visual writes/deletes and compose-scene required the double-submit CSRF header. Existing visual client coverage explicitly expected resolver preview requests to omit `X-CSRF-Token`.
- Summary: Updated the architecture-contracts OpenSpec visual admin client scenario, required CSRF for visual resolver preview POST helpers, and updated visual client tests so resolver preview and compose-scene POST requests all carry the CSRF header while retaining encoded visual path/query behavior.
- Files changed: web/lib/worlds/visual.ts, web/lib/worlds/visual.test.ts, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Updated visual admin client coverage to assert `resolve-sprite`, `resolve-background`, and `compose-scene` POST requests all forward `X-CSRF-Token`, replacing the prior no-CSRF resolver expectation.
- Verification: `cd web && npm run test -- lib/worlds/visual.test.ts` first failed with 1 failure on a missing resolver CSRF header, then passed with 4 tests after remediation; `cd web && npm run test -- lib/worlds/visual.test.ts lib/admin/api-client.test.ts lib/worlds/proxy.test.ts` passed with 13 tests; Web lint, typecheck, `check:next-env`, full unit test suite, build, and Playwright e2e passed before commit, with `next-env.d.ts` restored and checked after build/e2e. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue Web/e2e audits for remaining route handlers, proxy method exposure, response shaping, role boundary, client-side rendering sinks, local query construction, product normal-use flows, and spec/history drift. Push after successful commits unless the user changes that instruction.

## Post-v1.1 RC Audit and Hardening Web agent memory search CSRF entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web world client security remediation for F-105.
- Finding: F-105 found `searchAgentMemory` in `web/lib/worlds/client.ts` issued a world-scoped POST request without `csrf: true`, while adjacent agent memory profile refresh/forget, persona, observation, manual run, narrative, and agent mutation helpers required the double-submit CSRF header. Existing client coverage checked URL/body mapping but did not assert `X-CSRF-Token`.
- Summary: Updated the architecture-contracts OpenSpec agent memory client scenario, required CSRF for the agent memory search POST helper, and updated world client tests to assert the `memory/search` request carries the CSRF header while preserving encoded world/agent path behavior and JSON body mapping.
- Files changed: web/lib/worlds/client.ts, web/lib/worlds/client.test.ts, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Updated memory request client coverage to set a CSRF cookie and assert `memory/search` forwards `X-CSRF-Token` along with its JSON body.
- Verification: `cd web && npm run test -- lib/worlds/client.test.ts` first failed with 1 failure on a missing memory-search CSRF header, then passed with 35 tests after remediation; `cd web && npm run test -- lib/worlds/client.test.ts lib/worlds/proxy.test.ts lib/admin/api-client.test.ts` passed with 44 tests; Web lint, typecheck, `check:next-env`, full unit test suite, build, and Playwright e2e passed before commit, with `next-env.d.ts` restored and checked after build/e2e. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue Web/e2e audits for remaining route handlers, proxy method exposure, response shaping, role boundary, client-side rendering sinks, local query construction, product normal-use flows, and spec/history drift. Push after successful commits unless the user changes that instruction.

## Post-v1.1 RC Audit and Hardening Web backend error detail normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web client security remediation for F-106.
- Finding: F-106 found admin, world, media upload, private-beta, and beta-feedback Web API clients parsing backend JSON `detail` / `detail.message` and throwing raw client errors. Workspace notices can display those messages, so dirty backend failures containing provider secrets, auth tokens, storage refs, filesystem/object paths, local model paths, raw prompt/output markers, prompt snapshot refs, bytes, or base64-like evidence could cross into admin, member, player, or beta-user UI notices.
- Summary: Updated the architecture-contracts OpenSpec backend-error scenario, added shared `normalizeBackendErrorDetail`, and routed admin/world/media/private-beta/beta-feedback error parsing through route-specific generic fallbacks when backend detail text looks sensitive while preserving safe business errors and safe publication gate summaries.
- Files changed: web/lib/safe-error-detail.ts, web/lib/admin/api-client.ts, web/lib/admin/api-client.test.ts, web/lib/worlds/client.ts, web/lib/worlds/client.test.ts, web/lib/worlds/media.ts, web/lib/worlds/media.test.ts, web/lib/private-beta/client.ts, web/lib/private-beta/client.test.ts, web/lib/beta-feedback/client.ts, web/lib/beta-feedback/client.test.ts, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added client regression coverage for dirty backend detail strings/messages across admin, world, media upload, private-beta, and beta-feedback helpers, while preserving safe admin `Forbidden` and structured publication gate summary behavior.
- Verification: `cd web && npm run test -- lib/admin/api-client.test.ts lib/worlds/client.test.ts lib/worlds/media.test.ts lib/private-beta/client.test.ts lib/beta-feedback/client.test.ts` first failed with 5 failures against the unpatched clients because raw backend details were preserved, then passed with 53 tests after remediation; `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed; full `cd web && npm run test` passed with 52 files and 200 tests; `cd web && npm run build` passed with `next-env.d.ts` restored and checked; `cd web && npm run test:e2e` passed with 21 tests and `cd web && npm run check:next-env` passed afterward. OpenSpec strict validations and `git diff --check` passed after docs update.
- Follow-up notes: Continue Web/e2e audits for remaining route handlers, proxy method exposure, response shaping, role boundary, client-side rendering sinks, product normal-use flows, and spec/history drift. Push after successful commits unless the user changes that instruction.

## Post-v1.1 RC Audit and Hardening Web auth error detail normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web auth client security remediation for F-107.
- Finding: F-107 found `web/lib/auth/client.ts` parsing backend JSON `detail` and throwing `AuthClientError` with the raw string for CSRF, login, and current-subject requests. Login form maps common 401/422 responses to fixed text, but CSRF failures reached through other Web clients can be caught by generic `Error.message` UI fallbacks and display dirty backend detail.
- Summary: Extended the architecture-contracts backend-error scenario to auth clients, applied shared `normalizeBackendErrorDetail` inside auth response parsing with each route-specific fallback, and preserved safe credential/business errors while redacting sensitive-looking backend auth/CSRF details.
- Files changed: web/lib/auth/client.ts, web/lib/auth/client.test.ts, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added auth client regression coverage for dirty CSRF backend detail with `clientSecret`, `sk-*`, `storageUri`, and `media://` markers, plus reran the F-106 client normalization suite.
- Verification: `cd web && npm run test -- lib/auth/client.test.ts` first failed with 1 failure against the unpatched auth client because raw CSRF backend detail was preserved, then passed with 7 tests after remediation; `cd web && npm run test -- lib/auth/client.test.ts lib/admin/api-client.test.ts lib/worlds/client.test.ts lib/worlds/media.test.ts lib/private-beta/client.test.ts lib/beta-feedback/client.test.ts` passed with 60 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed; full `cd web && npm run test` passed with 52 files and 201 tests; `cd web && npm run build` passed with `next-env.d.ts` restored and checked; `cd web && npm run test:e2e` passed with 21 tests and `cd web && npm run check:next-env` passed afterward. OpenSpec strict validations and `git diff --check` passed after docs update.
- Follow-up notes: Continue Web/e2e audits for remaining route handlers, server-side loader error handling, proxy response shaping, role boundary, client-side rendering sinks, product normal-use flows, and spec/history drift. Push after successful commits unless the user changes that instruction.

## Post-v1.1 RC Audit and Hardening Web server loader error detail normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web server-loader security remediation for F-108.
- Finding: F-108 found `web/lib/worlds/server.ts` and `web/lib/beta-feedback/server.ts` parsing backend JSON `detail` into `WorldServerError` / `BetaFeedbackServerError` messages. Most loader failures become fixed page `loadError` strings, but `getWorldsIndexData()` and 401 rethrows can preserve dirty backend detail into Next server error/log boundaries.
- Summary: Added an architecture-contracts scenario for server loaders, routed worlds and beta-feedback server-loader `errorDetail` parsing through shared `normalizeBackendErrorDetail`, and preserved existing fixed page `loadError` behavior for caught loader failures.
- Files changed: web/lib/worlds/server.ts, web/lib/worlds/server.test.ts, web/lib/beta-feedback/server.ts, web/lib/beta-feedback/server.test.ts, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added server-loader regression coverage for dirty worlds index backend detail and dirty beta-feedback 401 backend detail, asserting both rethrown errors use route-specific generic messages.
- Verification: `cd web && npm run test -- lib/worlds/server.test.ts lib/beta-feedback/server.test.ts` first failed with 2 failures against unpatched server loaders because raw backend details were preserved in thrown server errors, then passed with 5 tests after remediation; `cd web && npm run lint`, `cd web && npm run typecheck`, and `cd web && npm run check:next-env` passed; full `cd web && npm run test` passed with 52 files and 203 tests; `cd web && npm run build` passed with `next-env.d.ts` restored and checked; `cd web && npm run test:e2e` passed with 21 tests and `cd web && npm run check:next-env` passed afterward. OpenSpec strict validations and `git diff --check` passed after docs update.
- Follow-up notes: Continue Web/e2e audits for remaining route handlers, proxy response shaping, server-side loader response DTOs, role boundary, client-side rendering sinks, product normal-use flows, and spec/history drift. Push after successful commits unless the user changes that instruction.

## Post-v1.1 RC Audit and Hardening Web proxy JSON error body normalization entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Web same-origin proxy response security remediation for F-109.
- Finding: F-109 found `web/lib/auth/proxy.ts` central `buildProxyResponse()` relaying non-204 backend response bodies as raw bytes. Auth, generic API, worlds, runtime, and private-beta proxies therefore could return dirty backend JSON error bodies containing provider secrets, auth tokens, storage refs, filesystem/object paths, local model paths, raw prompt/output markers, prompt snapshot refs, bytes, or base64-like evidence to browser clients even after UI-visible error text was normalized.
- Summary: Added an architecture-contracts scenario for Web proxy JSON error-body normalization and sanitized non-2xx JSON response bodies centrally in `buildProxyResponse()` using the shared backend-error detail detector, while preserving successful JSON, binary/no-content responses, streaming responses, and explicit auth cookie relay behavior.
- Files changed: web/lib/auth/proxy.ts, web/lib/auth/proxy.test.ts, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added proxy regression coverage for dirty backend JSON `detail` payloads containing `rawPrompt`, bearer-token, storage URI, and `media://` markers plus safe JSON errors that must remain byte-for-byte unchanged, asserting the proxied body uses a generic message, preserves safe review status, omits sensitive storage fields, and continues stripping backend `Set-Cookie` unless explicitly relayed.
- Verification: `cd web && npm run test -- lib/auth/proxy.test.ts` first failed against unpatched `buildProxyResponse()` because raw backend JSON detail was relayed, then passed with 6 tests after remediation; the proxy suite passed with 6 files and 19 tests; Web lint, typecheck, `check:next-env`, full unit suite, build, and Playwright e2e passed before commit, with `next-env.d.ts` restored and checked after build/e2e. OpenSpec strict validations and `git diff --check` passed before commit.
- Follow-up notes: Continue Web/e2e audits for remaining route handlers, proxy method exposure, server-loader response DTOs, role boundary, client-side rendering sinks, local query construction, product normal-use flows, and spec/history drift. Push after successful commits unless the user changes that instruction.

## Post-v1.1 RC Audit and Hardening platform-admin player record management entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend product/security consistency remediation for F-110.
- Finding: F-110 found player journal, notification, and intervention routes computing admin response visibility with `context.is_platform_admin or context.role == world_admin` while using world-admin-only role checks for cross-user access and all-user listing. Platform admins without direct world membership therefore received 403 or empty self-scoped lists on workflows that world admins could use.
- Summary: Added an architecture-contracts scenario for platform-admin player record management and reused the existing management predicate for player journal, in-world notification, and player intervention cross-user/list/create decisions while preserving member-only restrictions and member-safe DTO shaping.
- Files changed: backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added regression coverage for a platform admin without world membership listing another user's player journal, listing all notifications and interventions, and creating an intervention for that member while receiving admin-visible fields.
- Verification: `cd backend && uv run pytest tests/test_api_worlds.py::test_platform_admin_manages_player_records_without_world_membership -q` first failed with a 403 on platform-admin cross-user player journal access, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_worlds.py::test_knowledge_player_guardrail_apis_and_acceptance_gap_fixes tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope tests/test_api_permission_matrix.py -q` passed with 5 tests; focused `cd backend && uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` and `cd backend && uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 573 tests and 8 skipped. OpenSpec strict validations and `git diff --check` passed after docs update.
- Follow-up notes: Continue Web/e2e audits for remaining route handlers, proxy method exposure, server-loader response DTOs, role boundary, client-side rendering sinks, local query construction, product normal-use flows, and spec/history drift. Push after successful commits unless the user changes that instruction.


## Post-v1.1 RC Audit and Hardening agent memory worldline validation entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend memory/worldline security remediation for F-111.
- Finding: F-111 found `MemoryService.search()` and `MemoryService.delete_scope()` accepted request scopes and called the configured memory backend before validating that an explicit `worldline_id` belongs to the requested `world_id`. For external memory backends, invalid or cross-world worldline identifiers could cross the backend/provider boundary before local validation, and then surface as inconsistent API errors.
- Summary: Added an architecture-contracts OpenSpec scenario requiring agent memory backend calls to validate worldline scope first, resolved memory search/delete worldline IDs before backend calls, passed resolved scopes to backend search/delete operations, and mapped API search/forget validation failures to 422 responses.
- Files changed: backend/packages/memory/src/noveland/memory/service.py, backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_memory_backend.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Added a spy-backend service regression proving invalid cross-world worldline search/delete are rejected before backend search/delete calls, and extended the agent memory API test to assert cross-world worldline search/forget return 422 while valid admin memory workflows still pass.
- Verification: `cd backend && uv run pytest tests/test_memory_backend.py::test_memory_service_rejects_invalid_worldline_before_backend_search_or_delete -q` first failed with `backend.search_calls == 1`, then passed after remediation; `cd backend && uv run pytest tests/test_api_worlds.py::test_world_admin_manages_agent_memory tests/test_memory_backend.py::test_memory_service_rejects_invalid_worldline_before_backend_search_or_delete -q` passed with 2 tests; `cd backend && uv run pytest tests/test_memory_backend.py -q` passed with 17 tests; focused backend ruff/mypy passed for memory service, worlds API, and their updated tests; full backend `ruff`, `mypy`, and `pytest` passed with 574 tests and 8 skipped; OpenSpec strict validations and `git diff --check` passed after docs update.
- Follow-up notes: Continue read-only audit of remaining worldline/member response edges, especially API routes where existing invalid-worldline behavior returns empty lists rather than explicit 4xx responses, plus Web/e2e route-handler and product normal-use drift.


## Post-v1.1 RC Audit and Hardening agent memory read-route worldline validation entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend agent memory API worldline validation remediation for F-112.
- Finding: F-112 found that after F-111 fixed memory search/forget, adjacent memory read/profile routes still handled invalid worldlines inconsistently: memory list returned `200 []` for a cross-world `worldline_id`, while profile snapshot read and refresh raised unhandled `MemoryValidationError` exceptions instead of returning a validation response.
- Summary: Extended the architecture-contracts OpenSpec memory scenario, made `MemoryService.list_memories()` resolve and validate worldline scope before backend list calls, and mapped list/profile-snapshot/refresh `MemoryValidationError` failures to 422 responses in the worlds API while preserving valid memory list/snapshot behavior.
- Files changed: backend/packages/memory/src/noveland/memory/service.py, backend/services/api/src/noveland/services/api/worlds.py, backend/tests/test_memory_backend.py, backend/tests/test_api_worlds.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended the spy-backend memory service regression to require invalid list scope to raise before backend calls, and extended the agent memory API regression so list, profile snapshot read, profile snapshot refresh, search, and forget all return 422 for cross-world worldline IDs.
- Verification: `cd backend && uv run pytest tests/test_memory_backend.py::test_memory_service_rejects_invalid_worldline_before_backend_search_or_delete tests/test_api_worlds.py::test_world_admin_manages_agent_memory -q` first failed on the unpatched list/profile behavior, then passed with 2 tests; `cd backend && uv run pytest tests/test_memory_backend.py -q` passed with 17 tests; focused backend ruff/mypy passed for memory service, worlds API, and their updated tests; full backend `ruff`, `mypy`, and `pytest` passed with 574 tests and 8 skipped; OpenSpec strict validations and `git diff --check` passed after docs update.
- Follow-up notes: Continue invalid-worldline behavior audit outside agent memory, especially worldline query parameters in reader/player/member routes and Web clients that may mask 422 errors as empty states.


## Post-v1.1 RC Audit and Hardening player privacy request-list worldline validation entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend player privacy API worldline validation remediation for F-113.
- Finding: F-113 found `GET /worlds/{world_id}/player/privacy/export?worldline_id={other_worldline_id}` rejected a cross-world worldline through `PlayerPrivacyService._resolve_worldline_id()`, but adjacent `GET /worlds/{world_id}/player/privacy/requests?worldline_id={other_worldline_id}` returned `200 []` because request listing filtered by the supplied UUID without validating it belonged to the requested world.
- Summary: Extended the architecture-contracts OpenSpec worldline scenario, updated `PlayerPrivacyService.list_requests()` to resolve and validate explicit worldline scope before applying request-list filters, and mapped list-route `PlayerPrivacyNotFoundError` / validation failures through the existing API 404/400 helpers.
- Files changed: backend/packages/player_privacy/src/noveland/player_privacy/service.py, backend/services/api/src/noveland/services/api/player_privacy.py, backend/tests/test_api_player_privacy.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended `test_player_privacy_rejects_cross_worldline_requests` so privacy export and privacy request list both reject cross-world worldline IDs.
- Verification: `cd backend && uv run pytest tests/test_api_player_privacy.py::test_player_privacy_rejects_cross_worldline_requests -q` first failed with request list returning 200, then exposed missing API error mapping, then passed; `cd backend && uv run pytest tests/test_api_player_privacy.py -q` passed with 3 tests; focused backend ruff/mypy passed for player privacy service, API route, and tests; full backend `ruff`, `mypy`, and `pytest` passed with 574 tests and 8 skipped; OpenSpec strict validations and `git diff --check` passed after docs update.
- Follow-up notes: Continue invalid-worldline behavior audit for reader media, visual/speech generation, invocation filters, and Web clients that might present invalid scopes as empty states.

## Post-v1.1 RC Audit and Hardening reader media worldline validation entry

- Date: 2026-06-12
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Scope: Backend reader media worldline isolation remediation for F-114.
- Finding: F-114 found `ReaderMediaDeliveryService.list_media()` filtering directly on an explicit `worldline_id` without first validating that the worldline belongs to the requested world. Detail and download paths also compared against caller-supplied worldline UUIDs rather than a resolved same-world worldline.
- Summary: Added an architecture-contracts scenario for reader media invalid worldline rejection, resolved explicit reader media worldline scopes through `Worldline` before list/detail/download filtering, and mapped invalid scopes through the existing reader media 404 response.
- Files changed: backend/packages/reader_delivery/src/noveland/reader_delivery/service.py, backend/services/api/src/noveland/services/api/reader_media.py, backend/tests/test_api_reader_media.py, openspec/changes/audit-and-hardening-post-v1-1-rc/specs/architecture-contracts/spec.md, openspec/changes/audit-and-hardening-post-v1-1-rc/tasks.md, and harness docs.
- Tests added/updated: Extended `test_reader_media_rejects_cross_world_and_cross_worldline_requests` so reader media list requests reject a cross-world `worldline_id` instead of returning an empty success.
- Verification: `cd backend && uv run pytest tests/test_api_reader_media.py::test_reader_media_rejects_cross_world_and_cross_worldline_requests -q` first failed before remediation because cross-world reader media list returned `200`, then passed with 1 test after remediation; `cd backend && uv run pytest tests/test_api_reader_media.py -q` passed with 5 tests; focused backend ruff/mypy passed for reader delivery service, reader media API, and the updated test after ruff fixed import ordering. Full backend `ruff`, `mypy`, and `pytest` passed with 574 tests and 8 skipped. OpenSpec strict validations and `git diff --check` passed after docs update.
- Follow-up notes: Continue invalid-worldline behavior audit for visual/speech generation, invocation filters, member/player DTOs, and Web clients that might present invalid scopes as empty states. Push after successful commits unless the user changes that instruction.
