# Active Session Handoff

- Date: 2026-05-12T00:00:00Z
- Branch: main
- Objective: Begin Phase 8 Real Provider Configuration & Smoke Validation.
- Status: Phase 8 planning checkpoint is being recorded on `main`; implementation should continue on `feat/real-provider-smoke-validation` after the docs-only commit.

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

## Required Next Steps

- Commit Phase 8 docs-only plan on `main`.
- Create `feat/real-provider-smoke-validation`.
- Implement provider secret resolver, recursive secret-key rejection/sanitization, safe provider health/smoke-test APIs, and ledger snapshot sanitization.
- Run targeted Phase 8 tests and the full local gate before fast-forward merging back to `main`.
- Do not push unless explicitly requested.

## Verification Completed

- Targeted Phase 7 backend tests passed.
- Backend `ruff`, `mypy`, and full `pytest` passed.
- Web lint, typecheck, test, build, `check:next-env`, and e2e passed.
- `docker compose -f infra/compose.yaml config` passed.
- `git diff --check` passed.
- Note: `tests/e2e/auth.spec.ts` release gate blocker test failed once during the interrupted run, then passed both as a single-test rerun and in the full e2e run.
