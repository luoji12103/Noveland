# Active Session Handoff

- Date: 2026-06-12T07:40:40+00:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-093 are remediated on this branch; latest batch is F-093 package and authoring leaky-key normalization.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-093 batch: 988c614 fix(diagnostics): normalize leaky json key variants.
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

- Continued backend import/export and authoring validator audit after F-092.
- Recorded/remediated F-093: world packaging, authoring, and asset generation contract validators missed camelCase/compact leaky keys such as `storageUri`, `rawPrompt`, `promptSnapshotId`, and `filesystemPath`.
- Updated architecture-contracts OpenSpec before implementation.
- Normalized forbidden key comparisons in world packaging, authoring, and asset generation contract validators.
- Updated regression tests so camelCase storage/prompt/path key variants fail before remediation and are rejected after remediation.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_world_packaging.py::test_world_package_import_rejects_forbidden_manifest_values tests/test_authoring_service.py::test_authoring_json_rejects_leaky_values tests/test_asset_generation_service.py::test_policy_rejects_leaky_json_and_preview_validates_worldline -q` first failed with 3 failures on accepted camelCase leaky keys, then passed with 3 tests after remediation; `cd backend && uv run pytest tests/test_api_world_packaging.py tests/test_authoring_service.py tests/test_asset_generation_service.py tests/test_api_asset_generation.py tests/test_authoring_regression_fixture.py -q` passed with 39 tests; focused backend ruff/mypy passed for world packaging, authoring, asset generation contracts, and their updated tests; full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 572 passed and 8 skipped. OpenSpec strict validations and `git diff --check` passed before commit.

## Remaining Work

1. Continue Web/e2e audit for remaining local query navigation, route handlers, proxy method exposure, response shaping, role boundary, evidence redaction, and client-side rendering sinks.
2. Continue backend audits for remaining reader/member/player DTO exposure boundaries and sanitizer normalization drift, especially Web/server route response shaping, worlds public JSON helpers, and product normal-use paths.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless explicitly requested.

## Finding F-093

- Package, authoring, and asset generation validators must treat snake_case, camelCase, compact, and mixed-punctuation storage/prompt/path keys as equivalent.
- The remediation rejects forbidden key variants before package import, authoring metadata/config creation, or asset generation policy/proposal acceptance while preserving safe metadata.
- Residual risk: continue Web/server response-shaping and client-rendering audits for similar boundary drift.
