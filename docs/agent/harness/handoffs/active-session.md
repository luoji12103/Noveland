# Active Session Handoff

- Date: 2026-06-08T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001, F-002, and F-003 are remediated, tested, validated, and committed on this branch. No push performed.

## Current Context

- Baseline before branch: main and origin/main at 1ffbf8a7876a5ddc10789db2339cf2efba125c76, commit docs(openspec): archive v1.1 normal use release candidate.
- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before this batch: d91b398 fix(security): block legacy provider profile execution.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services: Noveland Postgres and NATS containers are healthy on overridden ports. Noveland API/Web/runtime are not intentionally running for this audit.
- Only .env.example was observed in the repo; do not read or expose real secrets.

## Guardrails

- Do not push unless explicitly requested.
- Do not bypass OpenSpec; add or update spec deltas before behavior-changing fixes.
- Keep real-provider tests opt-in only; do not set NOVELAND_RUN_REAL_PROVIDER_TESTS=1 without explicit user authorization.
- Preserve provider execution through ProviderExecutionService, quota-before-adapter execution, secret redaction, invocation ledger boundaries, media boundaries, worldline isolation, and reader/member/player DTO safety.
- Do not expose resolved secrets, disallowed auth refs, storage URIs, filesystem/object paths, local model paths, raw prompts, raw outputs, prompt snapshot internals, invite tokens, bytes, or base64.
- Do not broaden worlds.py into a catch-all router.
- Do not use browser/computer-use plugins. For UI/e2e use project Playwright/e2e only; use impeccable before any Web UI implementation.

## Completed This Batch

- Audited forbidden-data exposure in media/invocation/member response paths after F-002 closeout.
- Confirmed invocation raw prompt/snapshot APIs are admin-scoped via get_world_admin_context.
- Recorded F-003: member media asset list/search/get routes returned MediaAssetRecord with asset-level storage_uri, preview_uri, and thumbnail_uri copied from media assets.
- Added an architecture-contracts OpenSpec delta requiring member media asset catalog responses to redact internal storage references.
- Updated media API response shaping so non-admin member contexts receive MediaAssetRecord with storage_uri, preview_uri, and thumbnail_uri set to null, while world admins/platform admins retain storage refs.
- Added regression coverage proving member list/search/get redact storage refs and world admin get preserves them.

## Verification This Batch

- uv run pytest tests/test_api_media.py tests/test_api_reader_media.py: 12 passed.
- uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py: passed.
- uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with member-facing media metadata, context/input/reference metadata, world event payloads, and worldline isolation checks.
2. Later audit Web/e2e, product normal-use flows, and spec/history drift.

## Finding F-003

- Member media asset list/search/get routes used get_world_member_context but returned MediaAssetRecord, which includes storage_uri, preview_uri, and thumbnail_uri.
- The current remediation redacts those asset-level storage reference fields for non-admin member contexts.
- Residual risk: media metadata and nested context/input/reference DTOs still need dedicated forbidden-data review.
