# Active Session Handoff

- Date: 2026-06-12T14:26:40+00:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-115 are remediated on this branch; latest batch is F-115 speech list worldline validation.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-115 batch: d8aae91 fix(reader-media): validate worldline scope.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server status was rechecked before this continuation: branch matched origin at d8aae91 after F-114 push, worktree started clean/synced for F-115, active OpenSpec strict validation passed, and Noveland Postgres/NATS were healthy.
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

- Reconfirmed realtime branch/worktree/OpenSpec/container status using SSH/CLI only.
- Continued invalid-worldline audit outside reader media, focusing on speech voice profile, agent voice binding, and transcript list boundaries.
- Reproduced F-115 with a temporary CLI script using existing speech API fixtures: cross-world list scopes raised uncaught speech service exceptions.
- Added an architecture-contracts scenario requiring speech list routes to reject invalid explicit worldline scope with handled client errors.
- Changed speech list API handlers to map invalid service-level worldline scope failures through existing 422 responses.
- Added speech API regression coverage for cross-world voice profile, agent binding, and transcript list rejection.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_speech.py::test_speech_lists_reject_cross_worldline_requests -q` first failed with an uncaught `SpeechValidationError`, then passed with 1 test after remediation.
- `cd backend && uv run pytest tests/test_api_speech.py -q` passed with 2 tests.
- Focused `cd backend && uv run ruff check services/api/src/noveland/services/api/speech.py tests/test_api_speech.py` and matching mypy command passed.
- OpenSpec strict validations and `git diff --check` passed after docs update.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 575 tests and 8 skipped.

## Remaining Work

1. Continue backend audits for remaining invalid-worldline behavior drift outside speech list routes, especially visual generation, media job/source filters, invocation-adjacent filters, observability filters, and member/player DTOs.
2. Continue Web/e2e audit for remaining route handlers, proxy method exposure, server-side loader response DTOs, role boundary, client-side rendering sinks, and local query construction.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Push after successful commits unless the user changes that instruction.

## Finding F-115

- Speech voice profile, agent voice binding, and transcript list routes should catch service-level invalid worldline failures and return handled client errors.
- The remediation preserves valid speech list behavior and maps cross-world speech list scopes through existing 422 responses.
- Residual risk: audit remaining worldline query filters and Web empty-state handling outside speech list routes.
