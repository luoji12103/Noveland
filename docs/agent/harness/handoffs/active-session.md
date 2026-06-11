# Active Session Handoff

- Date: 2026-06-12T21:08:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-062 are remediated on this branch; latest batch is F-062 reader media worldline-scoped download.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-062 batch: 859d3aa fix(web): encode beta feedback server paths.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services at batch start: Noveland Postgres was healthy on 55432->5432; Noveland NATS was healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started outside project Web test/build commands.
- Only .env.example was observed in the repo; do not read or expose real secrets.

## Guardrails

- Current user instruction: use SSH/CLI only; avoid browser/computer-use plugins and other non-CLI tooling that may interrupt the session.
- Current goal instruction: do not push unless explicitly requested.
- Do not bypass OpenSpec; add or update spec deltas before behavior-changing fixes.
- Keep real-provider tests opt-in only; do not set NOVELAND_RUN_REAL_PROVIDER_TESTS=1 without explicit user authorization.
- Preserve provider execution through ProviderExecutionService, quota-before-adapter execution, secret redaction, invocation ledger boundaries, media boundaries, worldline isolation, and reader/member/player DTO safety.
- Do not expose resolved secrets, disallowed auth refs, storage URIs, filesystem/object paths, local model paths, raw prompts, raw outputs, prompt snapshot internals, invite tokens, bytes, or base64.
- Do not broaden worlds.py into a catch-all router.
- For UI/e2e use project Playwright/e2e only.

## Completed This Batch

- Continued backend worldline isolation audit after F-061.
- Recorded/remediated F-062: reader media object descriptors generated unscoped download URLs, and the backend default object download route read storage bytes with `worldline_id=None`.
- Added an architecture-contracts OpenSpec scenario requiring reader media object delivery to require worldline scope before storage reads.
- Generated reader media descriptor download URLs as `/worlds/{world}/reader/media/worldlines/{worldline}/objects/{object}/download`.
- Added a scoped backend route, kept the legacy query-scoped route for explicit scope only, and made missing scope return 404 before storage reads.
- Updated Web reader media URL validation and playback/scene/e2e expectations to accept only exact UUID world/worldline/object download paths.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_moderation.py::test_applied_moderation_takedown_hides_reader_media_without_admin_route_change tests/test_api_reader_media.py` passed with 6 tests; focused backend ruff/mypy passed; full `cd backend && uv run pytest` passed with 563 passed and 8 skipped; focused Web reader media tests passed with 3 files and 13 tests; `cd web && npm run lint`, `cd web && npm run typecheck`, full `cd web && npm run test`, `cd web && npm run build`, focused and full `cd web && npm run test:e2e`, `cd web && npm run check:next-env`, OpenSpec strict validations, and `git diff --check` passed.

## Remaining Work

1. Commit the completed F-062 batch after final status review; do not push unless explicitly requested.
2. Continue backend worldline isolation audit for provider smoke/fallback/test invocation routes, observability readiness, visual/speech generation services, and product normal-use/spec drift.
3. Continue Web/e2e security audit on remaining server loaders outside `web/lib/worlds/server.ts`, Next route handlers, proxy modules, method exposure, response shaping, role boundary, evidence redaction, and client-side leaks.

## Finding F-062

- Backend reader media object downloads lacked required worldline scope on generated descriptor URLs and the default byte route.
- The remediation makes the generated route worldline-scoped, rejects missing worldline scope, preserves query-string rejection in Web rendering, and adds backend/Web regression coverage.
- Residual risk: direct `GET /worlds/{world}/reader/media` and asset detail can still be called without a worldline filter by design; continue the broader worldline isolation audit before closing task 2.2.
