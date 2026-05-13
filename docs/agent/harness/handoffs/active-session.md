# Active Session Handoff

- Date: 2026-05-13T00:00:00Z
- Branch: main
- Objective: Continue v0.4 Operator/Admin UX after Phase 1 Admin UX Foundation.
- Status: Phase 1 implementation is fast-forward merged to local `main`. Phase 2 Provider Admin Console is next.

## Current Context

- Phase 3-13 backend architecture is complete and frozen through architecture docs, API/data inventories, ADRs, and the multimodal sample-world regression fixture.
- OpenSpec current specs live under `openspec/specs/`.
- v0.4 implementation source of truth is `openspec/changes/v0-4-operator-admin-ux/`.
- v0.4 phases must run in order: Admin UX Foundation, Provider Admin Console, Media Asset Admin Console, Visual Asset Admin Console, Speech Admin Console, Invocation Ledger Browser, Multimodal Diagnostics Dashboard.
- `PRODUCT.md` defines the frontend product context: product register, calm/rigorous/operator-grade personality, no marketing SaaS or gamey admin UI, WCAG AA, keyboard-first, reduced-motion friendly, and color not as sole signal.
- Phase 1 added reusable admin foundation components, platform-admin route guard helper, and CSRF-aware admin request helper. Later phases should reuse these patterns instead of inventing page-local equivalents.
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

- Confirm `main` is clean.
- Start v0.4 Phase 2 Provider Admin Console from clean local `main` only if no blocker appears.
- Continue to preserve Phase 13 guardrails and do not push unless explicitly requested.

## Latest Verification

- Phase 13 targeted regression and full local gate passed before v0.4 planning began.
- OpenSpec baseline and v0.4-v0.8 roadmap docs were committed.
- Product design context was committed in `PRODUCT.md`.
- v0.4 Phase 1 targeted tests passed: `npm run test -- admin-foundation admin-route-guard api-client provider-admin runtime-admin` (5 files, 13 tests).
- v0.4 Phase 1 full local gate passed: backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), web lint, web typecheck, web tests (`73 passed`), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
