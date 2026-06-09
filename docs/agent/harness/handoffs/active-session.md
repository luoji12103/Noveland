# Active Session Handoff

- Date: 2026-06-09T23:59:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-035 are remediated and targeted checks passed on this branch. No push performed.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before F-035 batch: d02f804 fix(web): encode provider api path segments.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services: Noveland Postgres and NATS containers are healthy on overridden ports. No authoritative Noveland API/Web/runtime process was started for this batch.
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

- Continued the Web/e2e security audit after F-034.
- Recorded F-035: browser-side speech admin same-origin API helper URLs embedded decoded world, agent, voice profile, binding, and style mapping identifiers directly into frontend API paths.
- Added an architecture-contracts OpenSpec delta requiring browser-side speech admin API clients to preserve fixed same-origin route templates and encoded dynamic segments.
- Encoded dynamic speech admin identifiers for voice profile collection/detail, agent voice bindings, style mappings, transcripts, TTS, and STT helper paths in `web/lib/worlds/speech.ts`.
- Added focused Web speech helper tests proving reserved characters stay inside identifier path segments across representative read and state-changing speech helpers.

## Verification This Batch

- `cd web && npm run test -- lib/worlds/speech.test.ts`: 3 passed.
- `cd web && npm run lint`: passed.
- `cd web && npm run typecheck`: passed.
- `cd web && npm run test`: 44 files and 143 tests passed. Existing React act warnings appeared in runtime-admin test output, but the suite passed.
- `cd web && npm run build`: passed.
- `cd web && npm run check:next-env`: passed.
- `cd web && npm run test:e2e`: attempted and failed on the workspace/conversation e2e after 11 passed and 9 skipped.
- `cd web && npm run test:e2e -- tests/e2e/auth.spec.ts -g "world admin manages workspace pages and conversations"`: first focused rerun failed at a different runtime notice assertion; second focused rerun passed.
- `openspec validate audit-and-hardening-post-v1-1-rc --strict`: passed.
- `openspec validate --changes --strict`: 1 passed.
- `openspec validate --specs --strict`: 76 passed.
- `git diff --check`: passed before commit.

## Remaining Work

1. Continue Web/e2e security audit for remaining Next route handlers, CSRF forwarding, method exposure, response header behavior, client-side data leaks, XSS-prone rendering sinks, and other client helper path construction outside this scoped speech admin API batch.
2. Audit project Playwright/e2e stability and boundary coverage without browser/computer-use plugins.
3. Continue product normal-use flows and spec/history drift audits after the remaining Web/e2e security pass.

## Finding F-035

- Browser-side speech admin same-origin API URL construction appended decoded world/agent/voice profile/binding/style mapping identifiers directly to frontend API paths.
- The remediation encodes dynamic segments for speech voice profile collection/detail, agent voice bindings, style mappings, transcripts, TTS, and STT helper paths, while preserving filters as query data.
- Residual risk: other Web client helpers and Next route handlers still contain many dynamic path constructions that need separate evidence-based review before broad remediation.
