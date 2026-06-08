# Active Session Handoff

- Date: 2026-06-08T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-023 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Baseline before branch: main and origin/main at 1ffbf8a7876a5ddc10789db2339cf2efba125c76, commit docs(openspec): archive v1.1 normal use release candidate.
- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-023 batch: d497773 fix(security): redact member release profile evidence.
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

- Reconfirmed server state after F-022: branch feature/audit-and-hardening-post-v1-1-rc, HEAD d497773 before this batch, clean worktree, active OpenSpec change in progress, Postgres/NATS healthy.
- Audited member-readable worlds.py world bible DTOs and confirmed source_material, continuity_config, and metadata exposure to ordinary world members.
- Recorded F-023: member-readable world bible responses exposed raw source material/import notes, continuity config, and metadata.
- Added an architecture-contracts OpenSpec delta requiring member world bible responses to omit source/config/metadata internals while preserving safe canon, setting, forbidden-change, sequel-boundary, continuity-status, identity, and timing fields.
- Added role-aware response shaping. World admins retain world bible source material, continuity config, and metadata; ordinary members receive source_material="", continuity_config={}, and metadata={}.
- Expanded world bible API regression coverage to compare admin-preserved source/config/metadata fields against member-redacted payloads.

## Verification This Batch

- uv run pytest tests/test_api_worlds.py::test_world_bible_api_preserves_continuity_contract_and_access: 1 passed.
- uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py: passed.
- uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- openspec validate --specs --strict: 76 passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with remaining non-realtime member DTOs, residual source/evidence refs, worldline isolation checks, and forbidden-data paths.
2. Later audit Web/e2e route handlers and client rendering for CSRF, XSS, auth forwarding, role boundaries, and client-side leaks.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-023

- Member-readable world bible REST responses exposed raw source material/import notes, continuity config, and metadata.
- The remediation makes this response role-aware, preserving canon management internals for admins while returning source_material="", continuity_config={}, and metadata={} to ordinary members.
- Residual risk: remaining source/evidence refs in member-readable DTOs such as presence/scheduled movement, Web proxies/rendering, and broader worldline isolation still need dedicated review.
