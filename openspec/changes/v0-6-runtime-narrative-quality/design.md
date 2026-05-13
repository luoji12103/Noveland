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
- Making quality evaluation block every runtime path initially

## Decisions

- Separate agent, conversation, GM, narrative, and eval contexts.
- Provider-backed GM work creates proposals first.
- Quality diagnostics produce admin-visible evidence before runtime blockers.
- Pacing policies constrain lookahead and generation budgets.

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

- Quality scoring can become subjective: Use scenario-backed metrics and diagnostics rather than vague scores.
- GM automation can overreach: Keep proposal/review/apply boundaries for impact-bearing events.
- Context leaks can expose secrets or hidden information: Use visibility-aware context schemas and prompt snapshots.

## Migration Plan

This roadmap skeleton does not add migrations. Future implementation phases must explicitly propose migrations when schema changes are required and must stop if phase plans and migration needs conflict.

## Open Questions

- Which phases can remain API-only and which require Web work when implementation begins?
- Which phases require new schema versus reuse of existing media/provider/invocation/eval records?
- Which phase should be selected first when the user asks to begin this version?
