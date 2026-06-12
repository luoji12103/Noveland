# Active Session Handoff

- Date: 2026-06-13T00:58:31+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-125 are remediated on this branch; latest batch is F-125 conversation realtime member turn text redaction.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-125 batch: b688e02 fix(realtime): enforce websocket origin port.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server status was rechecked before this continuation: branch matched origin at b688e02, worktree started clean for F-125 after F-124 push, active OpenSpec strict validation passed, specs strict validation passed with 76 specs, and Noveland Postgres/NATS were healthy.
- Only .env.example was observed in the repo; do not read or expose real secrets.

## Guardrails

- Current user instruction: use SSH/CLI only; avoid browser/computer-use plugins and other non-CLI tooling that may interrupt the session.
- User explicitly requested every commit be pushed; push after successful commits unless the user changes that instruction.
- Do not bypass OpenSpec; add or update spec deltas before behavior-changing fixes.
- Keep real-provider tests opt-in only; do not set NOVELAND_RUN_REAL_PROVIDER_TESTS=1 without explicit user authorization.
- Preserve provider execution through ProviderExecutionService, quota-before-adapter execution, secret redaction, invocation ledger boundaries, media boundaries, worldline isolation, and reader/member/player DTO safety.
- Do not expose resolved secrets, disallowed auth refs, storage URIs, filesystem/object paths, local model paths, raw prompts, raw outputs, prompt snapshot internals, invite tokens, bytes, or base64.
- Do not broaden worlds.py into a catch-all router.
- For UI/e2e use project Playwright/e2e only.

## Completed This Batch

- Continued backend realtime security audit after F-124 from a clean pushed branch.
- Identified F-125: conversation realtime member turn DTOs returned `input_text` and `output_text` unchanged, so sensitive-looking transcript text with raw prompt/output markers could reach member stream deltas and live WebSocket snapshots.
- Added an architecture-contracts scenario requiring member realtime turn payloads to blank sensitive-looking transcript text while preserving safe text.
- Extended stream delta regression coverage and added live WebSocket member snapshot coverage.
- Changed realtime turn payload construction to blank sensitive-looking member transcript text while preserving admin realtime payloads.

## Verification This Batch

- Temporary CLI reproduction using existing in-memory realtime fixtures showed `collect_conversation_stream_delta(..., include_admin_fields=False)` returned `raw_output: provider traceback payload` in member turn `input_text` and `output_text` before remediation.
- `cd backend && uv run pytest tests/test_api_realtime.py::test_conversation_stream_hides_admin_evidence_for_member_payloads tests/test_api_realtime.py::test_conversation_live_member_snapshot_hides_sensitive_turn_text -q` passed with 2 tests.
- `cd backend && uv run pytest tests/test_api_realtime.py -q` passed with 8 tests.
- Focused `cd backend && uv run ruff check services/api/src/noveland/services/api/realtime.py tests/test_api_realtime.py` and matching mypy command passed.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 581 tests and 8 skipped.

## Remaining Work

1. Continue backend/Web realtime audits for close reason safety, live command error payloads, client assumptions around sanitized realtime failures, and remaining member/admin DTO boundaries.
2. Continue Web/e2e audit for server-side loader response DTOs, client-side text sinks, playback empty states when media descriptors are absent, route handlers, and role boundaries.
3. Continue backend audits for remaining observability filters, invocation-adjacent filters, media object/reference subroutes, and member/player DTOs.
4. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
5. Push after successful commits unless the user changes that instruction.

## Finding F-125

- Conversation realtime member turn payloads should enforce the same sensitive-looking transcript redaction as member REST turn responses.
- The remediation blanks sensitive-looking `input_text` and `output_text` for member realtime stream deltas and live WebSocket snapshots while preserving safe text and admin realtime visibility.
- Residual risk: continue auditing WebSocket close reasons, command error payloads, and Web client handling of sanitized realtime failures.
