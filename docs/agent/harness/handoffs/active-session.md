# Active Session Handoff

- Date: 2026-06-09T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-027 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-027 batch: bb9f329 fix(security): redact member conversation narrative evidence.
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

- Reconfirmed server state after F-026: branch feature/audit-and-hardening-post-v1-1-rc, HEAD bb9f329 before this batch, clean worktree, active OpenSpec change in progress, Postgres/NATS healthy.
- Audited member-readable player privacy export payloads and confirmed they bypassed the F-019 player/member redaction boundary for journal/notification source refs and intervention choice/event linkage.
- Recorded F-027: player privacy exports exposed source evidence refs and choice/event linkage to ordinary world members.
- Added architecture-contracts and player-privacy OpenSpec deltas requiring privacy exports to omit operator-only player interaction evidence while preserving safe player-owned export fields.
- Redacted journal and notification source_ref plus intervention choice_id/event_id from player privacy exports.
- Expanded player privacy export regression coverage to seed those refs/linkages and assert exported values are null.

## Verification This Batch

- uv run pytest tests/test_api_player_privacy.py::test_player_privacy_export_is_player_scoped_and_redacted: 1 passed.
- uv run ruff check packages/player_privacy/src/noveland/player_privacy/service.py tests/test_api_player_privacy.py: passed.
- uv run mypy packages/player_privacy/src/noveland/player_privacy/service.py tests/test_api_player_privacy.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- openspec validate --specs --strict: 76 passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with remaining member-readable DTOs, worldline isolation checks, and forbidden-data paths.
2. Later audit Web/e2e route handlers and client rendering for CSRF, XSS, auth forwarding, role boundaries, and client-side leaks.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-027

- Member-readable player privacy export responses exposed journal/notification source refs and intervention choice/event linkage to ordinary world members.
- The remediation redacts those export evidence fields while preserving safe player-owned export data and request audit summaries.
- Residual risk: other member-readable DTOs, Web proxies/rendering, and broader worldline isolation still need dedicated review.
