# Design — v0.6 Runtime Narrative Quality

## Context

Noveland runtime should produce more consistent, character-faithful, emotionally coherent, and causally continuous world evolution while preserving review gates and worldline isolation.

Current `openspec/specs/` files describe the implemented Phase 3-13 baseline. This change is proposed future work and must remain under `openspec/changes/` until implemented and archived.

## Goals / Non-Goals

Goals:

- Define a roadmap-level architecture for v0.6 Runtime Narrative Quality.
- Split the version into 10 independently implementable, testable, mergeable phases.
- Preserve the Phase 13 architecture freeze.

Non-goals:

- Provider output directly modifying world state
- Bypassing invocation ledger
- Bypassing context visibility
- Automatic GM apply for high-impact events
- Public launch
- Broad new runtime-quality routes in `worlds.py`
- Web dashboard implementation in initial v0.6 phases
- Making quality evaluation block every runtime path initially

## Decisions

- Add or confirm provider-kernel text generation execution before provider-backed GM or narrative generation.
- Decide the `narrative_artifacts` worldline strategy before Narrative Writer v2: v2-generated narrative artifacts/publications require first-class worldline persistence before write paths are added. Legacy metadata may be read for compatibility, but new v2 write isolation must not rely on metadata alone.
- Use a dedicated narrative quality boundary for new v0.6 APIs:
  `backend/packages/narrative_quality/` and
  `backend/services/api/src/noveland/services/api/narrative_quality.py`.
- Register the narrative quality router at app-level only.
- Implement API-first diagnostics; defer Web dashboard routes, components, and e2e scenarios until API contracts are stable.
- Separate agent, conversation, GM, narrative, and eval contexts.
- Provider-backed GM work creates proposals first.
- Quality diagnostics produce admin-visible evidence before runtime blockers.
- Pacing policies constrain lookahead and generation budgets.

## Boundary

New v0.6 quality APIs SHALL be implemented in the narrative quality package/router. They SHALL reuse existing systems rather than duplicating them:

- `ProviderExecutionService`, `ProviderSecretResolver`, invocation ledger, and prompt snapshots.
- `LivingWorldContextSelector` and `LivingWorldGuardrailService`.
- `GMEventProposal`, `NarrativeArtifactService`, and `NarrativeContinuityReview`.
- `conversation_turn_presentations`, visual resolver, and speech style mappings.
- multimodal eval diagnostics and `LongRunEvalRun`.

Do not add broad new runtime-quality routes to `worlds.py`. A narrow compatibility helper is acceptable only if a later implementation plan proves it unavoidable.

## Architecture Guardrails

- no storage_uri/path/base64/bytes in world_events.payload
- no raw prompt/output in world_events.payload
- no resolved provider secret exposure
- strict worldline visual state
- provider output does not directly mutate world state
- media assets are not narrative artifacts
- ComfyUI remains optional provider, not a core dependency
- asset generation remains admin apply only unless a future accepted OpenSpec change changes it
- conversation presentation remains API-only until a specific UI phase implements it
- no runtime daemon auto-generation unless a future accepted OpenSpec change changes it
- reader/player-facing routes do not expose admin/developer-only data
- API responses suppress raw prompts, raw outputs, prompt snapshots, storage paths, secrets, bytes, base64, and admin-only evidence for non-admin callers

## Risks / Trade-offs

- Quality scoring can become subjective: Use scenario-backed metrics and diagnostics rather than vague scores.
- GM automation can overreach: Keep proposal/review/apply boundaries for impact-bearing events.
- Context leaks can expose secrets or hidden information: Use visibility-aware context schemas and prompt snapshots.
- Web work can couple UI to unstable APIs: keep v0.6 diagnostics API-first until contracts are proven.
- Narrative Writer v2 can weaken worldline isolation if `narrative_artifacts` remain metadata-scoped only: decide the schema strategy before implementation.
- Provider-backed text work can accidentally revive legacy provider profiles: route new provider-backed v0.6 generation through the provider kernel.

## Migration Plan

This roadmap skeleton does not add migrations. Future implementation phases must explicitly propose migrations when schema changes are required and must stop if phase plans and migration needs conflict.

## Open Questions

- Which phases require new schema versus reuse of existing media/provider/invocation/eval records?
- Which phase should be selected first when the user asks to begin this version?
- Should GM proposal invocation linkage remain safe JSON evidence or become a direct FK to `model_invocations`?
