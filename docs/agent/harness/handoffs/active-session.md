# Active Session Handoff

- Date: 2026-05-11T00:00:00Z
- Branch: main
- Objective: Start Phase 7 Speech Provider & Voice Profile Pipeline after completed Phase 6 Image Provider & Visual Asset Pipeline.
- Status: Phase 7 planning checkpoint prepared; implementation should start on `feat/speech-provider-voice-profile-pipeline` after the docs-only commit.

## Current Context

- Phase 3 Model Invocation Ledger is complete with `model_invocations`, `prompt_snapshots`, prompt templates, invocation tags, and runtime-run invocation links.
- Phase 4 Media Kernel is complete with media objects, generic references, upload/download flows, media job updates, and invocation links.
- Phase 5 Provider Execution Kernel is complete with `noveland-providers`, provider integrations, capabilities, health checks, fake execution, invocation ledger writes, and media writeback.
- Phase 6 Image Provider & Visual Asset Pipeline is complete with image generation/edit/compose services, OpenAI/OpenAI-compatible image adapters, ComfyUI adapter contract, deterministic composition, and an independent `/worlds/{world_id}/images` API router.
- The next phase must add speech contracts/services, voice profile persistence, speech provider adapters, transcript writeback, and an independent `/worlds/{world_id}/speech` API router.
- `provider_profiles` remains the legacy LLM provider profile table and must not become the universal provider registry.
- `provider_integrations.adapter_kind` is required from the first Phase 5 migration so execution routing does not depend on `provider_key` naming or hidden `config_json` conventions.
- Provider-backed image calls must write Phase 3 invocation ledger records and Phase 4 media records.
- Storage URIs, file paths, bytes, base64, raw prompts, and raw outputs must stay out of `world_events.payload`.

## Required Next Steps

- Commit the Phase 7 docs-only planning checkpoint on `main`.
- Create `feat/speech-provider-voice-profile-pipeline`.
- Implement speech contracts/models/services, provider speech adapters, speech API router, workspace dependencies, docs updates, and tests.
- Run targeted Phase 7 tests plus the full local gate.
- Fast-forward merge locally back to `main`.
- Do not push unless explicitly requested.
