# Current System Contracts

This document freezes the backend contracts after Phase 3-12. Future work may extend these layers, but must not bypass their ownership boundaries.

## Worldline Isolation Contract

- `world_id` and `worldline_id` are first-class parameters for stateful world data.
- Worldline-scoped records must validate same world and same worldline before linking records.
- Visual bindings, media assets, media objects, media jobs, conversation presentations, speech transcripts, asset generation records, and model invocations are worldline-scoped.
- Nullable `worldline_id` is not allowed for Phase 9 visual binding records.
- Cross-worldline inheritance is deferred; do not simulate it with nullable defaults.

## Provider Execution Boundary

- Provider adapters are owned by `noveland.providers`.
- Product modules must not call OpenAI, OpenAI-compatible, ComfyUI, MiMo, OmniVoice, GPT-SoVITS, or custom HTTP adapters directly.
- Provider execution routes through `ProviderExecutionService`.
- Execution dispatch uses `adapter_kind`, not `provider_key` naming or hidden `config_json` conventions.
- Provider-backed image and speech services must route through provider execution so the ledger and media writeback paths stay uniform.

## Secret Boundary

- `provider_integrations.auth_ref` is an opaque reference such as `env:OPENAI_API_KEY`; it is not a secret value.
- Actual secret values are resolved in memory through `ProviderSecretResolver`.
- Secret-like keys in provider config/default params are rejected or redacted before persistence.
- Secrets must not be written to provider configs, health metadata, media jobs, model invocations, prompt snapshots, logs, diagnostics, or API responses.
- Admin APIs may expose `auth_ref` as a reference identifier only, never the resolved value.

## Invocation Ledger Boundary

- Every model/provider call must create a `model_invocations` row.
- Every model/provider call must have a `prompt_snapshots` row or explicit redaction evidence.
- Prompt snapshots are admin/developer evidence, not reader/member content.
- Raw prompts and raw outputs must not be copied into `world_events.payload`.
- Invocation records can link to media jobs/assets, conversation turns, agents, and memory jobs through explicit IDs.

## Media Kernel Boundary

- Binary outputs and uploaded media are represented by `media_assets`, `media_objects`, `media_jobs`, and `media_references`.
- `media://` storage URIs are internal storage references; regular API responses should use safe DTOs or download routes.
- `narrative_artifacts` are prose/publication records and must not be used as media storage.
- Media jobs describe planned or completed work; provider execution is still explicit and audited.
- `world_events.payload` must never contain storage URI, file path, bytes, base64, raw prompt, or raw output fields.

## Visual Asset Boundary

- Visual records live in `noveland.visual`.
- Sprite sets, sprite variants, and scene background profiles point to existing `media_assets`.
- Visual bindings are strict-worldline records with non-null `worldline_id`.
- Sprite resolution is deterministic: exact match, neutral fallback, default fallback, then actionable error.
- Scene composition reuses the Phase 6 image composer through image/visual services; do not add a second composer.

## Conversation Turn Presentation Boundary

- `conversation_turn_presentations` is the canonical backend record for turn presentation state.
- It may reference sprite/background/composite/voice/TTS/transcript records by ID.
- Rendering visual or speech assets must attach media through `media_references`.
- STT may create a transcript and presentation reference, but must not mutate `conversation_turns.input_text` or `output_text`.
- STT must not automatically enqueue memory writes.
- Phase 10 is API-only; Web preview/playback is deferred.

## Speech And Voice Boundary

- Voice profiles, agent voice bindings, speech transcripts, and style mappings are owned by `noveland.speech`.
- TTS/STT provider calls go through the provider execution layer.
- TTS output audio is media, not turn text.
- STT transcript text is a transcript record, not automatic memory or direct turn mutation.
- Voice cloning is metadata/reference-only unless a later explicit phase adds a provider-backed training flow.

## Asset Generation Boundary

- Asset generation is proposal plus admin apply.
- Preview creates proposal records only; it must not call providers.
- Apply creates queued `media_jobs`; it must not execute providers or start daemon work.
- Runtime daemon auto-generation and hidden background spend are deferred.
- Media job priority, invalidation, and cancellation helpers operate on existing jobs and respect terminal states.

## Multimodal Eval Boundary

- Multimodal evals reuse `long_run_eval_runs` with multimodal eval keys.
- Diagnostics inspect existing provider, invocation, media, visual, speech, presentation, asset generation, and event records.
- Diagnostics may report blockers/warnings/recommendations, but must not create a parallel release framework.
- Evidence references must be table/id style references and must not expose storage URIs or raw prompts/outputs.

## World Event Payload Prohibitions

Never write these to `world_events.payload`:

- `storage_uri`, `preview_uri`, `thumbnail_uri`
- raw filesystem path or file path
- raw bytes
- base64 data
- raw prompt text or raw messages
- raw model/provider output
- provider secret values or authorization headers

## API Exposure Prohibitions

Reader/member APIs must not expose:

- resolved provider secrets
- prompt snapshots or raw prompts/outputs
- storage URI, filesystem path, bytes, or base64 payloads
- hidden/developer-only media, voice, visual, or provider records
- admin-only diagnostics, invocation ledgers, provider health metadata, or release evidence
