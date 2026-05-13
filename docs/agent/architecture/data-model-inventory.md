# Data Model Inventory

This inventory covers the Phase 3-12 multimodal data model. Tables are grouped by phase and owning package.

## Phase 3 Invocation Ledger

### `model_invocations`

- Owner: `noveland.invocations`
- Purpose: audit source for model/provider calls.
- Worldline: non-null `world_id` and `worldline_id`.
- References: agent, conversation, turn, world event, media job, media asset, memory write job.
- Must not store: resolved provider secrets or unrestricted reader-facing raw content.
- Migration: `20260512_0032_model_invocation_ledger.py`

### `prompt_snapshots`

- Owner: `noveland.invocations`
- Purpose: request/prompt/response evidence for one invocation.
- Worldline: through `model_invocations`.
- References: one `model_invocations` row.
- Must not store: unredacted authorization headers, secret values, storage bytes, or reader-visible raw prompts.
- Migration: `20260512_0032_model_invocation_ledger.py`

### `prompt_templates`, `model_invocation_tags`, `agent_runtime_run_model_invocations`

- Owner: `noveland.invocations`
- Purpose: reusable prompts, searchable tags, and runtime-run to invocation links.
- Worldline: templates can be global/world scoped; tags and runtime links are worldline-scoped.
- Must not store: provider secrets or media bytes.
- Migration: `20260512_0032_model_invocation_ledger.py`

## Phase 4 Media Kernel

### `media_assets`

- Owner: `noveland.media`
- Purpose: canonical media asset metadata.
- Worldline: non-null `world_id` and `worldline_id`.
- References: source job, source event, source invocation.
- Must not store: raw binary bytes or base64.
- Migration: `20260512_0033_media_kernel.py`

### `media_objects`

- Owner: `noveland.media`
- Purpose: object-level storage metadata for assets.
- Worldline: non-null `world_id` and `worldline_id`.
- References: `media_assets`.
- Must not store: raw bytes; `storage_uri` is internal and not regular response content.
- Migration: `20260512_0033_media_kernel.py`

### `media_jobs`

- Owner: `noveland.media`
- Purpose: queued/running/completed media work record.
- Worldline: non-null `world_id` and `worldline_id`.
- References: conversation, turn, agent, source event, source invocation.
- Must not store: provider secrets, binary bytes, base64, raw prompts.
- Migration: `20260512_0033_media_kernel.py`

### `media_references`, `media_asset_inputs`, `media_asset_tags`, `media_asset_collections`

- Owner: `noveland.media`
- Purpose: generic attachment, lineage, tagging, and collection metadata.
- Worldline: non-null for references/inputs/tags/collections.
- References: media assets, jobs, turns, agents, scenes, events, narrative artifacts as relationship targets only.
- Must not store: binary bytes or leaked storage paths in arbitrary metadata.
- Migration: `20260512_0033_media_kernel.py`

## Phase 5 Provider Kernel

### `provider_integrations`

- Owner: `noveland.providers`
- Purpose: configured provider registry entry.
- Worldline: world-scoped or global; not worldline-scoped.
- References: optional world.
- Must not store: actual API keys or secret values in `auth_ref`, `config_json`, or `default_params_json`.
- Migration: `20260512_0034_provider_execution_kernel.py`

### `provider_capabilities`

- Owner: `noveland.providers`
- Purpose: capability metadata for routing and validation.
- Worldline: inherits provider scope.
- References: `provider_integrations`.
- Must not store: secrets.
- Migration: `20260512_0034_provider_execution_kernel.py`

### `provider_health_checks`

- Owner: `noveland.providers`
- Purpose: health/smoke status evidence.
- Worldline: inherits provider scope.
- References: `provider_integrations`.
- Must not store: secrets, auth headers, raw request bodies.
- Migration: `20260512_0034_provider_execution_kernel.py`

## Phase 6 Image Links

- Owner: `noveland.media`, `noveland.providers`
- Purpose: image generation/edit/compose uses existing media jobs/assets/objects/inputs plus invocation links.
- Worldline: image jobs and assets are worldline-scoped.
- References: `model_invocations`, `prompt_snapshots`, `media_assets`, `media_objects`, `media_jobs`, `media_asset_inputs`.
- Must not store: image bytes/base64 in event payloads or regular API JSON.
- Migration: no image-specific table beyond Phase 4/5 records.

## Phase 7 Speech And Voice

### `voice_profiles`

- Owner: `noveland.speech`
- Purpose: reusable voice identity/configuration.
- Worldline: nullable for profile definitions, but bindings and transcript usage must validate world/worldline.
- References: owner agent, provider integration, provider voice id, optional reference asset.
- Must not store: voice audio bytes or provider secrets.
- Migration: `20260512_0036_speech_voice_pipeline.py`

### `agent_voice_profile_bindings`

- Owner: `noveland.speech`
- Purpose: many-to-many agent to voice profile binding.
- Worldline: nullable in schema, but Phase 10/13 flows require same worldline validation for turn rendering.
- References: agent and voice profile.
- Must not store: audio bytes or provider secrets.
- Migration: `20260512_0036_speech_voice_pipeline.py`

### `speech_transcripts`

- Owner: `noveland.speech`
- Purpose: STT transcript record.
- Worldline: non-null `world_id` and `worldline_id`.
- References: source audio asset, media job, model invocation, conversation, turn.
- Must not store: audio bytes, storage paths, or automatic memory writes.
- Migration: `20260512_0036_speech_voice_pipeline.py`

### `speech_style_mappings`

- Owner: `noveland.speech`
- Purpose: map emotion tags to provider style payloads.
- Worldline: world-scoped.
- References: provider kind.
- Must not store: secrets.
- Migration: `20260512_0036_speech_voice_pipeline.py`

## Phase 9 Visual

### `character_sprite_sets`

- Owner: `noveland.visual`
- Purpose: agent/style-level sprite collection.
- Worldline: non-null strict worldline.
- References: agent and default variant id.
- Must not store: storage URIs, image bytes, nullable worldline defaults.
- Migration: `20260512_0037_visual_asset_system.py`

### `character_sprite_variants`

- Owner: `noveland.visual`
- Purpose: expression/pose/outfit sprite variant mapping.
- Worldline: non-null strict worldline.
- References: sprite set and media asset.
- Must not store: storage URIs, image bytes, nullable worldline defaults.
- Migration: `20260512_0037_visual_asset_system.py`

### `scene_background_profiles`

- Owner: `noveland.visual`
- Purpose: scene/location/time/weather to background asset mapping.
- Worldline: non-null strict worldline.
- References: scene and media asset.
- Must not store: storage URIs, image bytes, nullable worldline defaults.
- Migration: `20260512_0037_visual_asset_system.py`

## Phase 10 Presentation

### `conversation_turn_presentations`

- Owner: `noveland.conversations`
- Purpose: canonical presentation state for one conversation turn.
- Worldline: non-null `world_id` and `worldline_id`, unique per turn.
- References: conversation, turn, speaker agent, sprite set/variant, voice profile, TTS asset, background asset, composite asset, transcript.
- Must not store: storage URIs, bytes, base64, raw provider prompts, or replacement turn text.
- Migration: `20260512_0038_conversation_turn_presentations.py`

## Phase 11 Asset Generation

### `asset_generation_policies`

- Owner: `noveland.asset_generation`
- Purpose: admin-reviewed generation policy settings.
- Worldline: non-null strict worldline.
- References: worldline.
- Must not store: secrets, storage URIs, raw bytes, base64.
- Migration: `20260512_0039_asset_generation_orchestrator.py`

### `asset_generation_runs`

- Owner: `noveland.asset_generation`
- Purpose: preview/apply run envelope.
- Worldline: non-null strict worldline.
- References: optional policy.
- Must not store: provider secrets or raw binary data.
- Migration: `20260512_0039_asset_generation_orchestrator.py`

### `asset_generation_proposals`

- Owner: `noveland.asset_generation`
- Purpose: reviewable generation proposal with safe request/evidence JSON.
- Worldline: non-null strict worldline.
- References: run, provider integration, resulting media job.
- Must not store: provider secrets, storage URIs, raw bytes, base64, raw prompt/output.
- Migration: `20260512_0039_asset_generation_orchestrator.py`

## Phase 12 Reused Eval Records

### `long_run_eval_runs`

- Owner: `noveland.worlds`
- Purpose: reused eval evidence table for multimodal diagnostics.
- Worldline: non-null `world_id` and `worldline_id`.
- References: worldline through IDs and safe metadata/evidence refs.
- Must not store: storage URIs, raw prompt/output, secrets, media bytes, base64.
- Migration: existing beta release readiness migration, reused by Phase 12.
