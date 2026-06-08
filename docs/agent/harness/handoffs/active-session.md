# Active Session Handoff

- Date: 2026-06-08T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-008 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Baseline before branch: main and origin/main at 1ffbf8a7876a5ddc10789db2339cf2efba125c76, commit docs(openspec): archive v1.1 normal use release candidate.
- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-008 batch: bb457bf fix(security): redact member realtime stream internals.
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

- Reconfirmed server state after F-007: branch feature/audit-and-hardening-post-v1-1-rc, HEAD bb457bf before this batch, clean worktree, active OpenSpec change in progress, Postgres/NATS healthy.
- Audited non-realtime member-readable worlds.py run and narrative endpoints after F-007.
- Recorded F-008: the member-readable agent run list REST API serialized prompt_text, response_text, provider_profile_id, and diagnostics to ordinary world members.
- Added an architecture-contracts OpenSpec delta requiring member agent runtime run lists to omit operator-only run internals while preserving safe run status and timing fields.
- Added role-aware agent run list response shaping. Admin consumers retain run internals; ordinary members receive safe identifiers, status/source linkage, and timing fields with prompt, response, provider, and diagnostics redacted.
- Expanded API worlds regression coverage to prove admin list visibility and member list redaction.

## Verification This Batch

- uv run pytest tests/test_api_worlds.py::test_agent_runs_and_narrative_artifacts_api tests/test_api_worlds.py::test_agent_run_apis_filter_by_worldline: 2 passed.
- uv run ruff check services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py: passed.
- uv run mypy services/api/src/noveland/services/api/worlds.py tests/test_api_worlds.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- openspec validate --specs --strict: 76 passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with remaining non-realtime reader/player/member DTOs, worldline isolation checks, and forbidden-data paths.
2. Later audit Web/e2e route handlers and client rendering for CSRF, XSS, auth forwarding, role boundaries, and client-side leaks.
3. Later audit product normal-use flows and spec/history drift.

## Finding F-008

- Member-readable agent run list REST responses exposed prompt_text, response_text, provider_profile_id, and run diagnostics.
- The remediation makes list_agent_runs role-aware, preserving run internals for admins while restricting ordinary members to safe identifiers, status/source linkage, and timing fields with prompt, response, provider, and diagnostics redacted.
- Residual risk: additional non-realtime reader/player/member DTOs, Web proxies/rendering, and broader worldline isolation still need dedicated review.
