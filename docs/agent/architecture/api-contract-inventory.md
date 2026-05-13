# API Contract Inventory

This inventory lists stable Phase 3-12 backend API boundaries. It is intentionally concise and points to owning DTOs, services, ACL expectations, and side effects.

## Providers

- Router: `backend/services/api/src/noveland/services/api/providers.py`
- Paths: `/worlds/{world_id}/providers`, provider capabilities, health check, smoke test, test invocation.
- DTOs: `noveland.providers.contracts`
- Services: `ProviderRegistryService`, `ProviderHealthService`, `ProviderExecutionService`
- ACL: world admin for world providers; platform admin for global/restricted providers.
- Worldline: execution and media refs validate same world/worldline when present.
- Side effects: provider CRUD, health checks, invocation ledger records, media jobs/assets/objects for fake/image/speech flows.
- Tests: `test_api_providers.py`, `test_provider_registry_service.py`, `test_provider_execution_service.py`

## Model Invocations

- Router: `backend/services/api/src/noveland/services/api/invocations.py`
- Paths: `/worlds/{world_id}/model-invocations`, prompt snapshots, prompt templates, invocation tags.
- DTOs: `noveland.invocations.contracts`
- Services: `InvocationLedgerService`, `PromptSnapshotService`
- ACL: world admin only.
- Worldline: invocation records are worldline-scoped.
- Side effects: ledger writes, snapshot writes, redaction/status updates, tags.
- Tests: `test_api_invocations.py`, `test_invocation_ledger_service.py`

## Media

- Router: `backend/services/api/src/noveland/services/api/media.py`
- Paths: `/worlds/{world_id}/media/*`, turn media attachment routes.
- DTOs: `noveland.media.contracts`
- Services: `MediaService`, `MediaJobService`, `MediaCatalogService`, `MediaReferenceService`
- ACL: world admin/member according to route; restricted records are filtered.
- Worldline: assets, objects, jobs, references, contexts, inputs, tags, and collections validate same worldline.
- Side effects: media asset/object upload, job updates, references, tags, collections, lineage.
- Tests: `test_api_media.py`, `test_api_media_catalog.py`, `test_media_service.py`, `test_media_catalog_service.py`, `test_media_storage.py`

## Images

- Router: `backend/services/api/src/noveland/services/api/images.py`
- Paths: `/worlds/{world_id}/images/generate`, edit, compose, jobs.
- DTOs: `noveland.media.image_contracts`
- Services: `ImageService`, `ProviderExecutionService`, media composer.
- ACL: world admin.
- Worldline: image jobs/assets/objects are worldline-scoped.
- Side effects: provider-backed generation/edit writes invocation ledger and media records; local composition writes media job/asset/object without provider invocation.
- Tests: `test_api_images.py`, `test_image_service.py`, `test_image_composer.py`, adapter tests.

## Speech

- Router: `backend/services/api/src/noveland/services/api/speech.py`
- Paths: `/worlds/{world_id}/speech/*`, `/worlds/{world_id}/agents/{agent_id}/voice-profiles`.
- DTOs: `noveland.speech.contracts`
- Services: `SpeechService`, `VoiceProfileService`, `SpeechTranscriptService`, `SpeechStyleMappingService`
- ACL: world admin for management and speech operations.
- Worldline: voice bindings, TTS/STT jobs, transcripts, source audio, and output audio validate same worldline.
- Side effects: TTS/STT jobs, provider execution, media records, turn media references, transcript records.
- Tests: `test_api_speech.py`, `test_speech_service.py`, `test_voice_profiles.py`, speech adapter tests.

## Visual

- Router: `backend/services/api/src/noveland/services/api/visual.py`
- Paths: `/worlds/{world_id}/visual/sprite-sets`, variants, resolve-sprite, backgrounds, resolve-background, compose-scene.
- DTOs: `noveland.visual.contracts`
- Services: `VisualAssetService`, `VisualResolver`, `VisualCompositionService`
- ACL: world admin.
- Worldline: all visual records require non-null worldline; referenced assets must match same worldline.
- Side effects: visual binding CRUD, deterministic resolution, composition through image service.
- Tests: `test_api_visual.py`, `test_visual_service.py`

## Conversation Presentations

- Router: `backend/services/api/src/noveland/services/api/conversation_presentations.py`
- Paths: `/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation/*`
- DTOs: `noveland.conversations.contracts`
- Services: `ConversationPresentationService`, `VisualResolver`, `VisualCompositionService`, `SpeechService`
- ACL: world admin.
- Worldline: presentation and referenced sprite/background/voice/media/transcript records must match conversation worldline.
- Side effects: presentation upsert/update, visual render, TTS render, STT transcript, media references.
- Tests: `test_api_conversation_presentations.py`, `test_conversation_presentation_service.py`

## Asset Generation

- Router: `backend/services/api/src/noveland/services/api/asset_generation.py`
- Paths: `/worlds/{world_id}/asset-generation/*`, `/worlds/{world_id}/media/jobs/reprioritize`, cancel-superseded.
- DTOs: `noveland.asset_generation.contracts`
- Services: `AssetGenerationService`, `MediaJobService`
- ACL: world admin.
- Worldline: policies, runs, proposals, and created jobs are strict-worldline records.
- Side effects: preview persists proposals only; apply creates queued media jobs; job priority/cancel helpers update existing jobs.
- Tests: `test_api_asset_generation.py`, `test_asset_generation_service.py`

## Multimodal Evals

- Router: `backend/services/api/src/noveland/services/api/multimodal_evals.py`
- Paths: `/worlds/{world_id}/multimodal-evals`, run/get, `/worlds/{world_id}/diagnostics/multimodal`.
- DTOs: `noveland.multimodal_eval.contracts`
- Services: `MultimodalEvalService`
- ACL: world admin.
- Worldline: diagnostics and eval runs are worldline-scoped.
- Side effects: diagnostics read existing records; eval run writes `long_run_eval_runs`.
- Tests: `test_api_multimodal_evals.py`, `test_multimodal_eval_service.py`
