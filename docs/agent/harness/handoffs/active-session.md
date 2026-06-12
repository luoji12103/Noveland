# Active Session Handoff

- Date: 2026-06-13T03:20:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-131 are remediated on this branch; latest batch is F-131 reader media reference moderation hardening.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-131 batch: 042944f fix(web): preserve explicit playback media absence.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server status was rechecked before this continuation: branch was `feature/audit-and-hardening-post-v1-1-rc` at 042944f, branch was ahead of upstream by 1 local commit, worktree started clean, active OpenSpec change was in progress, specs strict validation passed with 76 specs, change strict validation passed, and Noveland Postgres/NATS were healthy.
- Only .env.example was observed in the repo; do not read or expose real secrets.

## Guardrails

- Current user instruction: use SSH/CLI only; avoid browser/computer-use plugins and other non-CLI tooling that may interrupt the session.
- Current goal instruction says do not push unless the user explicitly asks; commit locally after verified remediation and leave branch unpushed.
- Do not bypass OpenSpec; add or update spec deltas before behavior-changing fixes.
- Keep real-provider tests opt-in only; do not set NOVELAND_RUN_REAL_PROVIDER_TESTS=1 without explicit user authorization.
- Preserve provider execution through ProviderExecutionService, quota-before-adapter execution, secret redaction, invocation ledger boundaries, media boundaries, worldline isolation, and reader/member/player DTO safety.
- Do not expose resolved secrets, disallowed auth refs, storage URIs, filesystem/object paths, local model paths, raw prompts, raw outputs, prompt snapshot internals, invite tokens, bytes, or base64.
- Do not broaden worlds.py into a catch-all router.
- For UI/e2e use project Playwright/e2e only.

## Completed This Batch

- Continued backend reader/player media safety audit after F-126 from a clean pushed branch.
- Identified F-127: reader media delivery exposed `reader_visible` video objects with active `text/html` MIME as same-origin downloadable media.
- Added a reader-media-delivery OpenSpec scenario requiring reader descriptors/downloads to expose only safe image/audio/video MIME types.
- Added focused reader media regression coverage preserving safe `video/mp4` while hiding `text/html` reader media descriptors, details, and downloads.
- Changed `ReaderMediaDeliveryService` to filter reader objects by whitelisted MIME per asset kind and hide assets that have no safe reader-deliverable objects.
- Identified F-128: player resume still marked playback ready when referenced presentation media had no safe reader-deliverable object, or only objects filtered out by active/scriptable MIME type.
- Added a player-session-stability OpenSpec scenario requiring missing-media recovery for presentation media without safe reader objects.
- Changed `PlayerSessionService` to require referenced presentation media assets to have at least one whitelisted image/audio/video `MediaObject` before returning ready playback.
- Added player session regression coverage for safe media, objectless media, and `text/html` object media.
- Identified F-129: player resume still marked playback ready when referenced presentation media had a safe object but no reader-visible media descriptor/reference.
- Changed `PlayerSessionService` to align readiness with `ReaderMediaDeliveryService.get_media()` descriptor availability while keeping the import lazy to avoid package cycles.
- Extended player session regression coverage for no-reference media returning missing-media.
- Identified F-130: Web playback/scene media resolution substituted unrelated referenced media when explicit presentation media ids were unresolved or omitted from reader descriptors.
- Added a reader-media-delivery OpenSpec scenario requiring Web playback/scene to render missing-media state for unresolved explicit presentation media instead of substituting unrelated referenced media.
- Added `web/features/worlds/playback-media.test.ts` covering unresolved explicit image/audio ids, referenced fallback with no explicit ids, and alternate explicit image resolution.
- Changed `resolveTurnMedia()` so referenced media fallback is used only when the presentation has no explicit media id for that media kind.
- Identified F-131: Reader media delivery ignored applied moderation suppression on referenced surfaces such as conversation turns and sessions.
- Added a reader-media-delivery OpenSpec scenario requiring descriptors/details/downloads to respect applied moderation suppression on worldlines, narrative publications, conversation sessions, and conversation turns.
- Changed `ReaderMediaDeliveryService` to suppress worldline-targeted media and filter moderated narrative publication, conversation session, and conversation turn references before descriptor assembly and object delivery.
- Added reader media API regressions for moderated turn/session references and moderated worldline/narrative publication targets, plus mixed suppressed/unsuppressed reference filtering.

## Verification This Batch

- Temporary CLI reproduction first showed a `reader_visible` video asset with `text/html` object content appearing in reader descriptors and downloading as `200 text/html; charset=utf-8`.
- `cd backend && uv run pytest tests/test_api_reader_media.py::test_reader_media_suppresses_active_content_type_objects -q` first failed because the unsafe object was listed and downloadable, then passed after remediation.
- `cd backend && uv run pytest tests/test_api_reader_media.py -q` passed with 6 tests.
- Focused `cd backend && uv run ruff check packages/reader_delivery/src/noveland/reader_delivery/service.py tests/test_api_reader_media.py` and matching mypy command passed.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 582 tests and 8 skipped.
- Temporary CLI reproduction first showed objectless player-visible presentation media returning `recovery_status=ready` with `open_reader_playback`.
- `cd backend && uv run pytest tests/test_api_player_sessions.py::test_player_session_media_without_safe_reader_objects_is_missing_media -q` first failed before remediation, then passed after remediation.
- `cd backend && uv run pytest tests/test_api_player_sessions.py -q` passed with 5 tests.
- Focused backend ruff/mypy passed for player session service and tests.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 583 tests and 8 skipped.
- Temporary CLI reproduction first showed safe-object/no-reference player-visible presentation media returning `recovery_status=ready`, while reader media returned `[]` and member presentation hid the asset id.
- `cd backend && uv run pytest tests/test_api_player_sessions.py::test_player_session_media_without_safe_reader_objects_is_missing_media -q` passed after remediation.
- `cd backend && uv run pytest tests/test_api_player_sessions.py -q` passed with 5 tests; related player/reader/presentation API tests passed with 14 tests; focused backend ruff/mypy passed for player session service and tests.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 583 tests and 8 skipped after F-129.
- `cd web && npm run test -- features/worlds/playback-media.test.ts` first failed against the old resolver because unresolved explicit presentation media fell through to `referenced-image`, then passed with 3 tests after remediation.
- `cd web && npm run test -- features/worlds/playback-media.test.ts features/worlds/conversation-playback.test.tsx features/worlds/conversation-scene-view.test.tsx` passed with 3 files and 11 tests.
- `cd web && npm run typecheck -- --pretty false` passed.
- `cd web && npm run lint -- features/worlds/playback-media.ts features/worlds/playback-media.test.ts features/worlds/conversation-playback.test.tsx features/worlds/conversation-scene-view.test.tsx` passed via the project lint script.
- Full `cd web && npm run test` passed with 53 files and 212 tests, with existing runtime-admin React act warnings.
- `cd web && npm run build` passed.
- `cd web && npm run check:next-env` passed.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict` with 76 specs, and `git diff --check` passed.
- Web e2e was not run for F-130 because the batch is isolated to shared resolver logic covered by unit/component tests.
- Temporary CLI reproduction first showed applied `takedown_content` moderation on a conversation turn still allowed reader media list/detail/download 200 responses.
- `cd backend && uv run pytest tests/test_api_reader_media.py::test_reader_media_suppresses_moderated_reference_targets -q` first failed against the old implementation, then passed after remediation.
- `cd backend && uv run pytest tests/test_api_reader_media.py::test_reader_media_suppresses_moderated_reference_targets tests/test_api_reader_media.py::test_reader_media_suppresses_moderated_worldline_and_publication_targets tests/test_api_reader_media.py::test_reader_media_keeps_unsuppressed_references_when_one_reference_is_moderated -q` passed with 3 tests.
- `cd backend && uv run pytest tests/test_api_reader_media.py tests/test_api_moderation.py tests/test_api_player_sessions.py tests/test_api_conversation_presentations.py -q` passed with 24 tests.
- Focused backend ruff/mypy passed for reader delivery service and reader media tests.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 586 tests and 8 skipped after F-131.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict` with 76 specs, and `git diff --check` passed after F-131 docs.

## Remaining Work

1. Continue backend moderation target validation breadth, media reference edge cases, and remaining reader/player media boundary audits.
2. Continue Web/e2e audit for remaining client-side text sinks, EventSource failure assumptions, route handlers, and role boundaries.
3. Continue backend audits for remaining observability filters, invocation-adjacent filters, media object/reference subroutes, and member/player DTOs.
4. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
5. Do not push unless the user explicitly asks; keep local branch clean after commits.

## Finding F-127

- Reader media delivery should not serve active document/scriptable MIME types as same-origin reader media.
- The remediation suppresses unsafe object content types from reader descriptors and downloads while preserving safe image/audio/video media delivery.
- Residual risk: continue auditing frontend reader/player behavior when media descriptors are absent or downgraded because objects are unsafe.

## Finding F-128

- Player resume should not advertise ready playback when referenced presentation media has no safe reader-deliverable object.
- The remediation aligns player media readiness with the reader media MIME boundary by requiring a safe image/audio/video object on each referenced presentation media asset.
- Residual risk: continue auditing Web playback and scene empty states when safe media descriptors are absent or downgraded.

## Finding F-129

- Player resume should not advertise ready playback unless referenced presentation media resolves to the same reader media descriptor boundary used by playback.
- The remediation reuses `ReaderMediaDeliveryService.get_media()` so safe objects, safe MIME, reader-visible references, moderation suppression, and descriptor assembly stay aligned.
- Residual risk: continue auditing Web playback and scene behavior when descriptors are absent, downgraded, or replaced by fallback media.

## Finding F-130

- Web playback and scene view should not substitute unrelated referenced media when canonical presentation media ids are explicit but unavailable through reader media descriptors.
- The remediation distinguishes absent explicit ids from unresolved explicit ids inside `resolveTurnMedia()` and preserves referenced fallback only for turns without explicit presentation media for that kind.
- Residual risk: continue Web/e2e route-handler and client-side leak audits, and keep checking backend descriptor/moderation alignment for media references.

## Finding F-131

- Reader media delivery should honor applied moderation suppression on referenced reader surfaces, not only on media assets.
- The remediation suppresses worldline-targeted reader media and filters moderated narrative publication, conversation session, and conversation turn references before descriptors and scoped downloads are served.
- Residual risk: continue auditing moderation target validation and other reader/member DTO paths for similar surface-level suppression gaps.
