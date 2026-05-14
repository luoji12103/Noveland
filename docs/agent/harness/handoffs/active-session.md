# Active Session Handoff

- Date: 2026-05-14T00:00:00Z
- Branch: main
- Objective: Continue v0.5 Authoring & Import Studio with Phase 3 Character & Relationship Extractor.
- Status: v0.5 Phase 2 Script Parser & Dialogue Extractor is implemented, validated, and fast-forward merged locally.

## Current Context

- `main` is ahead of `origin/main` locally; do not push unless explicitly requested.
- Phase 3-13 backend architecture is complete and frozen through architecture docs, API/data inventories, ADRs, and the multimodal sample-world regression fixture.
- v0.4 Operator/Admin UX is complete across all seven phases: Admin UX Foundation, Provider Admin Console, Media Asset Admin Console, Visual Asset Admin Console, Speech Admin Console, Invocation Ledger Browser, and Multimodal Diagnostics Dashboard.
- Current implemented behavior is represented under `openspec/specs/`.
- The completed v0.4 change is archived under `openspec/changes/archive/2026-05-14-v0-4-operator-admin-ux/`.
- v0.4 release notes live at `docs/agent/harness/release-notes/v0.4-operator-admin-ux.md`.
- v0.5 must use `backend/packages/authoring/` and `backend/services/api/src/noveland/services/api/authoring.py` for new authoring/import work.
- v0.5 Phase 1 is complete: source registry plus import run/proposal/review decision/source traceability/preview/apply foundation.
- v0.5 Phase 2 is complete: deterministic parser creates traceable proposals for dialogue, unresolved quoted dialogue, scenes, choices, routes, and events without provider calls or canonical mutation.
- v0.5 Phase 3 is next: Character & Relationship Extractor.
- Existing `authoring_templates`, `authoring_import_jobs`, and world composition import are legacy-compatible inputs or references, not the primary v0.5 foundation.
- v0.5 lore/world-bible extraction is proposal-only until a later accepted architecture decision defines safe global-vs-worldline canon apply behavior.
- `PRODUCT.md` defines the frontend product context: product register, calm/rigorous/operator-grade personality, no marketing SaaS or gamey admin UI, WCAG AA, keyboard-first, reduced-motion friendly, and color not as sole signal.
- `.opencode/` is ignored and must not be committed.
- Do not push unless explicitly requested.

## Guardrails To Preserve

- Do not expose resolved provider secrets.
- Do not expose storage URIs, filesystem paths, bytes, base64, raw prompts, or raw outputs in event payloads or reader/member routes.
- Do not bypass backend ACLs or validation from Web code.
- Do not use `narrative_artifacts` as media storage.
- Do not add runtime daemon execution, streaming, provider marketplace, public reader media delivery, or Web features outside an accepted change.
- Do not modify `worlds.py` for broad route growth unless explicitly accepted.

## Required Next Steps

- Start Phase 3 from clean local `main` with a docs-only planning checkpoint.
- Phase 3 should implement only `character-relationship-extractor` scope and reuse Phase 1 import proposals.
- Do not add new v0.5 routes to `worlds.py`; keep using the independent authoring router.
- Do not push unless explicitly requested.

## Latest Verification

- v0.4 Phase 7 full local gate passed before archive: backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed` after standalone rerun; initial concurrent run with `next build` timed out), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.4 archive/release-notes work is docs-only and should be validated with OpenSpec validation plus `git diff --check`.
- v0.5 architecture decision docs are docs-only and should be validated with OpenSpec validation plus `git diff --check`.
- v0.5 Phase 1 targeted tests passed: `32 passed`.
- v0.5 Phase 1 full local gate passed: backend ruff, backend mypy, backend pytest (`298 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.5 Phase 2 targeted tests passed: `10 passed`.
- v0.5 Phase 2 full local gate passed: backend ruff, backend mypy, backend pytest (`300 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, `git diff --check`, and OpenSpec strict validate.
