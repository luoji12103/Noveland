# Proposal — v0.9 Self-use MVP Demo World Cut

## Why

Noveland has completed the platform, authoring, quality, production-hardening, and public-experience foundations through v0.8. The next step should not expand architecture broadly; it should compress those foundations into a real self-use loop where the developer can configure real providers, import already-unpacked galgame materials, assemble a demo world, and play it for about 30 minutes.

## What Changes

- Plan a v0.9 roadmap focused on one playable demo world rather than another platform expansion wave.
- Productize provider setup through settings-facing templates, model list discovery, manual model-name fallback, smoke checks, and provider lab testing.
- Add a Visual Generation Control Plane for provider-neutral image generation planning across ComfyUI, Z-Image, GPT Image, OpenAI-compatible image APIs, and generic image providers.
- Accept only user-provided already-unpacked galgame assets and scripts; do not implement cracking, unpacking, DRM bypass, or automated acquisition.
- Extend the authoring/import workflow toward galgame source intake, script dialogue extraction, persona-card generation, memory candidates, visual generation profiles, visual mapping, voice mapping, and demo-world assembly.
- Keep import, memory migration, asset binding, persona creation, and world assembly behind preview/review/apply.
- Keep workflow/profile/model-selection changes behind pre-registered templates, validated slots, proposal/review/apply, and provider capability checks.
- Preserve provider secret boundaries, media boundaries, invocation ledger records, source traceability, worldline isolation, and safe reader/player DTOs.
- Require real provider tests to run only in an opt-in provider lab worktree/profile, never in the default gate.

## Capabilities

### New Capabilities

- `mvp-provider-settings-model-lab`: Settings/admin-facing provider templates, editable provider configuration, model discovery, manual model fallback, and safe smoke checks for LLM, image, TTS, and ASR providers.
- `visual-generation-control-plane`: Versioned workflow templates, visual model asset inventory, character visual generation profiles, provider-neutral visual generation plans, reference image policies, ComfyUI slot validation, and reviewable AI-assisted workflow/profile proposals.
- `provider-worktree-integration-harness`: Opt-in real-provider worktree and test profile for smoke, model list, sample generation, TTS, ASR, and image checks without default quota spend.
- `galgame-source-intake`: Intake already-unpacked galgame source directories into traceable source assets, fragments, and media records without canon mutation.
- `galgame-dialogue-extraction`: Extract speaker, line, narrator, scene, choice, route, emotion, and relationship candidates from source scripts as reviewable proposals.
- `character-memory-distillation`: Use extraction agents to produce character persona cards, speech style, relationship summaries, and memory candidates from traceable source fragments.
- `galgame-visual-asset-mapping`: Map imported sprites, expression variants, backgrounds, and CG assets into the existing media and visual systems through preview/apply.
- `galgame-voice-profile-mapping`: Map imported voice references or configurable MiMo/generic speech presets into voice profiles, bindings, and style mappings.
- `demo-world-assembly`: Assemble a minimal demo world from reviewed imports, persona/memory candidates, visual mappings, voice mappings, conversations, and source traceability.
- `self-use-mvp-gate`: Validate that the developer can enter the demo world, play for about 30 minutes, inspect failures, and resume with preserved state.

### Modified Capabilities

- None. v0.9 may later extend implemented specs during implementation, but this roadmap change introduces new planned capability contracts.

## Impact

- Future backend work will likely touch provider settings, provider adapters, model discovery, workflow template registries, image planning, authoring, media, visual, speech, memory, conversations, and readiness/eval packages.
- Future Web work will likely touch provider settings/model lab, visual generation template/profile review, import review, asset mapping, voice mapping, and demo-world setup surfaces; those surfaces must use the existing Noveland product UI style and avoid marketing/gamey admin patterns.
- Future implementation must not add broad routes to `worlds.py`, duplicate provider/media/memory systems, expose secrets or storage paths, or run real external provider calls by default.
