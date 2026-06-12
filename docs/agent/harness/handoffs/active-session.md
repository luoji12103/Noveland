# Active Session Handoff

- Date: 2026-06-12T07:57:40+00:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-094 are remediated on this branch; latest batch is F-094 Web invocation ledger evidence key normalization.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-094 batch: 9dc7e57 fix(contracts): normalize leaky manifest keys.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server status was rechecked before the batch: branch matched origin at 9dc7e57, only F-094 files were modified, and OpenSpec change validation passed.
- Only .env.example was observed in the repo; do not read or expose real secrets.

## Guardrails

- Current user instruction: use SSH/CLI only; avoid browser/computer-use plugins and other non-CLI tooling that may interrupt the session.
- Current goal instruction: do not push unless explicitly requested.
- Do not bypass OpenSpec; add or update spec deltas before behavior-changing fixes.
- Keep real-provider tests opt-in only; do not set NOVELAND_RUN_REAL_PROVIDER_TESTS=1 without explicit user authorization.
- Preserve provider execution through ProviderExecutionService, quota-before-adapter execution, secret redaction, invocation ledger boundaries, media boundaries, worldline isolation, and reader/member/player DTO safety.
- Do not expose resolved secrets, disallowed auth refs, storage URIs, filesystem/object paths, local model paths, raw prompts, raw outputs, prompt snapshot internals, invite tokens, bytes, or base64.
- Do not broaden worlds.py into a catch-all router.
- For UI/e2e use project Playwright/e2e only.

## Completed This Batch

- Continued Web admin invocation ledger evidence rendering audit after F-093.
- Recorded/remediated F-094: Web invocation ledger evidence redaction missed camelCase/compact sensitive keys such as `storageUri`, `rawPrompt`, and `promptSnapshotId`.
- Updated architecture-contracts OpenSpec before implementation.
- Normalized evidence keys before redaction in `InvocationLedgerAdmin`, expanded forbidden evidence key markers, and replaced sensitive key names with `redacted_N` placeholders before rendering.
- Updated regression coverage to assert sensitive key names/values stay absent and safe non-sensitive evidence fields remain visible.

## Verification This Batch

- `cd web && npm run test -- features/admin/invocation-ledger-admin.test.tsx` first failed on rendered `storageUri` and `rawPrompt`, then passed with 3 tests after remediation.
- `cd web && npm run test -- features/admin/invocation-ledger-admin.test.tsx lib/worlds/invocations.test.ts` passed with 6 tests.
- `cd web && npm run lint`, `cd web && npm run typecheck`, `cd web && npm run check:next-env`, full `cd web && npm run test`, `cd web && npm run build`, and `cd web && npm run test:e2e` passed before commit.
- OpenSpec strict validations and `git diff --check` passed before commit.

## Remaining Work

1. Continue Web/e2e audit for remaining route handlers, proxy method exposure, response shaping, role boundary, client-side rendering sinks, and local query construction.
2. Continue backend audits for remaining reader/member/player DTO exposure boundaries and sanitizer normalization drift, especially Web/server route response shaping, worlds public JSON helpers, and product normal-use paths.
3. Continue product normal-use/spec-history drift review for v1.1 RC onboarding, resume, feedback, quota/degraded state, import/export, provider reliability UX, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless explicitly requested.

## Finding F-094

- Web invocation ledger evidence redaction must treat snake_case, camelCase, compact, and mixed-punctuation storage/prompt/path/snapshot/auth keys as equivalent before rendering admin evidence blocks.
- The remediation redacts both sensitive evidence values and sensitive key names, replacing the latter with redacted placeholders while preserving safe evidence fields.
- Residual risk: continue Web route-handler and component rendering audits for similar response-shaping or client-side evidence leaks.
