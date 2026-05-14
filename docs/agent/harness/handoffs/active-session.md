# Active Session Handoff

- Date: 2026-05-14T00:00:00Z
- Branch: feat/multimodal-diagnostics-dashboard
- Objective: Continue v0.4 Operator/Admin UX Phase 7 Multimodal Diagnostics Dashboard.
- Status: Phase 7 Multimodal Diagnostics Dashboard implementation and full local gate are complete; fast-forward merge to local `main` is next.

## Current Context

- Phase 3-13 backend architecture is complete and frozen through architecture docs, API/data inventories, ADRs, and the multimodal sample-world regression fixture.
- OpenSpec current specs live under `openspec/specs/`.
- v0.4 implementation source of truth is `openspec/changes/v0-4-operator-admin-ux/`.
- v0.4 phases must run in order: Admin UX Foundation, Provider Admin Console, Media Asset Admin Console, Visual Asset Admin Console, Speech Admin Console, Invocation Ledger Browser, Multimodal Diagnostics Dashboard.
- `PRODUCT.md` defines the frontend product context: product register, calm/rigorous/operator-grade personality, no marketing SaaS or gamey admin UI, WCAG AA, keyboard-first, reduced-motion friendly, and color not as sole signal.
- Phase 1 added reusable admin foundation components, platform-admin route guard helper, and CSRF-aware admin request helper. Later phases should reuse these patterns instead of inventing page-local equivalents.
- Phase 2 route decision: keep `/admin/providers` for legacy platform provider profiles and add `/worlds/{worldId}/providers` for Phase 5+ provider integrations.
- Phase 2 implementation adds world-scoped provider integration UI only. It does not alter provider kernel behavior or expose resolved secrets.
- Phase 3 added a media asset admin console using existing media APIs and admin foundation patterns. It did not add storage delivery, public reader media delivery, schema changes, or backend media kernel behavior changes.
- Phase 4 adds a visual asset admin console using existing visual APIs, media references, and admin foundation patterns. It does not add automatic sprite/background generation, background orchestration, nullable worldline visual defaults, schema changes, backend visual behavior changes, or public reader delivery.
- Phase 5 adds a speech admin console using existing speech APIs, voice profile services, media references, and admin foundation patterns. It does not add realtime voice, streaming, local voice server deployment, backend speech behavior changes, schema changes, automatic STT memory writes, or public reader audio delivery.
- Phase 7 should add a multimodal diagnostics dashboard using existing multimodal eval, provider, media, invocation, visual, speech, and long-run eval APIs. Do not add backend diagnostic rule changes, schema changes, public launch gate changes, duplicate release/eval framework, provider execution changes, daemon behavior, streaming, or reader/member evidence exposure unless the Phase 7 plan explicitly requires them.
- `.opencode/` is ignored and must not be committed.
- Do not push unless explicitly requested.

## Phase 13 Guardrails To Preserve

- Do not expose resolved provider secrets.
- Do not expose storage URIs, filesystem paths, bytes, base64, raw prompts, or raw outputs in event payloads or reader/member routes.
- Do not bypass backend ACLs or validation from Web code.
- Do not use `narrative_artifacts` as media storage.
- Do not add runtime daemon execution, streaming, provider marketplace, public reader media delivery, or Web features outside the active v0.4 phase.
- Do not modify `worlds.py` as part of v0.4 Web work.

## Required Next Steps

- Commit `feat/multimodal-diagnostics-dashboard`, fast-forward merge back to local `main`, record Phase 7 merge bookkeeping, and stop v0.4 implementation unless explicitly asked to archive the OpenSpec change.
- Continue to preserve Phase 13 guardrails and do not push unless explicitly requested.

## Latest Verification

- Phase 13 targeted regression and full local gate passed before v0.4 planning began.
- OpenSpec baseline and v0.4-v0.8 roadmap docs were committed.
- Product design context was committed in `PRODUCT.md`.
- v0.4 Phase 1 targeted tests passed: `npm run test -- admin-foundation admin-route-guard api-client provider-admin runtime-admin` (5 files, 13 tests).
- v0.4 Phase 1 full local gate passed: backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`73 passed`), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.4 Phase 2 targeted tests passed: `npm run test -- provider-integrations provider-integration-admin workspace-shell` (2 files, 7 tests), plus web lint/typecheck and `git diff --check`.
- v0.4 Phase 2 full local gate passed: backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`80 passed`), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.4 Phase 3 targeted tests passed: `npm run test -- media-admin media workspace-shell` (2 files, 8 tests), plus web lint/typecheck.
- v0.4 Phase 3 full local gate passed: backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`88 passed`), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.4 Phase 4 targeted tests passed: `npm run test -- visual-admin visual workspace-shell` (3 files, 8 tests), plus web lint/typecheck and `git diff --check`.
- v0.4 Phase 4 full local gate passed: backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`96 passed` after standalone rerun), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.4 Phase 5 targeted tests passed: `npm run test -- speech-admin speech workspace-shell` (3 files, 7 tests), plus web lint/typecheck and `git diff --check`.
- v0.4 Phase 5 full local gate passed: backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`102 passed`), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.4 Phase 6 targeted tests passed: `npm run test -- invocation-ledger invocation workspace-shell` (3 files, 6 tests), plus web lint/typecheck and `git diff --check`.
- v0.4 Phase 6 full local gate passed: backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`107 passed`), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.4 Phase 7 targeted tests passed: `npm run test -- multimodal-diagnostics diagnostics workspace-shell` (3 files, 6 tests), plus web lint/typecheck and `git diff --check`.
- v0.4 Phase 7 full local gate passed: backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`112 passed` after standalone rerun; initial concurrent run with `next build` timed out), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
