# Active Session Handoff

- Date: 2026-05-15T00:00:00Z
- Branch: main
- Objective: v0.7 Production Hardening Phase 4.
- Status: Phase 3 Cost & Rate Control is fast-forward merged to local `main`; Phase 4 Object Storage & Backup v2 planning checkpoint is next.

## Current Context

- `main` is ahead of `origin/main` after local v0.6 work; do not push unless explicitly requested.
- Phase 3-13 backend architecture is complete and frozen through architecture docs, API/data inventories, ADRs, and the multimodal sample-world regression fixture.
- v0.4 Operator/Admin UX is complete across all seven phases: Admin UX Foundation, Provider Admin Console, Media Asset Admin Console, Visual Asset Admin Console, Speech Admin Console, Invocation Ledger Browser, and Multimodal Diagnostics Dashboard.
- Current Phase 3-13, v0.4, and v0.5 implemented behavior is represented under `openspec/specs/`.
- The completed v0.4 change is archived under `openspec/changes/archive/2026-05-14-v0-4-operator-admin-ux/`.
- The completed v0.5 change is archived under `openspec/changes/archive/2026-05-15-v0-5-authoring-import-studio/`.
- v0.4 release notes live at `docs/agent/harness/release-notes/v0.4-operator-admin-ux.md`.
- v0.5 release notes live at `docs/agent/harness/release-notes/v0.5-authoring-import-studio.md`.
- v0.5 must use `backend/packages/authoring/` and `backend/services/api/src/noveland/services/api/authoring.py` for new authoring/import work.
- v0.5 Phase 1 is complete: source registry plus import run/proposal/review decision/source traceability/preview/apply foundation.
- v0.5 Phase 2 is complete: deterministic parser creates traceable proposals for dialogue, unresolved quoted dialogue, scenes, choices, routes, and events without provider calls or canonical mutation.
- v0.5 Phase 3 is complete: deterministic extractor creates traceable proposals for characters, aliases, factions, identities, relationships, and emotional baselines without provider calls or canonical mutation.
- v0.5 Phase 4 is complete: deterministic lore extractor creates proposal-only lore, location, organization, world-rule, secret, and knowledge-boundary candidates without provider calls or canonical mutation.
- v0.5 Phase 5 is complete: deterministic conflict review creates reviewable conflict report proposals without provider calls, automatic resolution, or canonical mutation.
- v0.5 Phase 6 is complete: deterministic memory migration creates reviewable fact, episodic, relationship, preference, and style memory proposals without provider calls, memory writes, or canonical mutation.
- v0.5 Phase 7 is complete: deterministic asset matching creates reviewable sprite, background, CG, and voice-reference proposals without provider calls, media jobs, visual/speech binding writes, or canonical mutation.
- v0.5 Phase 8 is complete: deterministic authoring regression fixture covers source registry, parser, character/lore extraction, conflict review, memory migration, asset matching, guarded review/apply, and side-effect leak checks.
- Existing `authoring_templates`, `authoring_import_jobs`, and world composition import are legacy-compatible inputs or references, not the primary v0.5 foundation.
- v0.5 lore/world-bible extraction is proposal-only until a later accepted architecture decision defines safe global-vs-worldline canon apply behavior.
- v0.6 Runtime Narrative Quality is complete locally and ready to archive if requested; this session does not archive it.
- v0.7 Production Hardening is the next proposed OpenSpec change and should start API/test/docs-first.
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

- Keep `main` clean and do not push unless explicitly requested.
- If requested, archive v0.6 and generate v0.6 release notes before v0.7 implementation starts.
- If implementation is requested, continue v0.7 with Phase 2 Secret & Provider Governance from clean local `main`.
- Stop for an architecture decision if v0.7 needs broad new `worlds.py` routes or a cross-cutting production-hardening package/router.

## Latest Verification

- v0.4 Phase 7 full local gate passed before archive: backend ruff, backend mypy, backend pytest (`293 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed` after standalone rerun; initial concurrent run with `next build` timed out), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.4 archive/release-notes work is docs-only and should be validated with OpenSpec validation plus `git diff --check`.
- v0.5 architecture decision docs are docs-only and should be validated with OpenSpec validation plus `git diff --check`.
- v0.5 Phase 1 targeted tests passed: `32 passed`.
- v0.5 Phase 1 full local gate passed: backend ruff, backend mypy, backend pytest (`298 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.5 Phase 2 targeted tests passed: `10 passed`.
- v0.5 Phase 2 full local gate passed: backend ruff, backend mypy, backend pytest (`300 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, `git diff --check`, and OpenSpec strict validate.
- v0.5 Phase 3 planning checkpoint is docs-only and validated with OpenSpec strict validate plus `git diff --check`.
- v0.5 Phase 3 targeted tests passed: `12 passed`.
- v0.5 Phase 3 full local gate passed: backend ruff, backend mypy, backend pytest (`302 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, `git diff --check`, and OpenSpec strict validate.
- v0.5 Phase 4 planning checkpoint is docs-only and validated with OpenSpec strict validate plus `git diff --check`.
- v0.5 Phase 4 targeted tests passed: `14 passed`.
- v0.5 Phase 4 full local gate passed: backend ruff, backend mypy, backend pytest (`304 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, `git diff --check`, and OpenSpec strict validate.
- v0.5 Phase 5 planning checkpoint is docs-only and validated with OpenSpec strict validate plus `git diff --check`.
- v0.5 Phase 5 targeted tests passed: `16 passed`.
- v0.5 Phase 5 full local gate passed: backend ruff, backend mypy, backend pytest (`306 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, `git diff --check`, and OpenSpec strict validate.
- v0.5 Phase 6 planning checkpoint is docs-only and validated with OpenSpec strict validate plus `git diff --check`.
- v0.5 Phase 6 targeted tests passed: `18 passed`.
- v0.5 Phase 6 full local gate passed: backend ruff, backend mypy, backend pytest (`308 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`35 passed`, `112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed` after rerun; initial attempt timed out at the conversations e2e scene), docker compose config, `git diff --check`, and OpenSpec strict validate.
- v0.5 Phase 6 fast-forward merge to local `main` completed.
- v0.5 Phase 7 planning checkpoint is docs-only and should be validated with OpenSpec strict validate plus `git diff --check`.
- v0.5 Phase 7 targeted tests passed: `21 passed`.
- v0.5 Phase 7 full local gate passed: backend ruff, backend mypy, backend pytest (`311 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`35 passed`, `112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, `git diff --check`, and OpenSpec strict validate.
- v0.5 Phase 7 fast-forward merge to local `main` completed.
- v0.5 Phase 8 planning checkpoint is docs-only and should be validated with OpenSpec strict validate plus `git diff --check`.
- v0.5 Phase 8 targeted tests passed: `25 passed`.
- v0.5 Phase 8 full local gate passed: backend ruff, backend mypy, backend pytest (`315 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`35 passed`, `112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, `git diff --check`, and OpenSpec strict validate.
- v0.5 Phase 8 fast-forward merge to local `main` completed.
- v0.6 Phase 1 targeted checks passed: backend ruff for narrative quality files, backend mypy for narrative quality/API/tests, targeted pytest (`10 passed`), OpenSpec strict changes/spec validation, and `git diff --check`.
- v0.6 Phase 1 full local gate passed: backend ruff, backend mypy (`246 source files`), backend pytest (`321 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.6 Phase 1 fast-forward merge to local `main` completed.
- v0.6 Phase 2 planning checkpoint is docs-only and should be validated with OpenSpec strict validation plus `git diff --check`.
- v0.6 Phase 2 targeted checks passed: backend ruff for narrative quality files, backend mypy for narrative quality/API/tests, targeted pytest (`21 passed`), OpenSpec strict changes/spec validation, and `git diff --check`.
- v0.6 Phase 2 full local gate passed: backend ruff, backend mypy (`246 source files`), backend pytest (`327 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.6 Phase 2 fast-forward merge to local `main` completed.
- v0.6 Phase 3 planning checkpoint is docs-only and should be validated with OpenSpec strict validation plus `git diff --check`.
- v0.6 Phase 3 targeted checks passed: backend ruff for narrative quality files, backend mypy for narrative quality/API/tests, targeted pytest (`21 passed`), OpenSpec strict changes/spec validation, and `git diff --check`.
- v0.6 Phase 3 full local gate passed: backend ruff, backend mypy (`246 source files`), backend pytest (`332 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed` after rerun), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Flaky note: The first full Web test run had one isolated `agent-builder.test.tsx` mock-call failure; the individual test passed immediately afterward, and the full Web test/build/e2e sequence passed on rerun.
- v0.6 Phase 3 fast-forward merge to local `main` completed.
- v0.6 Phase 4 planning checkpoint is docs-only and should be validated with OpenSpec strict validation plus `git diff --check`.
- v0.6 Phase 4 targeted checks passed: backend ruff for narrative quality files, backend mypy for narrative quality/API/tests, targeted pytest (`27 passed`), OpenSpec strict changes/spec validation, and `git diff --check`.
- v0.6 Phase 4 full local gate passed: backend ruff, backend mypy (`246 source files`), backend pytest (`338 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.6 Phase 4 fast-forward merge to local `main` completed.
- v0.6 Phase 5 targeted checks passed: backend ruff for narrative quality/narrative/API/tests, backend mypy for narrative quality/narrative/API/tests, targeted pytest (`70 passed`), OpenSpec strict changes/spec validation, and `git diff --check`.
- v0.6 Phase 5 full local gate passed: backend ruff, backend mypy (`246 source files`), backend pytest (`347 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.6 Phase 5 fast-forward merge to local `main` completed.
- v0.6 Phase 6 targeted checks passed: backend ruff for narrative quality/API/tests, backend mypy for narrative quality/API/tests, targeted pytest (`43 passed`), OpenSpec strict changes/spec validation, and `git diff --check`.
- v0.6 Phase 6 full local gate passed: backend ruff, backend mypy (`246 source files`), backend pytest (`358 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.6 Phase 6 fast-forward merge to local `main` completed.
- v0.6 Phase 7 planning checkpoint is docs-only and validated with OpenSpec strict validation plus `git diff --check`.
- v0.6 Phase 7 targeted checks passed: backend ruff for narrative quality/API/tests, backend mypy for narrative quality/API/tests, targeted pytest (`50 passed`), OpenSpec strict changes/spec validation, and `git diff --check`.
- v0.6 Phase 7 full local gate passed: backend ruff, backend mypy (`246 source files`), backend pytest (`365 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed` after rerun; first attempt hit an existing world composition import/export response-body race), docker compose config, and `git diff --check`.
- v0.6 Phase 7 fast-forward merge to local `main` completed.
- v0.6 Phase 8 planning checkpoint is docs-only and should be validated with OpenSpec strict validation plus `git diff --check`.
- v0.6 Phase 8 targeted checks passed: backend ruff for narrative quality/API/tests, backend mypy for narrative quality/API/tests, targeted pytest (`56 passed`), OpenSpec strict changes/spec validation, and `git diff --check`.
- v0.6 Phase 8 full local gate passed: backend ruff, backend mypy (`246 source files`), backend pytest (`371 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.6 Phase 8 fast-forward merge to local `main` completed.
- v0.6 Phase 9 planning checkpoint is docs-only and was validated with OpenSpec strict validation plus `git diff --check`.
- v0.6 Phase 9 targeted checks passed: backend ruff for narrative quality/API/tests, backend mypy for narrative quality/API/tests, targeted pytest (`63 passed`), OpenSpec strict changes/spec validation, and `git diff --check`.
- v0.6 Phase 9 full local gate passed: backend ruff, backend mypy (`246 source files`), backend pytest (`378 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed` after rerun; first attempt hit the existing world composition import/export response-body race), docker compose config, and `git diff --check`.
- v0.6 Phase 9 fast-forward merge to local `main` completed.
- v0.6 Phase 10 implementation added a read-only admin-scoped dashboard summary API under the narrative quality router.
- v0.6 Phase 10 targeted checks passed: backend ruff for narrative quality/API/tests, backend mypy for narrative quality/API/tests, targeted pytest (`68 passed`), OpenSpec strict changes/spec validation, and `git diff --check`.
- v0.6 Phase 10 full local gate passed: backend ruff, backend mypy (`246 source files`), backend pytest (`383 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed` after rerun), docker compose config, and `git diff --check`.
- Flaky note: the first Web e2e run hit the existing world composition import/export response-body race; the rerun completed cleanly.
- v0.6 Phase 10 fast-forward merge to local `main` completed.
- v0.7 Production Hardening feasibility review optimized the OpenSpec proposal/design/phase-plan/tasks/specs after v0.6 completion.
- v0.7 revised first implementation target is Phase 1 Permission Matrix & ACL Regression Baseline.
- v0.7 Phase 1 planning checkpoint added `docs/agent/harness/feature-updates/v0.7.1-permission-matrix-acl-regression-plan.md`.
- v0.7 Phase 1 targeted checks passed: backend ruff for `test_api_permission_matrix.py`, backend mypy for `test_api_permission_matrix.py`, targeted pytest (`3 passed`), OpenSpec strict changes/spec validation, and `git diff --check`.
- v0.7 Phase 1 full local gate passed: backend ruff, backend mypy (`247 source files`), backend pytest (`386 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.7 Phase 1 fast-forward merge to local `main` completed.
- v0.7 Phase 2 planning checkpoint added `docs/agent/harness/feature-updates/v0.7.2-secret-provider-governance-plan.md`.
- v0.7 Phase 2 targeted checks passed: backend ruff for provider governance code/tests, backend mypy for provider governance code/tests, targeted pytest (`70 passed`), OpenSpec strict changes/spec validation, and `git diff --check`.
- v0.7 Phase 2 full local gate passed: backend ruff, backend mypy (`247 source files`), backend pytest (`391 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed`), docker compose config, and `git diff --check`.
- v0.7 Phase 2 fast-forward merge to local `main` completed.
- v0.7 Phase 3 planning checkpoint added `docs/agent/harness/feature-updates/v0.7.3-cost-rate-control-plan.md`.
- v0.7 Phase 3 targeted checks passed: backend ruff for provider budget code/tests, backend mypy for provider budget code/tests, targeted pytest (`109 passed`), and `git diff --check`.
- v0.7 Phase 3 full local gate passed: backend ruff, backend mypy (`248 source files`), backend pytest (`397 passed, 7 skipped`), Web lint, Web typecheck, Web tests (`112 passed`), Web build, Web `check:next-env`, Web e2e (`13 passed` after stabilizing an existing import/export response-body race), docker compose config, and `git diff --check`.
- Flaky note: one e2e run hit a transient unauthenticated reader redirect 404 during Next dev dynamic route cold start; the isolated test and the subsequent full e2e run passed.
- v0.7 Phase 3 fast-forward merge to local `main` completed.
