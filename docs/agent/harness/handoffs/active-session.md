# Active Session Handoff

- Date: 2026-05-13T00:00:00Z
- Branch: main
- Objective: Implement v0.4 Operator/Admin UX, starting with Phase 1 Admin UX Foundation.
- Status: Phase 13 is complete. OpenSpec baseline and v0.4-v0.8 roadmap skeleton are committed. v0.4 Phase 1 planning checkpoint is in progress on `main`.

## Current Context

- Phase 3-13 backend architecture is complete and frozen through architecture docs, API/data inventories, ADRs, and the multimodal sample-world regression fixture.
- OpenSpec current specs live under `openspec/specs/`.
- v0.4 implementation source of truth is `openspec/changes/v0-4-operator-admin-ux/`.
- v0.4 phases must run in order: Admin UX Foundation, Provider Admin Console, Media Asset Admin Console, Visual Asset Admin Console, Speech Admin Console, Invocation Ledger Browser, Multimodal Diagnostics Dashboard.
- `PRODUCT.md` defines the frontend product context: product register, calm/rigorous/operator-grade personality, no marketing SaaS or gamey admin UI, WCAG AA, keyboard-first, reduced-motion friendly, and color not as sole signal.
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

- Commit the v0.4.1 docs-only planning checkpoint on `main`.
- Create `feat/admin-ux-foundation`.
- Implement shared admin UI foundation only.
- Run targeted Web tests and the full local gate.
- Fast-forward merge to local `main`, update OpenSpec tasks and harness docs, then continue to v0.4 Phase 2 only if all gates pass.

## Latest Verification

- Phase 13 targeted regression and full local gate passed before v0.4 planning began.
- OpenSpec baseline and v0.4-v0.8 roadmap docs were committed.
- Product design context was committed in `PRODUCT.md`.
