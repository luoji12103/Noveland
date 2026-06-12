# Active Session Handoff

- Date: 2026-06-13T16:45:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-124 are remediated on this branch; latest batch is F-124 conversation live WebSocket origin hardening.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-124 batch: 79d74cd fix(realtime): sanitize stream setup errors.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server status was rechecked before this continuation: branch matched origin at 79d74cd, worktree started clean for F-124 after F-123 push, active OpenSpec strict validation passed, specs strict validation passed with 76 specs, and Noveland Postgres/NATS were healthy.
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

- Continued backend/Web realtime security audit after F-123 from a clean pushed branch.
- Identified F-124: conversation live WebSocket origin validation compared only hostnames and ignored scheme/port.
- Added an architecture-contracts scenario requiring full same-origin WebSocket boundaries with HTTP-to-WebSocket scheme equivalence.
- Added a focused API regression showing `Origin: http://testserver:4444` was accepted before remediation.
- Changed `_origin_allowed()` to compare normalized scheme, hostname, and effective port while preserving valid same-origin TestClient behavior.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_realtime.py::test_conversation_live_websocket_rejects_cross_port_origin -q` first failed because `Origin: http://testserver:4444` was accepted, then passed after remediation.
- `cd backend && uv run pytest tests/test_api_realtime.py::test_conversation_live_websocket_rejects_cross_port_origin tests/test_api_realtime.py::test_conversation_live_websocket_enforces_origin_and_admin_controls -q` passed with 2 tests.
- `cd backend && uv run pytest tests/test_api_realtime.py -q` passed with 7 tests.
- Focused `cd backend && uv run ruff check services/api/src/noveland/services/api/realtime.py tests/test_api_realtime.py` and matching mypy command passed.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 580 tests and 8 skipped.

## Remaining Work

1. Continue backend/Web realtime audits for live socket client assumptions, close reason safety, WebSocket command error redaction, and remaining member/admin DTO boundaries.
2. Continue Web/e2e audit for server-side loader response DTOs, client-side text sinks, playback empty states when media descriptors are absent, route handlers, and role boundaries.
3. Continue backend audits for remaining observability filters, invocation-adjacent filters, media object/reference subroutes, and member/player DTOs.
4. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
5. Push after successful commits unless the user changes that instruction.

## Finding F-124

- Conversation live WebSocket origin validation should enforce full same-origin boundaries for cookie-authenticated live command surfaces.
- The remediation rejects missing/malformed/cross-scheme/cross-port origins before authentication or command processing while preserving valid same-origin WebSocket use.
- Residual risk: continue auditing WebSocket close reasons and command error payloads for sensitive detail exposure.
