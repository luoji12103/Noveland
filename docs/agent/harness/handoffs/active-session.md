# Active Session Handoff

- Date: 2026-06-13T09:18:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-146 are remediated on this branch; latest batch is F-146 provider execution visibility hardening.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before the F-146 commit: 5134473 fix(web): redact storage path error variants.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server status was rechecked at the start of this batch: branch was `feature/audit-and-hardening-post-v1-1-rc`, local and upstream were even at `5134473`, active OpenSpec change was in progress, worktree contained the in-progress F-146 edits from the prior handoff, and Noveland Postgres/NATS were healthy.
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

- Confirmed realtime server state from `/root/code/Noveland`: branch `feature/audit-and-hardening-post-v1-1-rc`, HEAD `5134473`, local branch even with upstream, active OpenSpec change in progress, and Postgres/NATS healthy.
- Resumed F-146 from the prior in-progress worktree and inspected the provider execution visibility diff before running tests.
- Remediated F-146: provider smoke-test and test-invocation routes now pass caller platform-admin context into provider execution requests, and provider registry/execution resolution applies that context before primary/fallback provider adapter execution.
- Added a provider-system scenario requiring world-admin provider execution to respect registry visibility.
- Added `test_provider_test_execution_respects_world_admin_visibility`, covering hidden/developer-only global provider rejection for detail, smoke-test, explicit test-invocation, and routed test-invocation, plus no health-check, invocation, or prompt-snapshot writes.
- Preserved platform-admin diagnostics and existing ProviderExecutionService ownership; no provider execution path was moved into the API router.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_providers.py::test_provider_test_execution_respects_world_admin_visibility -q` passed.
- `cd backend && uv run pytest tests/test_api_providers.py tests/test_provider_execution_service.py -q` passed with 31 tests.
- Focused backend ruff/mypy passed for changed provider/API/test files.
- `git diff --check`, `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, and `openspec validate --specs --strict` passed; specs validation covered 76 specs.
- Full backend gate passed: `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` with 588 passed and 8 skipped.

## Remaining Work

1. Reproduce and triage remaining provider execution visibility candidates: speech TTS/STT, image generation/edit, and visual-generation provider refs.
2. Reproduce and triage Web subagent candidates: provider admin data and world overview server loaders may serialize raw admin data to client components before display redaction.
3. Continue product normal-use/spec-history drift review for provider reliability/quota UX, import/export/package UI scope, release notes, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless the user explicitly asks; keep local branch clean after commits.

## Finding F-146

- World-admin provider execution must not use platform-admin provider visibility unless the caller is a platform admin.
- The remediation moves caller platform-admin context through `ProviderExecutionRequest`, provider registry explicit/routed resolution, fallback lookup, smoke-test, and test-invocation before adapter execution or evidence writes.
- Residual risk: continue auditing speech, image, and visual-generation routes for equivalent provider visibility assumptions.
