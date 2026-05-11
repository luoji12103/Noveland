# Active Session Handoff

- Date: 2026-05-11T00:00:00Z
- Branch: feat/provider-execution-kernel
- Objective: Complete Phase 5 Provider Execution Kernel and merge locally back to `main`.
- Status: Implementation complete on feature branch; targeted Phase 5 tests, backend ruff, and backend mypy pass. Full local gate and fast-forward merge remain before Phase 6 can start.

## Current Context

- Phase 3 Model Invocation Ledger is complete with `model_invocations`, `prompt_snapshots`, prompt templates, invocation tags, and runtime-run invocation links.
- Phase 4 Media Kernel is complete with media objects, generic references, upload/download flows, media job updates, and invocation links.
- The phase adds a separate `noveland-providers` package and independent `/worlds/{world_id}/providers` API router.
- `provider_profiles` remains the legacy LLM provider profile table and must not become the universal provider registry.
- `provider_integrations.adapter_kind` is required from the first Phase 5 migration so execution routing does not depend on `provider_key` naming or hidden `config_json` conventions.
- Provider calls must write Phase 3 invocation ledger records and media-producing fake executions must write Phase 4 media records.
- Storage URIs, file paths, bytes, base64, raw prompts, and raw outputs must stay out of `world_events.payload`.

## Required Next Steps

- Run the remaining Phase 5 full local gate.
- Commit the Phase 5 implementation on `feat/provider-execution-kernel`.
- Fast-forward merge locally back to `main`.
- Do not start Phase 6 until Phase 5 is merged cleanly and the full gate passes.
- Do not push unless explicitly requested.
