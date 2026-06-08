# Active Session Handoff

- Date: 2026-06-08T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-012 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Baseline before branch: main and origin/main at 1ffbf8a7876a5ddc10789db2339cf2efba125c76, commit docs(openspec): archive v1.1 normal use release candidate.
- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-012 batch: f090c45 fix(security): redact member schedule rule config.
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

- Reconfirmed server state after F-011: branch feature/audit-and-hardening-post-v1-1-rc, HEAD f090c45 before this batch, clean worktree, active OpenSpec change in progress, Postgres/NATS healthy.
- Audited member-readable worlds.py narrative artifact REST DTOs after F-011.
- Recorded F-012: member-readable narrative artifact list/detail REST responses exposed source_run_id, arbitrary artifact metadata, continuity metadata/status, publication metadata, source_draft_id, published_by_user_id, and publication_gate to ordinary world members.
- Added an architecture-contracts OpenSpec delta requiring member narrative artifact responses to omit operator-only artifact and publication internals while preserving safe published content, identity, conversation linkage, status, visibility, and timing.
- Added role-aware narrative artifact response shaping. World admins retain artifact metadata and publication review evidence; ordinary members receive redacted source run refs, metadata, continuity fields, publication metadata, source draft refs, publisher refs, and publication gate evidence.
- Expanded narrative reader API regression coverage to prove member redaction and admin preservation for source run, metadata, continuity, and publication gate fields.

## Verification This Batch

- uv run pytest tests/test_api_worlds.py::test_narrative_reader_api_supports_filters_and_detail_for_world_members tests/test_api_worlds.py::test_narrative_publication_workflow_filters_reader_visibility tests/test_api_realtime.py::test_world_stream_hides_admin_evidence_for_member_payloads: 3 passed.
- uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py tests/test_api_realtime.py: passed.
- uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py tests/test_api_realtime.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- openspec validate --specs --strict: 76 passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with remaining non-realtime reader/player/member DTOs, worldline isolation checks, and forbidden-data paths.
2. Later audit Web/e2e route handlers and client rendering for CSRF, XSS, auth forwarding, role boundaries, and client-side leaks.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-012

- Member-readable narrative artifact list/detail REST responses exposed operator-only artifact metadata, source run refs, continuity evidence, and publication review/user internals.
- The remediation makes list_narrative_artifacts and get_narrative_artifact role-aware, preserving metadata/publication evidence for admins while restricting ordinary members to safe published narrative artifact fields.
- Residual risk: additional member-readable worlds.py metadata/source DTOs, reader/player DTOs, Web proxies/rendering, and broader worldline isolation still need dedicated review.
