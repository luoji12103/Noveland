# Debug Journal

## Entry format

- Date:
- Branch:
- Issue:
- Reproduction:
- Root cause:
- Fix:
- Regression test:
- Remaining risk:

## Initial state

No debug entries yet.

## 2026-04-15 backend namespace package import failure

- Date: 2026-04-15
- Branch: feat/bootstrap-runnable-skeleton
- Issue: `uv run pytest` and `uv run mypy .` could not import `noveland.*` workspace packages.
- Reproduction: Run `uv run pytest` from `backend/` after initial workspace setup.
- Root cause: Hatch member configs packaged `src/noveland/<domain>`, which caused editable installs to add nested namespace paths instead of each member's `src` root.
- Fix: Set each member's Hatch wheel package root to `src/noveland` and add all member `src` roots to `mypy_path`.
- Regression test: `uv run pytest` imports every workspace package; `uv run mypy .` now resolves namespace imports.
- Remaining risk: Future package members must keep the same namespace packaging pattern.

## 2026-04-15 Playwright port collision

- Date: 2026-04-15
- Branch: feat/bootstrap-runnable-skeleton
- Issue: Playwright loaded an unrelated Photogiraffe login page instead of the Noveland app.
- Reproduction: Run `npm run test:e2e` while another service owns `127.0.0.1:3000`.
- Root cause: Playwright reused an existing server on the default Next.js port.
- Fix: Move Playwright web server and base URL to `127.0.0.1:3107`.
- Regression test: `npm run test:e2e` now launches the Noveland app and verifies the dashboard shell.
- Remaining risk: Port `3107` could still collide in rare local environments; choose another unused port if that happens.

## 2026-05-06 V2 phases 1-35 acceptance follow-up bundle

- Date: 2026-05-06
- Branch: main
- Issue: V2 living-world phases 1-35 have implementation baselines and passing targeted checks, but acceptance review found several roadmap-semantics gaps that should be handled together after the remaining V2 phases are completed rather than interrupting the current roadmap flow.
- Reproduction: Review `docs/agent/harness/roadmap-v2-living-world.md` phases 1-35 against current code and run targeted acceptance checks:
  - `cd backend && uv run pytest tests/test_api_worlds.py tests/test_memory_backend.py tests/test_runtime_daemon.py tests/test_replay_snapshot.py tests/test_schema_metadata.py tests/test_alembic_config.py`
  - `cd web && npm run test -- lib/worlds/client.test.ts features/worlds/world-overview.test.tsx features/agents/agent-builder.test.tsx`
- Root cause: Several bundles intentionally implemented deterministic baseline contracts first. Some acceptance signals require deeper cross-service behavior than the initial baseline provides.
- Fix: Deferred. Track as a consolidated post-phases-35 remediation item, preferably after phases 36-50 establish knowledge state, secrets, emotional state, player journal, intervention, GM style, continuity review, authoring, release profile, and beta validation surfaces.
- Regression test: Targeted checks passed during review: backend `64 passed`; Web `3 files / 23 tests passed`.
- Remaining risk:
  - Phase 1: world bible is editable/readable, but runtime and narrative paths do not yet strongly consume bible constraints during generation/review.
  - Phase 6/24: memory write/search/list is worldline scoped, but runtime agent context currently builds memory context against the primary worldline unless a future runtime path carries explicit worldline scope.
  - Phase 15: GM v1 is mostly a deterministic due-offscreen-event resolver, not yet a richer macro situation, daily insert, and plot-pressure engine.
  - Phase 18: `LivingWorldGMService.dry_run_rule` only evaluates a narrow set of conditions; it does not yet inspect the full expected state surface such as time, presence/location, faction progress, and player history.
  - Phase 20: `player.choice_recorded` events are appended only when choice consequences are applied; `apply=false` choice records do not currently append to `world_events`.
  - Phase 23: worldline fork records snapshot/event fork metadata but copies current queryable state rather than reconstructing state as of that snapshot or event sequence.
  - Phase 26: story hooks/promises are queryable via admin/API and copied on fork, but narrative writer/publishing paths do not yet consume unresolved hooks directly.
  - Phase 29: plot trigger dry-run covers open hooks, route affinity, relationship tension, and scene presence, but not the full roadmap matrix of time, faction state, hook state variants, and player choices.
  - Phase 31: daily episode drafts are deterministic/admin-created from candidates, but runtime does not yet automatically create low-risk daily narrative drafts from low-risk event proposals.
  - Phase 32: group interaction contexts exist as worldline-scoped admin state, but the conversation engine has not yet been extended to execute with group context, organization refs, location constraints, and participant roles.

## 2026-05-07 V2 phases 36-50 acceptance quality report

- Date: 2026-05-07
- Branch: main
- Issue: V2 living-world phases 36-50 are implemented and merged into local `main`, but the final acceptance quality needed to be recorded alongside the existing phases 1-35 follow-up record so future hardening can separate accepted baseline behavior from beta-evidence-driven improvements.
- Reproduction: Review `docs/agent/harness/roadmap-v2-living-world.md` phases 36-50 against the completed implementation entries in `docs/agent/harness/change-journal.md` and the final gate recorded for the beta-readiness bundle:
  - `cd backend && uv run ruff check .`
  - `cd backend && uv run mypy .`
  - `cd backend && uv run pytest`
  - `cd web && npm run lint`
  - `cd web && npm run typecheck`
  - `cd web && npm run test`
  - `cd web && npm run build`
  - `cd web && npm run check:next-env`
  - `cd web && npm run test:e2e`
  - `docker compose -f infra/compose.yaml config`
  - `git diff --check`
- Root cause: The last V2 bundles intentionally delivered deterministic baselines, review surfaces, and beta-readiness infrastructure rather than a public production launch. Without a quality report, later work could confuse infrastructure acceptance with narrative-quality or launch-readiness guarantees.
- Fix:
  - Phases 36-45 are accepted as the knowledge/player/guardrails baseline. Evidence includes migration `20260507_0027_living_world_knowledge_player_guardrails.py`, worldline-scoped knowledge facts, secrets/reveals, emotional states, relationship repair records, player journal entries, notifications, interventions, GM style diagnostics, narrative continuity reviews, Web world overview panels, Playwright mock routes, and backend/Web tests.
  - The phases 36-45 bundle also closed the earlier phases 1-35 follow-up gaps that naturally belonged there: `apply=false` choices now log `player.choice_recorded` events, runtime memory context propagates `worldline_id`, unsupported historical forks are rejected instead of silently copying current state, deterministic dry-runs inspect a broader context surface, rumor delivery updates knowledge state, low-risk resolved offscreen events can create daily episode drafts, and conversation writer config can carry group interaction context.
  - Phases 46-50 are accepted as beta-release-readiness infrastructure. Evidence includes migration `20260507_0028_living_world_beta_release_readiness.py`, route milestones, ending candidates, deterministic ending dry-runs, long-run eval runs with blockers/recommendations, sequel-world authoring templates and import jobs, release profile records, beta checklist runs/items, operator docs at `docs/agent/operations/living-world-release-profile.md`, Web beta-readiness panels, Playwright mock routes, and backend/Web tests.
- Regression test: The beta-readiness final gate passed after `web/next-env.d.ts` build/e2e churn was restored and `npm run check:next-env` was rerun. Current acceptance logging is docs-only and should be protected with `git diff --check`.
- Remaining risk:
  - Phases 36-37: knowledge and secret handling provide worldline-scoped visibility/reveal state, but real narrative leak prevention still depends on future beta evidence, prompt usage, and publication review tuning.
  - Phases 38-39: emotional state and relationship repair are deterministic rule baselines; calibration against authored worlds and long-run play traces remains future work.
  - Phases 40-45: dashboard, journal, notification, intervention, style, and continuity surfaces are operational baselines. GM style and continuity reviews warn/report by default and are not hard publication blockers unless a future policy explicitly promotes them.
  - Phases 46-50: route/ending planning, long-run eval, authoring templates, release profiles, and beta checklists capture readiness evidence; they do not constitute a public production launch or guarantee narrative quality.
  - Persistent databases must apply migrations `20260507_0027` and `20260507_0028` before using the final V2 data surfaces.
  - The 50-phase V2 roadmap has no remaining phase-number work. Future work should come from beta evidence, operator feedback, and targeted hardening rather than new phase-number branches.
