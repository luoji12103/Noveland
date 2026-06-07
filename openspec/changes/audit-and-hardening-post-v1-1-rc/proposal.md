## Why

Noveland has reached the v1.1 normal-use release-candidate checkpoint, so the next work must deliberately look for security, isolation, leak, provider-spend, normal-use, and spec/history drift before making additional changes. A single post-RC audit and hardening change keeps findings, fixes, tests, and harness records inside the OpenSpec workflow instead of allowing ad hoc remediation on `main`.

## What Changes

- Establish a post-v1.1 release-candidate audit stream that covers backend security, Web/e2e security, product normal-use flows, and spec/history compliance.
- Record findings with severity, affected boundary, evidence, remediation tasks, targeted tests, and residual risk before or alongside fixes.
- Apply accepted remediations in small batches under a feature branch, with targeted tests and full-gate attempts where practical.
- Preserve existing architecture boundaries: provider calls through `ProviderExecutionService`, no secret/raw prompt/storage/media path leaks, strict worldline and role isolation, and no broad `worlds.py` route growth.
- Keep real-provider tests opt-in only; default audit and regression checks must use fake/mocked providers and must not consume external quota.
- Update harness documents after each meaningful audit/fix batch so handoff state matches the repository.

## Capabilities

### New Capabilities
- `post-v1-1-rc-audit-hardening`: Tracks post-release-candidate audit governance, finding triage, remediation discipline, test evidence, and harness closeout for security, product, and spec compliance hardening.

### Modified Capabilities

None initially. If a finding requires changing an existing capability contract, add the relevant spec delta before implementing that behavior change.

## Impact

- May touch backend packages and API routers related to auth, authorization, providers, media, invocations, memory, player sessions, private beta, beta feedback, moderation, observability, world packaging, conversations, and worlds.
- May touch Web route handlers, API proxies, clients, feature components, and Playwright/project e2e only after the relevant audit finding is documented; UI work must use `impeccable` first.
- May add or update backend pytest, Web unit tests, existing Playwright e2e tests, OpenSpec specs/tasks, and harness documents.
- Does not introduce new external dependencies, real-provider default tests, public launch behavior, or a duplicate readiness/provider/media/moderation/authoring framework.
