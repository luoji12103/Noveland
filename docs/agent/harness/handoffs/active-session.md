# Active Session Handoff

- Date: 2026-06-12T10:05:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-068 are remediated on this branch; latest batch is F-068 agent character profile redaction.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-068 batch: 32c762f fix(worlds): redact player actor profile metadata.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services at F-068 batch start: Noveland Postgres was healthy on 55432->5432; Noveland NATS was healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started for this batch.
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

- Reconfirmed current state after F-067: branch `feature/audit-and-hardening-post-v1-1-rc`, worktree clean, local branch ahead by F-067 only, active OpenSpec change valid, Postgres/NATS healthy.
- Continued backend forbidden-evidence audit across member-readable worlds API profile/metadata surfaces.
- Recorded/remediated F-068: member-readable `GET /worlds/{world_id}/agents` returned arbitrary `Agent.character_profile` JSON to ordinary members, including dynamic reproduction of `storage_uri=media://private/agent-profile` and nested `raw_prompt=operator prompt` values.
- Added an architecture-contracts OpenSpec scenario requiring member agent character profile reads to omit forbidden profile keys/values while retaining safe public characterization fields.
- Generalized the F-067 player actor profile redaction helper into a public profile sanitizer and applied it to non-admin agent catalog responses; admin agent authoring/list responses retain full character profile data.
- Expanded agent catalog coverage to assert admin responses retain full dirty profile metadata while member responses omit storage refs, filesystem paths, raw prompt/output markers, secret refs, and unsafe values.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_worlds.py::test_create_agent_from_preset_materializes_persona_calendar_and_provider_mapping -q` passed with 1 test.
- `cd backend && uv run pytest tests/test_api_worlds.py::test_world_member_can_use_own_player_interaction_records_without_admin_scope tests/test_api_worlds.py::test_create_agent_from_preset_materializes_persona_calendar_and_provider_mapping -q` passed with 2 tests.
- `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 38 tests.
- `cd backend && uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- `cd backend && uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- OpenSpec strict validations and `git diff --check` passed after harness updates.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 564 passed and 8 skipped.

## Remaining Work

1. Commit the completed F-068 batch after final status review; do not push unless explicitly requested.
2. Continue backend forbidden-evidence audits for remaining member/player DTOs, player privacy export contents, and worldline isolation edge cases.
3. Continue Web/e2e security audit on remaining Next route handlers, proxy modules, method exposure, response shaping, role boundary, evidence redaction, and client-side leaks.

## Finding F-068

- Member agent catalog responses exposed arbitrary agent character profile JSON to ordinary world members.
- The remediation sanitizes non-admin agent `character_profile` responses with the shared public profile redaction helper, dropping forbidden keys and sensitive-looking values while retaining safe public characterization fields.
- Residual risk: this focused batch covered agent character profiles only; continue auditing other metadata-bearing member/player responses and exports for historical dirty JSON.
