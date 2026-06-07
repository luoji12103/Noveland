# Active Session Handoff

- Date: 2026-06-08T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001, F-002, F-003, and F-004 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Baseline before branch: main and origin/main at 1ffbf8a7876a5ddc10789db2339cf2efba125c76, commit docs(openspec): archive v1.1 normal use release candidate.
- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-004 batch: ca88e17 fix(security): redact member media storage refs.
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

- Reconfirmed realtime server state: branch feature/audit-and-hardening-post-v1-1-rc, HEAD ca88e17 before this batch, clean worktree, active OpenSpec change 12/27 tasks, specs and changes strict validation passing, Postgres/NATS healthy.
- Audited media forbidden-data exposure after F-003.
- Recorded F-004: media job list/detail used get_world_member_context while returning MediaJobRecord with provider_config_json, request_json, result_json, error_text, and created_by_actor_ref.
- Added an architecture-contracts OpenSpec delta requiring member-scoped media routes not to expose media job execution diagnostics.
- Made media job list/detail admin-only via get_world_admin_context while preserving admin media management diagnostics.
- Added regression coverage proving ordinary world members receive 403 for media job list/detail containing internal execution evidence and world admins still receive diagnostics.

## Verification This Batch

- uv run pytest tests/test_api_media.py tests/test_api_reader_media.py: 13 passed.
- uv run ruff check services/api/src/noveland/services/api/media.py tests/test_api_media.py: passed.
- uv run mypy services/api/src/noveland/services/api/media.py tests/test_api_media.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- openspec validate --specs --strict: 76 passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with member-facing media lineage related_assets, metadata-bearing contexts/inputs/references/collections/tags, world event payloads, reader/player DTOs, and worldline isolation checks.
2. Later audit Web/e2e route handlers and client rendering for CSRF, XSS, auth forwarding, role boundaries, and client-side leaks.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-004

- Member media job list/detail routes used get_world_member_context but returned MediaJobRecord, which includes provider_config_json, request_json, result_json, error_text, and created_by_actor_ref.
- The remediation makes media job list/detail admin-only. Ordinary members no longer receive the job DTO, so provider config, prompt-like request JSON, storage_uri/bytes/base64 markers, raw-output-like result JSON, error text, and actor refs stay on admin diagnostics surfaces.
- Residual risk: media lineage related_assets and metadata-bearing member media DTOs still need dedicated forbidden-data review.
