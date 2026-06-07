# Active Session Handoff

- Date: 2026-06-08T00:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 recorded, remediated, tested, and committed at cc423ea; F-002 recorded at 7c900ae, remediated, tested, validated, and committed in the provider boundary batch. No push performed.

## Current Context

- Baseline before branch: main and origin/main at 1ffbf8a7876a5ddc10789db2339cf2efba125c76, commit docs(openspec): archive v1.1 normal use release candidate.
- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Initial baseline before this change: openspec list --json returned no active changes; openspec validate --specs --strict passed 76 specs; openspec validate --changes --strict had no items.
- Current server services: Noveland Postgres and NATS containers are healthy on overridden ports. Noveland API/Web/runtime are not intentionally running for this audit.
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

- Designed the F-002 compatibility remediation against the active provider-system and cost-quota-enforcement OpenSpec deltas.
- Chose the explicit block/degrade path rather than a partial migration because legacy platform provider profiles are not world-scoped ProviderIntegration records.
- Updated ProviderProfileService.invoke_profile to raise a safe configuration error before API key lookup, rate-limit accounting, plugin provider creation, or HTTP transport.
- Updated provider profile test-call behavior to persist failed configuration status without external provider spend.
- Updated service-level provider tests to prove legacy execution does not call mock transport and does not disclose missing secret refs in the disabled path.

## Verification This Batch

- uv run pytest tests/test_model_provider.py tests/test_api_runtime.py tests/test_runtime_daemon.py: 20 passed.
- uv run ruff check packages/adapters/src/noveland/adapters/model_provider.py tests/test_model_provider.py: passed.
- uv run mypy packages/adapters/src/noveland/adapters/model_provider.py tests/test_model_provider.py: passed.
- openspec validate audit-and-hardening-post-v1-1-rc --strict: passed.
- git diff --check: passed before commit.

## Remaining Work

1. Continue backend security audit with worldline isolation and forbidden-data exposure paths.
2. Later audit Web/e2e, product normal-use flows, and spec/history drift.

## Finding F-002

- Legacy ProviderProfileService remains callable from runtime agent runs, conversation/narrative generation, and platform provider-profile test calls.
- The previous path resolved provider_api_keys_json and instantiated plugin providers directly instead of using ProviderExecutionService.
- The current remediation blocks ProviderProfileService.invoke_profile before secret lookup, plugin creation, or HTTP transport, so legacy calls degrade/fail safely until migrated.
- Residual risk: legacy platform provider profiles still need a future migration/replacement path to world-scoped ProviderExecutionService provider integrations for restored live provider functionality.
