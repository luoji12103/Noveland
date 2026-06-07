# Active Session Handoff

- Date: 2026-06-08T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-005 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Baseline before branch: main and origin/main at 1ffbf8a7876a5ddc10789db2339cf2efba125c76, commit docs(openspec): archive v1.1 normal use release candidate.
- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-005 batch: e7e469a fix(security): restrict media job diagnostics to admins.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services: Noveland Postgres and NATS containers are healthy on overridden ports. Other uvicorn/next processes exist on the host, but they were not treated as authoritative Noveland project services for this audit.
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

- Continued media forbidden-data audit after F-004.
- Recorded F-005: member media lineage returned related_assets from MediaLineageService.lineage without applying API-layer storage reference redaction to nested MediaAssetRecord values.
- Added an architecture-contracts OpenSpec delta requiring member media lineage related_assets to redact storage_uri, preview_uri, and thumbnail_uri.
- Shaped MediaAssetLineage.related_assets through the existing _media_asset_record_for_context helper.
- Extended regression coverage proving ordinary world members receive redacted related asset storage refs and world admins retain them.

## Verification This Batch

- uv run pytest tests/test_api_media.py tests/test_api_reader_media.py: 13 passed.
- uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py: passed.
- uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with metadata-bearing media contexts/inputs/references/collections/tags, world event payloads, reader/player DTOs, and worldline isolation checks.
2. Later audit Web/e2e route handlers and client rendering for CSRF, XSS, auth forwarding, role boundaries, and client-side leaks.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-005

- Member media lineage related_assets were returned as full MediaAssetRecord values from the media catalog service, bypassing the F-003 top-level asset redaction helper.
- The remediation redacts storage_uri, preview_uri, and thumbnail_uri for related_assets in non-admin member lineage responses while preserving admin media-management visibility.
- Residual risk: arbitrary metadata on member-visible media context/input/reference/collection/tag DTOs still needs dedicated forbidden-data review.
