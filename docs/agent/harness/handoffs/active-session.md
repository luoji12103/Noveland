# Active Session Handoff

- Date: 2026-06-09T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-026 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-026 batch: 15260df fix(security): redact member conversation internals.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services: Noveland Postgres and NATS containers are healthy on overridden ports. No authoritative Noveland API, Web, or runtime process was observed during this batch.
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

- Reconfirmed server state after F-025: branch feature/audit-and-hardening-post-v1-1-rc, HEAD 15260df before this batch, clean worktree, active OpenSpec change in progress, Postgres/NATS healthy.
- Audited member-readable conversation-scoped narrative artifact list responses and confirmed they bypassed the world-level publication/redaction boundary.
- Recorded F-026: the conversation narrative list exposed draft/unpublished/non-reader-visible artifacts plus source_run_id and arbitrary metadata to ordinary world members.
- Added an architecture-contracts OpenSpec delta requiring member conversation narrative artifact list responses to include only published reader-visible artifacts and omit source run refs and artifact metadata.
- Added role-aware response shaping. World admins retain full conversation artifact list visibility and evidence fields; ordinary members receive only published reader-visible artifacts with source_run_id and metadata redacted.
- Added conversation API regression coverage for published, draft, and non-reader-visible conversation artifacts comparing member-safe and admin-full payloads.

## Verification This Batch

- uv run pytest tests/test_api_conversations.py::test_conversation_narrative_listing_redacts_member_evidence tests/test_api_conversations.py::test_conversation_narrative_generation_and_listing: 2 passed.
- uv run ruff check services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py: passed.
- uv run mypy services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- openspec validate --specs --strict: 76 passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with remaining member-readable DTOs, worldline isolation checks, and forbidden-data paths.
2. Later audit Web/e2e route handlers and client rendering for CSRF, XSS, auth forwarding, role boundaries, and client-side leaks.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-026

- Member-readable conversation-scoped narrative artifact REST responses exposed draft/unpublished/non-reader-visible artifacts and narrative evidence fields to ordinary world members.
- The remediation makes list responses role-aware, preserving draft/source/metadata evidence for admins while restricting ordinary members to published reader-visible conversation artifacts with source_run_id and metadata redacted.
- Residual risk: other member-readable DTOs, Web proxies/rendering, and broader worldline isolation still need dedicated review.
