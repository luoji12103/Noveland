# Active Session Handoff

- Date: 2026-05-13T00:00:00Z
- Branch: main
- Objective: Begin Phase 13 Architecture Freeze & Regression Fixture.
- Status: Phase 8-12 are complete and fast-forward merged to `main`; Phase 13 planning checkpoint is being recorded on `main`; implementation should continue on `feat/architecture-freeze-regression-fixture` after the docs-only commit.

## Current Context

- Phase 3 Model Invocation Ledger is complete with `model_invocations`, `prompt_snapshots`, prompt templates, invocation tags, and runtime-run invocation links.
- Phase 4 Media Kernel is complete with media objects, generic references, upload/download flows, media job updates, and invocation links.
- Phase 5 Provider Execution Kernel is complete with `noveland-providers`, provider integrations, capabilities, health checks, fake execution, invocation ledger writes, and media writeback.
- Phase 6 Image Provider & Visual Asset Pipeline is complete with image generation/edit/compose services, OpenAI/OpenAI-compatible image adapters, ComfyUI adapter contract, deterministic composition, and an independent `/worlds/{world_id}/images` API router.
- Phase 7 adds speech contracts/services, voice profile persistence, speech provider adapters, transcript writeback, and an independent `/worlds/{world_id}/speech` API router.
- `provider_profiles` remains the legacy LLM provider profile table and must not become the universal provider registry.
- `provider_integrations.adapter_kind` is required from the first Phase 5 migration so execution routing does not depend on `provider_key` naming or hidden `config_json` conventions.
- Provider-backed image and speech calls must write Phase 3 invocation ledger records and Phase 4 media records.
- Storage URIs, file paths, bytes, base64, raw prompts, and raw outputs must stay out of `world_events.payload`.
- Phase 8 decision: `provider_integrations.auth_ref` is an opaque secret reference, not a secret value. Provider config/default params must reject secret-like keys and execution must resolve real secrets only in memory from environment/settings.
- Phase 9 decision: visual binding records are strict-worldline-only. Sprite/background records must have non-null `worldline_id`; media bytes may be shared through media assets, but visual binding state must not use nullable worldline defaults.
- Phase 10 decision: conversation turn presentation is backend/API-only, one canonical record per turn, and must reuse visual/image/speech/media services without mutating turn text or auto-writing STT transcripts to memory.
- Phase 11 decision: asset generation is proposal plus admin apply only. Preview/apply must not call providers, must not hook a daemon, and must create only queued `media_jobs` for explicit later execution.
- Phase 12 decision: multimodal evaluation reuses existing `long_run_eval_runs` and release/eval evidence patterns. Do not create a duplicate release framework or a new eval table unless implementation proves the existing table insufficient.
- Phase 13 is a freeze/regression phase only. Do not add new product features, providers, Web UI, public reader media delivery, runtime daemon execution, streaming, release gate semantic changes, schema normalization, historical backfill, or `worlds.py` refactors.

## Required Next Steps

- Commit Phase 13 docs-only plan on `main`.
- Create `feat/architecture-freeze-regression-fixture`.
- Add architecture contract docs, API/data inventories, ADRs, fixture docs, a deterministic multimodal sample-world test fixture, and a regression test entrypoint.
- Run targeted Phase 13 tests and the full local gate before fast-forward merging back to `main`.
- Do not push unless explicitly requested.

## Verification Completed

- Targeted Phase 7 backend tests passed.
- Backend `ruff`, `mypy`, and full `pytest` passed.
- Web lint, typecheck, test, build, `check:next-env`, and e2e passed.
- `docker compose -f infra/compose.yaml config` passed.
- `git diff --check` passed.
- Note: `tests/e2e/auth.spec.ts` release gate blocker test failed once during the interrupted run, then passed both as a single-test rerun and in the full e2e run.
- Phase 8 targeted tests passed: 53 passed.
- Phase 8 final backend full pytest passed: 266 passed, 7 skipped.
- Phase 8 full local gate passed: backend ruff, backend mypy, backend pytest, web lint, web typecheck, web tests, web build, web `check:next-env`, web e2e, docker compose config, and `git diff --check`.
- Phase 9 targeted tests passed: 34 passed.
- Phase 9 full local gate passed: backend ruff, backend mypy, backend pytest, web lint, web typecheck, web tests, web build, web `check:next-env`, web e2e, docker compose config, `git diff --check`, and clean next-env check.
- Phase 10 targeted tests passed: 30 passed.
- Phase 10 full local gate passed: backend ruff, backend mypy, backend pytest, web lint, web typecheck, web tests, web build, web `check:next-env`, web e2e, docker compose config, and `git diff --check`.
- Phase 11 targeted tests passed: 32 passed.
- Phase 11 full local gate passed: backend ruff, backend mypy, backend pytest (`284 passed, 7 skipped`), web lint, web typecheck, web tests (`63 passed`), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
- Phase 12 targeted tests passed: 31 passed.
- Phase 12 full local gate passed: backend ruff, backend mypy, backend pytest (`288 passed, 7 skipped`), web lint, web typecheck, web tests (`63 passed`), web build, web `check:next-env`, web e2e (`13 passed`), docker compose config, and `git diff --check`.
