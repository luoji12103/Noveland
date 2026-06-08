# Active Session Handoff

- Date: 2026-06-09T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-029 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-029 batch: b72857a fix(security): redact member scene location rules.
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

- Reconfirmed server state after F-028: branch feature/audit-and-hardening-post-v1-1-rc, HEAD b72857a before this batch, clean worktree, active OpenSpec change in progress, Postgres/NATS healthy.
- Audited member-readable conversation turn payloads and confirmed REST turn lists exposed run_id and error_text despite realtime member streams already redacting them.
- Recorded F-029: member conversation turn responses exposed runtime run handles and provider/plugin error text to ordinary world members.
- Added an architecture-contracts OpenSpec delta requiring member conversation turn responses to omit runtime evidence while preserving safe transcript fields.
- Made conversation turn list responses role-aware. Admins retain run_id/error_text; ordinary members receive null values.
- Expanded conversation API access coverage to assert member turn redaction plus admin runtime evidence preservation.

## Verification This Batch

- uv run pytest tests/test_api_conversations.py::test_conversation_api_enforces_access_and_manual_advance: 1 passed.
- uv run ruff check services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py: passed.
- uv run mypy services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- openspec validate --specs --strict: 76 passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with remaining member-readable DTOs, worldline isolation checks, and forbidden-data paths.
2. Later audit Web/e2e route handlers and client rendering for CSRF, XSS, auth forwarding, role boundaries, and client-side leaks.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-029

- Member-readable conversation turn responses exposed runtime run_id and provider/plugin error_text to ordinary world members.
- The remediation redacts those runtime evidence fields for ordinary members while preserving safe transcript fields and admin diagnostics visibility.
- Residual risk: other member-readable DTOs, Web proxies/rendering, and broader worldline isolation still need dedicated review.
