# Active Session Handoff

- Date: 2026-06-12T07:25:08+00:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-092 are remediated on this branch; latest batch is F-092 budget and diagnostics leaky-key normalization.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-092 batch: 42007db fix(provider-secrets): normalize sensitive key variants.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services at batch start: Noveland Postgres and Noveland NATS were healthy. No authoritative Noveland API/Web/runtime process was started outside project test/e2e commands.
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

- Continued backend storage/prompt/path key normalization audit after F-091.
- Recorded/remediated F-092: provider budget policy JSON, multimodal prompt snapshot diagnostics, and narrative quality dashboard evidence checks missed camelCase/compact leaky keys such as `storageUri`, `rawPrompt`, and `promptSnapshotId`.
- Updated architecture-contracts OpenSpec before implementation.
- Normalized leaky key comparisons in provider budget validation, multimodal diagnostics, and narrative quality dashboard sanitization.
- Added regression tests so camelCase storage/prompt/prompt-snapshot keys fail before remediation and are rejected, flagged, or sanitized after remediation.

## Verification This Batch

- `cd backend && uv run pytest tests/test_provider_execution_service.py::test_budget_policy_rejects_camel_case_leaky_metadata tests/test_multimodal_eval_service.py::test_multimodal_eval_detects_camel_case_prompt_snapshot_leaks tests/test_narrative_quality_service.py::test_narrative_quality_dashboard_detects_camel_case_leaky_metadata -q` first failed with 3 failures on unblocked/unflagged camelCase leaky keys, then passed with 3 tests after remediation; `cd backend && uv run pytest tests/test_provider_execution_service.py tests/test_multimodal_eval_service.py tests/test_narrative_quality_service.py -q` passed with 72 tests; focused backend ruff/mypy passed for provider budget, multimodal eval, narrative quality, and their updated tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 572 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.

## Remaining Work

1. Continue Web/e2e audit for remaining local query navigation, route handlers, proxy method exposure, response shaping, role boundary, evidence redaction, and client-side rendering sinks.
2. Continue backend audits for remaining reader/member/player DTO exposure boundaries and sanitizer normalization drift, especially package-local import/export validators, world packaging, authoring/asset generation JSON validators, and worlds public JSON helpers.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless explicitly requested.

## Finding F-092

- Budget and diagnostics JSON checks must treat snake_case, camelCase, compact, and mixed-punctuation storage/prompt/path keys as equivalent.
- The remediation rejects provider budget policy JSON with forbidden leaky key variants and flags/sanitizes multimodal and narrative dashboard evidence without removing safe operational metadata.
- Residual risk: continue auditing remaining package-local import/export validators and Web/server response shaping for the same key-normalization drift.
