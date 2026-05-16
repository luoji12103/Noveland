# Phase Plan — v0.9 Self-use MVP Demo World Cut

## Version Goal

Create a real playable demo world that the developer can use for about 30 minutes, using configurable real providers and user-provided already-unpacked galgame materials while preserving Noveland's existing provider, media, authoring, memory, visual, speech, worldline, and safety boundaries.

## Version Non-Goals

- Cracking, unpacking, decryption, DRM bypass, or automated acquisition.
- Public launch, public unauthenticated access, marketplace, or multi-user beta.
- Hidden provider spend or provider tests in the default gate.
- Direct canon, memory, visual, or world-state mutation from provider output.
- Broad `worlds.py` route growth.
- Duplicate provider, media, memory, eval, packaging, or readiness systems.

## Phase Discipline

- Implement phases strictly in order unless OpenSpec is updated first.
- Each phase starts from clean local `main`.
- Each phase begins with a docs-only phase checkpoint and harness update.
- Each implementation phase is independently testable, mergeable, and reversible.
- Each phase runs targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- Do not continue after failing tests, unresolved migration issues, unclear provider boundaries, unclear worldline isolation, or leak risk.
- Do not push unless explicitly requested.

## Phase 1 — MVP Provider Settings & Model Lab

### Goal

Let an operator configure and test LLM, image, TTS, and ASR providers from settings/admin surfaces.

### Scope

- Settings-facing provider templates for OpenAI-compatible LLM, Anthropic-compatible LLM, MiMo V2.5 TTS, MiMo V2.5 ASR, generic TTS/STT, Z-Image, GPT Image, ComfyUI, and generic image API.
- Editable custom `base_url`, `auth_ref`, `model_name`, model list endpoint/discovery strategy, capabilities, `adapter_kind`, and provider kind.
- Add/edit/delete/test/smoke-check/model-list/manual-model-name workflows.
- Safe API responses that return only auth refs and redacted config.

### Non-Goals

- Hardcoded official vendor endpoints.
- Direct client-side API keys.
- Provider marketplace or user secret vault.
- Hidden provider execution outside explicit test/smoke actions.

### Reused Systems

- `provider_integrations`, `provider_capabilities`, provider health checks
- `ProviderSecretResolver`, `ProviderRegistryService`, `ProviderExecutionService`, smoke validation
- `model_invocations`, `prompt_snapshots`
- v0.4 provider admin console and v0.7 secret governance patterns

### Expected Files / Packages / Routes

- Existing provider package/router where possible.
- Web settings/admin provider surfaces if implementation scope includes UI.
- No broad `worlds.py` growth.

### Targeted Tests

- Provider template CRUD.
- OpenAI-compatible and Anthropic-compatible LLM setup.
- MiMo TTS/ASR setup with configurable base URL.
- Z-Image setup with configurable base URL/model.
- Model list success and manual fallback.
- No secret or prompt/storage leak in responses, logs, prompt snapshots, or events.

### Stop Conditions

- Text provider execution cannot be safely represented in the provider kernel.
- API key/auth ref boundary is unclear.
- Model discovery requires client-side secrets.
- Provider config would leak to reader/member/player APIs.

## Phase 2 — Provider Worktree Integration Test Harness

### Goal

Create an opt-in real-provider test discipline that does not pollute the main worktree or default gate.

### Scope

- Documentation for `git worktree add ../Noveland-provider-lab <branch>`.
- Provider lab test profile.
- `NOVELAND_RUN_REAL_PROVIDER_TESTS=1` style opt-in.
- Sample smoke, model list, generation, TTS, ASR, and image checks.

### Non-Goals

- Default external API calls.
- CI quota consumption.
- Persisting real secrets outside approved `auth_ref`/env boundaries.

### Reused Systems

- Existing fake provider tests.
- Provider smoke tests and health checks.
- Invocation ledger and prompt snapshot redaction.

### Targeted Tests

- Default real-provider tests are skipped.
- Opt-in env enables marked tests.
- Secrets are not printed or persisted.

### Stop Conditions

- Test profile would call external APIs by default.
- Worktree setup requires repository policy changes outside docs/tests.

## Phase 3 — Galgame Source Intake

### Goal

Import user-provided already-unpacked galgame assets and text as traceable source material without canon mutation.

### Scope

- Source registry for sprites, expression variants, backgrounds, CG, voice audio, optional BGM/SE, script/dialogue files, character profile text, route/choice files.
- Media asset/object creation for imported files.
- Source fragment records for text.
- Preview-only import inventory.

### Non-Goals

- Cracking, unpacking, decryption, DRM bypass, scraping, or auto-download.
- Public reader exposure of raw source content.
- Direct world canon mutation.

### Reused Systems

- v0.5 authoring source registry and proposals.
- `MediaService`, media assets, media objects, media references.
- Source traceability records.

### Targeted Tests

- Import a sample already-unpacked directory.
- Preview inventory without canon mutation.
- Trace source assets/fragments.
- No storage URI in event payload.

### Stop Conditions

- Intake path requires storing raw filesystem paths in reader-visible records.
- Existing authoring source records cannot preserve required traceability.

## Phase 4 — Script Dialogue Extraction

### Goal

Extract dialogue, narration, scenes, choices, routes, emotion hints, and relationship hints from source scripts.

### Scope

- Deterministic parser for generic text, JSON, CSV, and simple script formats.
- Manual mapping for unknown formats.
- Provider extraction optional and not required for first acceptance.
- Proposal outputs for speaker candidates, line text, scene candidates, route markers, emotion hints, and relationship hints.

### Non-Goals

- Perfect VN-engine parser coverage.
- Direct agent memory writes.
- Runtime prompt injection of full raw source.

### Reused Systems

- Authoring source fragments and proposals.
- Provider execution and invocation ledger if optional provider extraction is used.

### Targeted Tests

- Extract sample script lines.
- Map speakers to character candidates.
- Preserve unresolved/uncertain speakers.
- Output proposals only.

### Stop Conditions

- Parser requires unsafe raw source exposure.
- Provider extraction would bypass invocation ledger.

## Phase 5 — Character Memory Distillation Agent

### Goal

Generate persona cards and initial memory candidates so character agents are not empty-memory agents.

### Scope

- Persona card, speech style, relationship summary, key memories, emotional baseline, taboo/secret knowledge, route-specific facts, sample dialogue style, uncertainty/conflict notes.
- Provider-backed extraction through `ProviderExecutionService`.
- Reviewable authoring proposals before memory/persona apply.

### Non-Goals

- Direct unreviewed memory writes.
- Full raw script copies in runtime prompts.
- Provider output mutating canon.

### Reused Systems

- Provider execution, invocation ledger, prompt snapshots.
- Authoring proposals and review/apply.
- Memory service and agent persona services on explicit apply.

### Targeted Tests

- Generate persona from N source lines.
- Generate relationship memory candidates.
- Apply reviewed proposals to non-empty persona/memory.
- Preserve source traceability and redaction.

### Stop Conditions

- Prompt snapshot visibility or raw source boundary is unclear.
- Memory apply cannot be kept reviewable.

## Phase 6 — Visual Asset Mapping

### Goal

Map imported sprites, variants, backgrounds, and CGs into the visual system for galgame playback.

### Scope

- Character sprite sets and neutral/happy/sad variants.
- Scene background profiles.
- CG association as reader-safe media where appropriate.
- Filename, directory, metadata, and manual mapping proposals.
- Preview/apply without overwriting existing bindings automatically.

### Non-Goals

- New visual storage system.
- Automatic destructive remapping.
- Public raw source delivery.

### Reused Systems

- Media kernel.
- v0.9 source traceability.
- v0.8 scene view and reader media delivery.
- Phase 9 visual resolver and bindings.

### Targeted Tests

- Map neutral/happy/sad variants.
- Map 3-5 backgrounds.
- Reject cross-world and cross-worldline assets.
- Galgame view can resolve imported assets after apply.

### Stop Conditions

- Visual binding worldline isolation is unclear.
- Mapping would expose hidden/developer/private assets to readers.

## Phase 7 — Voice Profile Mapping

### Goal

Bind imported voice references or configurable MiMo/generic speech providers to characters.

### Scope

- Select provider, model, voice profile, voice ID, and style mapping.
- MiMo base URL/model name configured through settings, including newapi distribution.
- TTS smoke test.
- Voice profile binding to agents.

### Non-Goals

- Voice cloning implementation beyond provider-supported configuration.
- Hardcoded MiMo endpoint.
- API key exposure.

### Reused Systems

- Speech service, voice profiles, voice bindings, style mappings, transcripts.
- Provider settings/model lab.
- Invocation ledger and media references.

### Targeted Tests

- Character can generate TTS.
- Voice profile binds to agent/worldline.
- Style mapping follows emotion.
- API key does not appear in responses/events.

### Stop Conditions

- Speech provider config cannot be represented safely as `auth_ref`.
- TTS smoke would require client-side secrets.

## Phase 8 — Demo World Assembly

### Goal

Assemble a minimal demo world from reviewed source, persona, memory, visual, voice, and dialogue proposals.

### Scope

- 2-3 characters.
- One initial conversation path.
- Backgrounds, sprites, optional CG, and voice.
- Initial relationships and memories.
- Source traceability for applied content.

### Non-Goals

- Private beta onboarding.
- Perfect content polish.
- Global canon pollution.

### Reused Systems

- Authoring preview/apply.
- Worlds, worldlines, agents, conversations.
- Media, visual, speech, memory, reader playback, scene view.

### Targeted Tests

- Demo world can be entered.
- Characters have persona/memory.
- Conversation triggers presentation.
- Visual/audio assets resolve safely.

### Stop Conditions

- Assembly requires developer-only DB edits as the primary workflow.
- Source traceability is lost on apply.

## Phase 9 — 30-Minute Self-use MVP Gate

### Goal

Validate a self-use demo world that can be played for about 30 minutes and resumed later.

### Scope

- Manual/test-backed gate for entering the world, sustained conversation, state persistence, memory persistence, visual/speech follow-through, provider failure messaging, and admin ledger/media/job/provider inspection.
- Failure log and follow-up proposal capture.

### Non-Goals

- Public launch readiness.
- Private beta readiness.
- Automated content quality guarantees.

### Reused Systems

- v0.8 public launch/readiness evidence patterns.
- Multimodal diagnostics.
- Invocation ledger, media jobs, provider health, memory diagnostics.

### Targeted Tests

- Gate report passes when required evidence is present.
- Gate blocks when provider, memory, visual, or speech evidence is missing.
- Resume preserves conversation and memory state.

### Stop Conditions

- Demo requires manual DB edits to begin.
- Provider failures are unsafe or incomprehensible.
- Raw prompts, outputs, storage paths, or secrets appear in reports.
