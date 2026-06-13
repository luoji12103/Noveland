# Active Session Handoff

- Date: 2026-06-13T09:48:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-147 are remediated on this branch; latest batch is F-147 media/speech provider execution visibility hardening pending local commit.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before the F-147 commit: 92f7c74 fix(providers): enforce execution visibility.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server status was rechecked at the start of this batch: branch was `feature/audit-and-hardening-post-v1-1-rc`, local branch was ahead of upstream by the unpushed F-146 commit, active OpenSpec change was in progress, specs strict validation passed with 76 specs, and Noveland Postgres/NATS were healthy.
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

- Reconfirmed realtime server state and reviewed active handoff plus architecture/provider boundary docs.
- Read-only audit found F-147: image generation/editing and speech TTS/STT services resolved providers with platform-admin visibility while ordinary world-admin API routes did not pass caller context; presentation speech reused the same speech service; authoring distillation and narrative-quality GM/writer generation also omitted caller visibility in provider execution requests.
- Added provider-system OpenSpec coverage for media/speech/provider-backed text execution caller visibility.
- Added failing regressions for image and speech restricted-provider execution; after fixing global-provider test setup, image generate and speech STT returned 201 before remediation.
- Remediated image, speech, presentation speech, authoring distillation, and narrative-quality provider-backed generation to pass caller platform-admin context into provider lookup/capability checks and ProviderExecutionRequest before adapter execution or evidence writes.

## Verification This Batch

- F-147 focused regressions passed after remediation: `cd backend && uv run pytest tests/test_api_images.py::test_images_api_rejects_restricted_provider_execution_for_world_admin tests/test_api_speech.py::test_speech_api_rejects_restricted_provider_execution_for_world_admin -q`.
- Affected image/speech/presentation/authoring/narrative-quality suite passed with 132 tests.
- Focused backend ruff/mypy passed for changed API/service/test files.
- `git diff --check`, `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, and `openspec validate --specs --strict` passed; specs validation covered 76 specs.
- Full backend gate passed: `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` with 590 passed and 8 skipped.

## Remaining Work

1. Continue read-only audit for remaining provider-backed world-admin text paths and provider selection defaults outside the F-147 set.
2. Reproduce and triage Web candidates: provider admin data and world overview server loaders may serialize raw admin data to client components before display redaction.
3. Continue product normal-use/spec-history drift review for provider reliability/quota UX, import/export/package UI scope, release notes, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless the user explicitly asks; keep local branch clean after commits.

## Finding F-147

- World-admin media, speech, authoring, and narrative-quality provider execution must not use platform-admin provider visibility unless the caller is a platform admin.
- The remediation threads caller platform-admin context through image/speech services, presentation speech routes, authoring distillation, and narrative-quality provider resolution and ProviderExecutionRequest construction.
- Residual risk: continue auditing Web server loaders/client props and any less common provider-backed text paths for equivalent caller-visibility assumptions.
