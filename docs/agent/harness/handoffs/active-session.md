# Active Session Handoff

- Date: 2026-06-12T09:20:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-067 are remediated on this branch; latest batch is F-067 player actor profile redaction.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-067 batch: 3aec09d fix(speech): redact test response internals.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services at F-067 batch start: Noveland Postgres was healthy on 55432->5432; Noveland NATS was healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started for this batch.
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

- Reconfirmed realtime server state: branch `feature/audit-and-hardening-post-v1-1-rc`, local branch synced with origin after the user-requested push of F-065/F-066, active OpenSpec change valid, Postgres/NATS healthy.
- Continued backend forbidden-evidence audit across player/member worlds API surfaces.
- Recorded/remediated F-067: member-readable `GET /worlds/{world_id}/player-actors` and `PUT /worlds/{world_id}/player-actors` returned arbitrary `PlayerActorProfile.profile_json`, allowing storage refs, filesystem paths, raw prompt/output markers, secret/auth refs, bytes, or base64-looking values to reach ordinary members.
- Added an architecture-contracts OpenSpec scenario requiring member player actor profile reads and writes to omit forbidden profile keys/values while retaining safe fields.
- Added player actor profile sanitization before bind persistence and in `_player_actor_response()` so historical dirty records are also redacted on read.
- Expanded member/player interaction coverage to assert bind persistence stores only safe profile fields and simulated historical dirty profile JSON is redacted on member list response.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope -q` passed with 1 test.
- `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 38 tests.
- `cd backend && uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- `cd backend && uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- OpenSpec strict validations and `git diff --check` passed after harness updates.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 564 passed and 8 skipped.

## Remaining Work

1. Commit the completed F-067 batch after final status review; do not push unless explicitly requested.
2. Continue backend forbidden-evidence audits for remaining member/player DTOs, player privacy export contents, and worldline isolation edge cases.
3. Continue Web/e2e security audit on remaining Next route handlers, proxy modules, method exposure, response shaping, role boundary, evidence redaction, and client-side leaks.

## Finding F-067

- Member player actor bind/list responses exposed arbitrary profile JSON to ordinary world members.
- The remediation sanitizes player actor profile JSON on write and read, dropping forbidden keys and sensitive-looking values while retaining safe profile fields.
- Residual risk: this focused batch covered player actor profile DTOs only; continue auditing other profile/metadata-bearing member/player responses and exports for historical dirty JSON.
