# Active Session Handoff

- Date: 2026-06-12T10:30:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-076 are remediated on this branch; latest batch is F-076 member conversation turn transcript text redaction.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-076 batch: f706908 fix(worlds): sanitize world bible public json.
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

- Reconfirmed current state before F-076: branch `feature/audit-and-hardening-post-v1-1-rc`, worktree clean, local/remote synchronized at `f706908`, active OpenSpec change valid, and Postgres/NATS healthy.
- Continued backend forbidden-evidence audit across member-readable conversation turn responses after replay/state was found to expose only clock/sequence/counts.
- Recorded/remediated F-076: member turn list responses hid `run_id` and `error_text`, but still returned arbitrary `input_text` and `output_text` transcript text verbatim.
- Updated the architecture-contracts OpenSpec scenario so member conversation turns must blank sensitive-looking transcript text while preserving safe transcript text.
- Added a conversation API member transcript text sanitizer and applied it to non-admin `_turn_response()` input/output text only; admin responses remain unchanged.
- Extended conversation API regression coverage so admin seed/advance responses retain dirty transcript text while member turn list responses blank sensitive-looking transcript text and continue hiding run/error fields.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_conversations.py::test_conversation_api_enforces_access_and_manual_advance -q` passed with 1 test.
- `cd backend && uv run ruff check services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py` passed.
- `cd backend && uv run mypy services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py` passed.
- `cd backend && uv run pytest tests/test_api_conversations.py -q` passed with 6 tests.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 567 passed and 8 skipped.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

## Remaining Work

1. Continue backend audits for reader/player presentation and playback DTO text/media references, non-event persistence, and remaining reader/member/player exposure boundaries.
2. Continue Web/e2e security audit on remaining Next route handlers, proxy modules, method exposure, response shaping, role boundary, evidence redaction, and client-side leaks.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless explicitly requested.

## Finding F-076

- Conversation turn transcript text is member-visible, but it can still carry forbidden evidence from admin seed text or provider-backed output if not sanitized.
- The remediation keeps safe transcript text visible to members while blanking sensitive-looking text and preserving full transcript text for admin conversation management.
- Residual risk: continue auditing reader/player presentation DTOs, playback surfaces, and media descriptors for comparable forbidden-evidence exposure.
