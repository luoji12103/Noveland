# Design — v0.5 Authoring & Import Studio

## Context

World admins can ingest source materials, preview extracted canon, characters, relationships, memories, and assets, resolve conflicts, and selectively apply reviewed imports into a target worldline.

Current `openspec/specs/` files describe the implemented Phase 3-13 baseline. This change is proposed future work and must remain under `openspec/changes/` until implemented and archived.

## Goals / Non-Goals

Goals:

- Define a roadmap-level architecture for v0.5 Authoring & Import Studio.
- Split the version into 9 independently implementable, testable, mergeable phases.
- Preserve the Phase 13 architecture freeze.

Non-goals:

- Unreviewed automatic writes to canonical world state
- One-pass perfect parsing
- Bypassing preview/apply
- Automatic memory writes without migration proposal/apply
- Long-term runtime prompts containing full raw copyrighted sources
- Provider outputs directly mutating world state

## Decisions

- Treat imported material as source assets and proposals before apply.
- Persist traceability from applied records back to source fragments.
- Use media assets for imported images/audio and never narrative_artifacts as binary storage.
- Keep target worldline explicit for all import runs and proposals.

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

## Risks / Trade-offs

- Parsing can overclaim uncertain facts: Classify claims as canon, inferred, or uncertain and require admin review.
- Copyrighted source can leak into runtime prompts: Store source assets with controlled visibility and summarized extraction outputs.
- Import apply can pollute a worldline: Use preview/apply, conflict review, and rollback hints.

## Migration Plan

This roadmap skeleton does not add migrations. Future implementation phases must explicitly propose migrations when schema changes are required and must stop if phase plans and migration needs conflict.

## Open Questions

- Which phases can remain API-only and which require Web work when implementation begins?
- Which phases require new schema versus reuse of existing media/provider/invocation/eval records?
- Which phase should be selected first when the user asks to begin this version?
