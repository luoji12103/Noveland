# Active Session Handoff

- Date: 2026-06-12T09:45:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-075 are remediated on this branch; latest batch is F-075 member world bible public canon JSON redaction.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-075 batch: 48e74b3 fix(events): enforce safe world event payloads.
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

- Reconfirmed current state before F-075: branch `feature/audit-and-hardening-post-v1-1-rc`, worktree clean, local/remote synchronized at `48e74b3`, active OpenSpec change valid, and Postgres/NATS healthy.
- Continued backend forbidden-evidence audit across remaining member-readable `worlds.py` response helpers.
- Recorded/remediated F-075: member-readable world bible responses hid `source_material`, `continuity_config`, and `metadata`, but still returned arbitrary public canon JSON fields verbatim.
- Updated the architecture-contracts OpenSpec scenario so member world bible public canon JSON must remove forbidden keys/values while preserving safe canon fields.
- Applied the existing public JSON sanitizer to non-admin `canon_timeline`, `setting_rules`, `forbidden_changes`, and `sequel_boundaries` in `_world_bible_response()`.
- Extended world bible API regression coverage so admin reads retain dirty public canon JSON and member reads retain only safe canon fields.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_worlds.py::test_world_bible_api_preserves_continuity_contract_and_access -q` passed with 1 test.
- `cd backend && uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- `cd backend && uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py` passed.
- `cd backend && uv run pytest tests/test_api_worlds.py -q` passed with 41 tests.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 567 passed and 8 skipped.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

## Remaining Work

1. Commit the completed F-075 batch after final diff/status review; do not push unless explicitly requested.
2. Continue backend audits for member-readable replay/state and other public narrative/canon surfaces, non-event persistence, and remaining reader/member/player exposure boundaries.
3. Continue Web/e2e security audit on remaining Next route handlers, proxy modules, method exposure, response shaping, role boundary, evidence redaction, and client-side leaks.
4. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.

## Finding F-075

- Public world bible JSON fields are intentionally member-readable, but they are arbitrary admin-authored JSON and can carry forbidden evidence if not sanitized.
- The remediation keeps the public canon structure available to members while removing forbidden keys/values, and leaves admin canon-management responses unchanged.
- Residual risk: continue auditing member-readable replay/state and other public narrative/canon text or JSON for comparable forbidden-evidence exposure.
