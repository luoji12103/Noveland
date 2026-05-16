# Design — v0.9 Self-use MVP Demo World Cut

## Context

Noveland currently has provider execution, secret resolution, invocation ledger, media/image/speech pipelines, strict-worldline visual state, conversation turn presentations, authoring source/proposal/review/apply workflows, narrative quality diagnostics, production readiness, reader media delivery, playback/scene UI, world packaging, and moderation/readiness gates.

The next risk is not missing platform primitives. The risk is that the platform remains a set of safe subsystems without one complete self-use path. v0.9 should prove a concrete chain:

```text
provider settings
  -> visual generation control plane
  -> provider lab smoke
  -> galgame source intake
  -> script extraction
  -> persona and memory proposals
  -> visual and voice mapping
  -> demo world assembly
  -> 30-minute play gate
```

## Goals / Non-Goals

**Goals:**

- Make real provider configuration usable enough for self-use.
- Preserve configurable `base_url`, `auth_ref`, `model_name`, model discovery, capability flags, `adapter_kind`, and provider kind.
- Support OpenAI-compatible and Anthropic-compatible LLM configuration templates.
- Support MiMo V2.5 TTS/ASR and generic TTS/STT configuration templates without hardcoded vendor URLs.
- Support Z-Image, GPT Image, ComfyUI, and generic image API configuration templates without hardcoded vendor URLs.
- Support controlled image generation planning across providers with workflow templates, validated slots, visual model inventory, character visual profiles, prompt strategy, reference image policy, and reviewable AI-assisted proposals.
- Accept already-unpacked local galgame source material and preserve source traceability.
- Generate reviewable dialogue, persona, memory, visual mapping, voice mapping, and demo assembly proposals.
- Prove a 30-minute self-use loop with understandable provider/media/memory failure visibility.

**Non-Goals:**

- Cracking, unpacking, DRM bypass, scraping, or automated source acquisition.
- Public marketplace, public unauthenticated access, or broad multi-user beta workflows.
- Provider tests that run by default or consume quota in the normal gate.
- Runtime agents freely generating arbitrary ComfyUI workflow JSON or selecting arbitrary local checkpoint/LoRA assets.
- Full ComfyUI workflow editor, custom node installation, LoRA training, or model downloading in v0.9.
- Direct provider output mutation of canon, memory, visual bindings, or world state.
- Storage URI, path, bytes, base64, raw prompt, raw output, or resolved secret exposure in `world_events.payload` or reader/player/member APIs.
- Broad `worlds.py` route growth.

## Decisions

### Settings-facing provider templates reuse the provider kernel

Provider templates describe configuration shape and defaults; they do not create a second provider system. They must reuse `provider_integrations`, provider capabilities, `adapter_kind`, `ProviderSecretResolver`, `ProviderExecutionService`, provider health checks, smoke tests, and invocation ledger records.

Alternatives considered:

- Hardcode vendor integrations per model family. Rejected because MiMo may route through newapi, Z-Image may route through compatible gateways, and OpenAI/Anthropic-compatible providers need custom endpoints.
- Store user API keys directly in configuration JSON. Rejected because v0.7 secret governance requires opaque `auth_ref` and sanitized responses.

### Model discovery is best-effort with manual fallback

Provider setup must allow pulling model lists when a provider exposes a compatible endpoint, but failed discovery must not block manual model entry. This keeps self-use practical across newapi, local gateways, official endpoints, and incomplete provider APIs.

### Visual generation uses a provider-neutral control plane

Image generation should not be modeled as a ComfyUI-only parameter bag. v0.9 should define a Visual Generation Control Plane that produces provider-neutral plans before provider adapter execution. A plan captures intent, provider, workflow template, characters, scene, prompt plan, model choices, reference assets, output plan, validation results, source refs, and resulting media refs. Adapters map the plan to ComfyUI workflow slots, Z-Image request fields, GPT Image reference-image/edit fields, or generic image API request JSON.

Alternatives considered:

- Let character agents emit raw ComfyUI workflow JSON. Rejected because it bypasses validation, reproducibility, review/apply, provider capability checks, and auditability.
- Hardcode every possible workflow decision in program logic. Rejected because worlds and characters need different visual styles and reference policies.
- Make ComfyUI the central image abstraction. Rejected because v0.9 must preserve Z-Image, GPT Image, OpenAI-compatible image APIs, and generic provider compatibility.

### Workflow templates expose slots, not arbitrary execution payloads

Workflow templates are pre-registered and versioned. A template may represent ComfyUI workflow JSON, Z-Image request shape, GPT Image request shape, or generic image request shape. It exposes parameter slots such as checkpoint, LoRA list, positive prompt, negative prompt, reference images, mask/control image, seed, size, sampler, steps/CFG, and output node. Runtime generation may fill only whitelisted slots after schema, capability, visibility, and worldline validation.

### Visual model asset inventory is explicit

Checkpoint, LoRA, VAE, embedding, ControlNet, IP-Adapter, workflow template, and prompt preset choices should be represented as inventory records or equivalent provider metadata. LoRA metadata needs trigger words, recommended weight, base-model compatibility, conflicting LoRAs, preferred prompt fragments, negative prompt fragments, tags, visibility, and source/license notes where available.

### Character visual profiles guide generation

Each character/worldline may have a visual generation profile with preferred checkpoint, allowed/default/banned LoRAs, style prompt fragments, character prompt fragments, negative prompt fragments, reference image assets, workflow template preferences, and outfit/pose policies. The profile guides planner choices; it does not grant agents permission to execute arbitrary workflows.

### AI personalization is layered and reviewable

v0.9 should treat AI-assisted visual personalization in three levels:

- Level 0: fixed workflow templates where AI or deterministic logic fills validated slots only.
- Level 1: AI proposes world/character workflow bindings and visual profiles for admin review/apply.
- Level 2: AI proposes workflow variant proposals based on existing templates. Only whitelisted node or parameter changes are allowed, validation must pass, and admin review/apply is required before activation.

Runtime agents must never directly execute arbitrary workflow JSON.

### Real provider tests live in a separate provider lab profile

Default local gates must use fake/mocked providers. Real provider tests must require explicit environment such as `NOVELAND_RUN_REAL_PROVIDER_TESTS=1` and are documented for a separate worktree such as `../Noveland-provider-lab`.

### Galgame intake accepts only user-provided already-unpacked inputs

v0.9 may read local directories supplied by an authorized operator. It must not implement unpacking, decryption, DRM bypass, or automatic external content retrieval. Source traceability records must identify source batches, assets, fragments, and derived proposals.

### Extraction agents produce proposals, not canon

Dialogue extraction, persona-card generation, memory candidates, asset mapping, voice mapping, and world assembly must use preview/review/apply. Provider-backed extraction must go through `ProviderExecutionService` and write invocation/prompt snapshot evidence. Applied outputs must stay traceable to source fragments.

### Frontend planning uses the product register

Future Web implementation for settings, model lab, import review, and mapping surfaces must use Noveland's product UI posture: operator-grade, dense, explicit, keyboard-first, and safe. It must avoid marketing hero layouts, gamey admin panels, over-carded dashboards, and hidden execution or spend.

## Risks / Trade-offs

- Real provider APIs vary widely → Use template contracts, model discovery strategies, manual model fallback, provider lab tests, and actionable smoke-test failures.
- ComfyUI workflow flexibility can become unsafe → Use registered workflow templates, whitelisted slots, dry-run or schema validation, proposal/review/apply, and explicit model inventory.
- Image provider capabilities differ → Use provider-neutral plans plus capability validation so unsupported reference, edit, LoRA, mask, or workflow fields are rejected or safely ignored by policy.
- Imported copyrighted source can leak → Keep source visibility admin-scoped, use source refs in reader/player APIs, and never write raw source or storage paths to events.
- Persona/memory distillation can overfit or hallucinate → Require source traceability, uncertainty notes, conflict notes, and review/apply before memory mutation.
- Demo-world assembly can become a full authoring product → Limit v0.9 to a minimal 2-3 character self-use world and push team/beta workflows to v1.0.
- Provider failures can derail playability → Require fallbacks, safe errors, and ledger/media/provider state inspection in the MVP gate.

## Migration Plan

This roadmap does not add migrations. Future implementation phases must add a phase checkpoint before schema work. Expected migration pressure:

- Provider settings/model lab may reuse existing provider tables first; stop if new template or model-discovery persistence is required.
- Visual Generation Control Plane may need new template/profile/model-inventory records; stop if schema ownership conflicts with existing provider/media/visual packages.
- Galgame source intake should reuse v0.5 authoring records if sufficient; stop if source registry fields cannot represent directory/file traceability.
- Persona/memory distillation should reuse authoring proposals and existing memory apply paths; stop if new memory proposal schema is required.
- Visual and voice mapping should reuse media, visual, speech, and authoring proposals; stop if existing binding tables cannot preserve worldline scope.

## Open Questions

- Should provider templates be stored persistently, generated from code, or exposed as static configuration manifests?
- Should OpenAI-compatible and Anthropic-compatible text execution require new adapter kinds, or can current provider execution cover the first v0.9 scope?
- Should workflow templates and character visual profiles live under a new visual generation package or extend the existing visual/media/provider boundaries?
- What first ComfyUI validation depth is sufficient for v0.9: schema-only, mock queue dry run, real provider lab dry run, or all three?
- Which minimal galgame script formats should be first-class in Phase 4 versus treated as raw fragments with manual labels?
- Should the 30-minute self-use gate be a formal readiness API, a manual checklist backed by diagnostics, or both?
