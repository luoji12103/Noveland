# Active Session Handoff

- Date: 2026-06-12T11:10:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-077 are remediated on this branch; latest batch is F-077 member media catalog provenance redaction.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-077 batch: a8dd50b fix(conversations): sanitize member turn transcript text.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services at batch start: Noveland Postgres was healthy on 55432->5432; Noveland NATS was healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started for this batch.
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

- Reconfirmed current state before F-077: branch `feature/audit-and-hardening-post-v1-1-rc`, worktree clean, local ahead 1 at `a8dd50b`, active OpenSpec change valid, and Postgres/NATS healthy.
- Continued backend forbidden-evidence audit across member-readable media catalog/search/detail/lineage and reader media descriptors.
- Recorded/remediated F-077: member media asset responses hid storage URIs and metadata but still returned provider/source IDs, provider kind, actor refs, and lineage source job IDs; member source/provider filters could infer internal provenance.
- Updated the architecture-contracts OpenSpec media catalog, lineage, and metadata-bearing DTO scenarios for internal provenance redaction and source/provider filter rejection.
- Added media API member response shaping for internal provenance fields and rejected member catalog/search filters targeting source event IDs, source invocation IDs, or provider kinds; admin responses remain unchanged.
- Extended media API regression coverage for member/admin provenance field boundaries and internal filter rejection.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_media.py::test_media_api_member_visibility_acl_and_csrf tests/test_api_media.py::test_media_api_member_metadata_redaction_across_visible_records -q` passed with 2 tests.
- `cd backend && uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py` passed.
- `cd backend && uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py` passed.
- `cd backend && uv run pytest tests/test_api_media.py -q` passed with 9 tests.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 567 passed and 8 skipped.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

## Remaining Work

1. Continue backend audits for reader/player presentation and playback DTO text/media references, non-event persistence, and remaining reader/member/player exposure boundaries.
2. Continue Web/e2e security audit on remaining Next route handlers, proxy modules, method exposure, response shaping, role boundary, evidence redaction, and client-side leaks.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless explicitly requested.

## Finding F-077

- Member media asset catalog fields are member-visible, but provider/source IDs, provider kind, actor refs, and lineage source job IDs are internal provenance and can reveal operator/provider execution evidence.
- The remediation keeps safe media asset identity, type, dimensions, visibility, title/description, and sanitized metadata visible to members while blanking internal provenance and preserving full media management records for admins.
- Residual risk: continue auditing Web media proxy/client rendering and reader/player playback DTOs for comparable internal provenance exposure.
