# Active Session Handoff

- Date: 2026-06-08T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-006 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Baseline before branch: main and origin/main at 1ffbf8a7876a5ddc10789db2339cf2efba125c76, commit docs(openspec): archive v1.1 normal use release candidate.
- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-006 batch: 9477523 fix(security): redact media lineage related asset refs.
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

- Reconfirmed realtime server state after F-005: branch feature/audit-and-hardening-post-v1-1-rc, HEAD 9477523 before this batch, clean worktree, active OpenSpec change in progress, Postgres/NATS healthy.
- Audited member-readable media metadata-bearing DTOs after F-005.
- Recorded F-006: visible media asset/context/input/tag/collection/item/references/lineage DTOs carried arbitrary admin-authored metadata without member response sanitization.
- Added an architecture-contracts OpenSpec delta requiring member media metadata redaction while preserving safe metadata and admin full metadata visibility.
- Added recursive API-layer member metadata sanitization across member-facing media asset, context, input, tag, collection, collection item, references, and lineage responses.
- Added regression coverage proving member top-level and nested metadata omit forbidden keys/values while admin asset/reference metadata preserves internal fields.

## Verification This Batch

- uv run pytest tests/test_api_media.py tests/test_api_reader_media.py: 14 passed.
- uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py: passed.
- uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- openspec validate --specs --strict: 76 passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with world event payloads, reader/player DTOs, worldline isolation checks, and non-media forbidden-data paths.
2. Later audit Web/e2e route handlers and client rendering for CSRF, XSS, auth forwarding, role boundaries, and client-side leaks.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-006

- Member-readable media DTOs exposed arbitrary metadata copied from admin-authored metadata_json fields.
- The remediation recursively removes sensitive metadata keys and leak-pattern string values from non-admin member responses while preserving safe metadata and admin full metadata visibility.
- Residual risk: non-media reader/player/member DTOs and world event payloads still need dedicated forbidden-data review.
