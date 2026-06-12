# Active Session Handoff

- Date: 2026-06-12T14:05:36+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-088 are remediated on this branch; latest batch is F-088 remaining package-local JSON sensitive-key normalization.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-088 batch: 8f008a0 fix(member-json): normalize sensitive metadata keys.
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

- Continued backend sanitizer normalization audit after F-087, focusing on remaining package-local JSON filters in private beta, player privacy, and moderation.
- Recorded/remediated F-088: private beta invite metadata, player privacy export/request JSON, and moderation report/review metadata sanitizers missed camelCase/compact sensitive keys such as `rawPrompt`, `rawOutput`, `storageUri`, and `promptSnapshotId`.
- Updated architecture-contracts OpenSpec before implementation.
- Changed `PrivateBetaService`, `PlayerPrivacyService`, and `ModerationService` JSON sanitizers to normalize keys before sensitive marker comparison and expanded value marker matching for compact/camelCase sensitive terms.
- Extended private beta invite, player privacy export, and moderation report API coverage so unsafe key variants fail before remediation and safe metadata survives after remediation.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_private_beta.py::test_admin_invite_lifecycle_redeem_and_profile_bootstrap_are_safe tests/test_api_player_privacy.py::test_player_privacy_export_is_player_scoped_and_redacted tests/test_api_moderation.py::test_reader_can_create_report_and_admin_can_review_without_leaks -q` first failed on unredacted camelCase sensitive keys, then passed with 3 tests after remediation.
- `cd backend && uv run pytest tests/test_api_private_beta.py tests/test_api_player_privacy.py tests/test_api_moderation.py -q` passed with 12 tests.
- Focused `uv run ruff check packages/private_beta/src/noveland/private_beta/service.py packages/player_privacy/src/noveland/player_privacy/service.py packages/moderation/src/noveland/moderation/service.py tests/test_api_private_beta.py tests/test_api_player_privacy.py tests/test_api_moderation.py` passed.
- Focused `uv run mypy packages/private_beta/src/noveland/private_beta/service.py packages/player_privacy/src/noveland/player_privacy/service.py packages/moderation/src/noveland/moderation/service.py tests/test_api_private_beta.py tests/test_api_player_privacy.py tests/test_api_moderation.py` passed.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

## Remaining Work

1. Continue Web/e2e audit for remaining local query navigation, route handlers, proxy method exposure, response shaping, role boundary, evidence redaction, and client-side rendering sinks.
2. Continue backend audits for remaining reader/member/player DTO exposure boundaries, especially source evidence and non-event persistence outside the recently remediated run/replay/snapshot/player-choice/privacy-export/presentation/media/agent catalog/player-session/feedback/private-beta/moderation paths.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless explicitly requested.

## Finding F-088

- Package-local metadata sanitizers must treat snake_case, camelCase, compact, and mixed-punctuation sensitive keys as equivalent across onboarding, privacy, and moderation workflows.
- The remediation removes or redacts these key variants before persistence/readback while preserving safe metadata fields.
- Residual risk: continue auditing other package-local metadata sanitizers and frontend/API proxy surfaces for normalization drift and inconsistent forbidden-value markers.
