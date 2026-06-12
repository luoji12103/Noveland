# Active Session Handoff

- Date: 2026-06-12T14:36:12+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-090 are remediated on this branch; latest batch is F-090 member media/presentation JSON key normalization.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-090 batch: 41c6673 fix(events): normalize payload sensitive keys.
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

- Continued backend sanitizer normalization audit after F-089 and prioritized member-readable media metadata plus presentation JSON DTOs.
- Recorded/remediated F-090: media member metadata and conversation presentation member JSON sanitizers missed camelCase/compact forbidden keys such as `rawPrompt`, `rawOutput`, `storageUri`, and `promptSnapshotId`.
- Updated architecture-contracts OpenSpec before implementation.
- Changed member media metadata and member presentation JSON key filtering to normalize sensitive keys before comparison and expanded value marker matching for compact/camelCase URI/path/prompt/provider/job/invocation terms.
- Extended media metadata and member presentation GET regression coverage so unsafe key variants fail before remediation and member responses retain safe fields after remediation.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_media.py::test_media_api_member_metadata_redaction_across_visible_records tests/test_api_conversation_presentations.py::test_conversation_presentation_api_renders_visual_speech_and_transcript -q` first failed on unredacted camelCase sensitive keys, then passed with 2 tests after remediation.
- `cd backend && uv run pytest tests/test_api_media.py tests/test_api_conversation_presentations.py -q` passed with 12 tests.
- Focused `uv run ruff check services/api/src/noveland/services/api/media.py services/api/src/noveland/services/api/conversation_presentations.py tests/test_api_media.py tests/test_api_conversation_presentations.py` passed.
- Focused `uv run mypy services/api/src/noveland/services/api/media.py services/api/src/noveland/services/api/conversation_presentations.py tests/test_api_media.py tests/test_api_conversation_presentations.py` passed.
- Full `cd backend && uv run ruff check .`, `cd backend && uv run mypy .`, and `cd backend && uv run pytest` passed with 568 passed and 8 skipped.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and `git diff --check` passed.

## Remaining Work

1. Continue Web/e2e audit for remaining local query navigation, route handlers, proxy method exposure, response shaping, role boundary, evidence redaction, and client-side rendering sinks.
2. Continue backend audits for remaining reader/member/player DTO exposure boundaries and sanitizer normalization drift, especially `multimodal_eval`, `package_contracts`, provider budget/secret helpers, and worlds public JSON helpers.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless explicitly requested.

## Finding F-090

- Member-readable media metadata and presentation JSON sanitizers must treat snake_case, camelCase, compact, and mixed-punctuation forbidden keys as equivalent.
- The remediation removes forbidden key variants from ordinary member responses while preserving safe metadata and playback presentation fields.
- Residual risk: continue auditing other package-local metadata sanitizers and member DTO redaction helpers for normalization drift and inconsistent forbidden-value markers.
