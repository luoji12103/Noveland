# Active Session Handoff

- Date: 2026-06-09T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-025 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Baseline before branch: main and origin/main at 1ffbf8a7876a5ddc10789db2339cf2efba125c76, commit docs(openspec): archive v1.1 normal use release candidate.
- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-025 batch: c9d1841 fix(security): redact member presence internals.
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

- Reconfirmed server state after F-024: branch feature/audit-and-hardening-post-v1-1-rc, HEAD c9d1841 before this batch, clean worktree, active OpenSpec change in progress, Postgres/NATS healthy.
- Audited member-readable conversation session list/detail DTOs and confirmed objective, opening_prompt, policy, writer_config, memory_config, and group_context exposure to ordinary world members.
- Recorded F-025: member-readable conversation session responses exposed conversation orchestration internals and provider/plugin/memory configuration.
- Added an architecture-contracts OpenSpec delta requiring member conversation session responses to omit orchestration internals while preserving safe session identity, worldline, scene, title, scope, mode, status, turn counters, terminal state, and timing fields.
- Added role-aware response shaping. World admins retain conversation session orchestration internals; ordinary members receive redacted objective/opening prompt, policy, writer config, memory config, and group context.
- Expanded conversation API regression coverage to compare admin-preserved session internals against member-redacted list/detail payloads.

## Verification This Batch

- uv run pytest tests/test_api_conversations.py::test_conversation_api_enforces_access_and_manual_advance: 1 passed.
- uv run ruff check services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py: passed.
- uv run mypy services/api/src/noveland/services/api/conversations.py tests/test_api_conversations.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- openspec validate --specs --strict: 76 passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with remaining member-readable DTOs, including conversation narrative artifact metadata/source refs, worldline isolation checks, and forbidden-data paths.
2. Later audit Web/e2e route handlers and client rendering for CSRF, XSS, auth forwarding, role boundaries, and client-side leaks.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-025

- Member-readable conversation session REST responses exposed objective text, opening prompts, policy, writer/provider/plugin config, memory config, and group context.
- The remediation makes list/detail responses role-aware, preserving orchestration internals for admins while redacting them for ordinary members.
- Residual risk: conversation narrative artifact metadata/source refs, other member-readable DTOs, Web proxies/rendering, and broader worldline isolation still need dedicated review.
