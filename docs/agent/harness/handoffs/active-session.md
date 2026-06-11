# Active Session Handoff

- Date: 2026-06-12T06:08:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-064 are remediated on this branch; latest batch is F-064 beta feedback reporter triage evidence redaction.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Base before F-064 batch: 10c8c52 fix(speech): reject world-level voice media refs.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server services at F-064 batch start: Noveland Postgres was healthy on 55432->5432; Noveland NATS was healthy on 54222->4222 and 58222->8222. No authoritative Noveland API/Web/runtime process was started for this batch.
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

- Continued backend member/reader/player forbidden-evidence audit after F-063.
- Reviewed speech API, worlds member routes, conversation member routes, media member routes, player session resume, player privacy, and beta feedback surfaces for worldline/ref/data exposure; no confirmed defect was recorded in those slices except beta feedback reporter triage evidence.
- Recorded/remediated F-064: reporter-owned beta feedback reads returned admin triage evidence refs, repair proposal refs, moderation refs, admin actor refs, and metadata after operator triage.
- Added an architecture-contracts OpenSpec scenario requiring reporter/member beta feedback reads to hide admin triage evidence while admin routes retain repair/moderation evidence.
- Made `BetaFeedbackService._read()` role-aware so non-admin reads keep safe report status/severity and reporter-safe evidence kinds only, with metadata stripped; admin reads keep full triage evidence.
- Added focused API regression coverage for admin triage with media job/invocation evidence and reporter reads after triage.

## Verification This Batch

- `cd backend && uv run pytest tests/test_api_beta_feedback.py` passed with 4 tests; `cd backend && uv run pytest tests/test_api_moderation.py tests/test_api_authoring.py` passed with 19 tests; focused backend ruff/mypy passed; OpenSpec strict validations and `git diff --check` passed.
- Full backend/Web gates were not rerun for F-064; full backend pytest passed in the preceding F-063 batch with 564 passed and 8 skipped, and the previous F-062 batch had full Web unit/build/e2e gates passing.

## Remaining Work

1. Commit the completed F-064 batch after final status review; do not push unless explicitly requested.
2. Continue backend forbidden-evidence audits for moderation, observability, privacy export contents, speech/API output, and remaining member/player DTOs.
3. Continue Web/e2e security audit on remaining Next route handlers, proxy modules, method exposure, response shaping, role boundary, evidence redaction, and client-side leaks.

## Finding F-064

- Beta feedback reporter reads exposed admin triage evidence refs and linkage fields after admin triage.
- The remediation keeps full triage evidence on admin reads but hides media job/invocation/admin repair/moderation/actor/metadata fields from reporter/member reads.
- Residual risk: continue reviewing moderation and privacy/export DTOs for similar admin-evidence backflow before closing task 2.4.
