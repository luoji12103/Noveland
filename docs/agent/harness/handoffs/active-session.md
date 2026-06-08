# Active Session Handoff

- Date: 2026-06-09T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-028 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-028 batch: 7992341 fix(security): redact player privacy export evidence.
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

- Reconfirmed server state after F-027: branch feature/audit-and-hardening-post-v1-1-rc, HEAD 7992341 before this batch, clean worktree, active OpenSpec change in progress, Postgres/NATS healthy.
- Audited member-readable scene and location graph payloads and confirmed scene opening_rules and location traversal_rules were exposed to ordinary world members.
- Recorded F-028: member scene and location graph responses exposed admin-authored movement/rule config.
- Added an architecture-contracts OpenSpec delta requiring member scene/location graph responses to omit rule/config internals while preserving safe public scene/location fields.
- Made scene and location-edge list responses role-aware. Admins retain opening/traversal rule config; ordinary members receive empty rule/config objects.
- Expanded location graph regression coverage to seed forbidden markers in opening/traversal rules and assert member redaction plus admin preservation.

## Verification This Batch

- uv run pytest tests/test_api_worlds.py::test_location_graph_and_agent_presence_enforce_world_scope: 1 passed.
- uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py: passed.
- uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- openspec validate --specs --strict: 76 passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with remaining member-readable DTOs, worldline isolation checks, and forbidden-data paths.
2. Later audit Web/e2e route handlers and client rendering for CSRF, XSS, auth forwarding, role boundaries, and client-side leaks.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-028

- Member-readable scene and location graph responses exposed scene opening_rules and location traversal_rules to ordinary world members.
- The remediation redacts those rule/config fields for ordinary members while preserving safe scene/location graph identity fields and admin rule visibility.
- Residual risk: other member-readable DTOs, Web proxies/rendering, and broader worldline isolation still need dedicated review.
