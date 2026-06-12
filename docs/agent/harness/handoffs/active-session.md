# Active Session Handoff

- Date: 2026-06-13T09:00:00+08:00
- Branch: feature/audit-and-hardening-post-v1-1-rc
- Objective: post-v1.1 release-candidate audit, hardening, tests, and records under OpenSpec.
- Status: F-001 through F-145 are remediated on this branch; latest worktree batch is F-145 Web error storage/path variant redaction hardening pending local commit.

## Current Context

- Active branch: feature/audit-and-hardening-post-v1-1-rc.
- Current HEAD before the F-145 commit: b7a19a2e67cba752a3c97e2dbadfec32ca91489c.
- Active OpenSpec change: openspec/changes/audit-and-hardening-post-v1-1-rc/.
- Current server status was rechecked at the start of this batch: branch was `feature/audit-and-hardening-post-v1-1-rc`, local and upstream were even at `b7a19a2`, active OpenSpec change was in progress, specs strict validation passed with 76 specs, Noveland Postgres/NATS were healthy, and API/Web/runtime containers were not running.
- Only .env.example was observed in the repo; do not read or expose real secrets.

## Guardrails

- Current user instruction: use SSH/CLI only; avoid browser/computer-use plugins and other non-CLI tooling that may interrupt the session.
- Current goal instruction says do not push unless the user explicitly asks; commit locally after verified remediation and leave branch unpushed.
- Do not bypass OpenSpec; add or update spec deltas before behavior-changing fixes.
- Keep real-provider tests opt-in only; do not set NOVELAND_RUN_REAL_PROVIDER_TESTS=1 without explicit user authorization.
- Preserve provider execution through ProviderExecutionService, quota-before-adapter execution, secret redaction, invocation ledger boundaries, media boundaries, worldline isolation, and reader/member/player DTO safety.
- Do not expose resolved secrets, disallowed auth refs, storage URIs, filesystem/object paths, local model paths, raw prompts, raw outputs, prompt snapshot internals, invite tokens, bytes, or base64.
- Do not broaden worlds.py into a catch-all router.
- For UI/e2e use project Playwright/e2e only.

## Completed This Batch

- Reconfirmed realtime server state from `/root/code/Noveland`: branch `feature/audit-and-hardening-post-v1-1-rc`, HEAD `b7a19a2`, local branch even with upstream, active OpenSpec change valid, specs strict validation passed with 76 specs, and Postgres/NATS healthy.
- Started three read-only CLI subagent audits for backend boundary review, Web security review, and product/spec drift; all exited without modifying the repository.
- Identified F-145: shared Web backend-error detection missed storage/path variants including `file://`, `s3://`, `gs://`, and `/root/...`, so Web clients, server loaders, API proxies, and event-stream setup error paths could preserve backend filesystem/object-storage evidence in browser-visible errors.
- Added an architecture-contracts scenario requiring Web error sanitization to recognize storage/path variants.
- Extended `web/lib/auth/proxy.test.ts` with a failing regression for `file:///root/...`, `s3://...`, and `/root/...` in non-2xx JSON proxy error bodies.
- Changed `web/lib/safe-error-detail.ts` to classify file URLs, object-storage URL schemes, and common server absolute paths as sensitive while preserving safe business error text.

## Verification This Batch

- `cd web && npm run test -- lib/auth/proxy.test.ts -t "filesystem and object-storage"` first failed because the proxied JSON error body still contained `file:///root/...` and `s3://...`.
- The same focused test passed after remediation.
- Related Web proxy/client/server-loader suite passed with 14 files and 87 tests.
- Full Web gate passed: `npm run lint`, `npm run typecheck`, `npm run test` with 53 files and 213 tests, `npm run build`, and `npm run check:next-env`.
- Final `git diff --check`, `openspec validate audit-and-hardening-post-v1-1-rc --strict`, `openspec validate --changes --strict`, `openspec validate --specs --strict`, and the related Web proxy/client/server-loader suite passed after the handoff/doc update.

## Remaining Work

1. Reproduce and triage read-only backend subagent candidates: platform-only/hidden provider execution through provider smoke/test invocation, speech TTS/STT, image generation/edit, and visual-generation provider refs.
2. Reproduce and triage Web subagent candidates: provider admin data and world overview server loaders may serialize raw admin data to client components before display redaction.
3. Continue product normal-use/spec-history drift review for provider reliability/quota UX, import/export/package UI scope, release notes, and archived v0.9/v1.0/v1.1 evidence.
4. Do not push unless the user explicitly asks; keep local branch clean after commits.

## Finding F-145

- Web error normalization should not rely only on marker keys or `media://`; object-storage refs and server filesystem paths in backend error values are also forbidden browser-visible evidence.
- The remediation expands the shared Web sensitive-error detector used by clients, server loaders, API proxies, and event-stream setup error handling.
- Residual risk: continue auditing Web server loaders and client components for raw admin/provider data serialized into browser props before display-only redaction.
