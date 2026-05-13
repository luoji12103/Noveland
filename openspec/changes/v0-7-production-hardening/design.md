# Design — v0.7 Production Hardening

## Context

Noveland should support stable long-running deployment with stronger permissions, secret governance, budgets, backups, observability, and security regression coverage.

Current `openspec/specs/` files describe the implemented Phase 3-13 baseline. This change is proposed future work and must remain under `openspec/changes/` until implemented and archived.

## Goals / Non-Goals

Goals:

- Define a roadmap-level architecture for v0.7 Production Hardening.
- Split the version into 8 independently implementable, testable, mergeable phases.
- Preserve the Phase 13 architecture freeze.

Non-goals:

- Large new gameplay features
- Player-facing public launch
- Provider marketplace
- Streaming
- Expanded automatic content generation

## Decisions

- Harden existing boundaries before broad public exposure.
- Govern provider and cost controls centrally.
- Use readiness gates for internal production posture, not public launch.
- Prefer backup/restore drills and regression tests over unchecked operational assumptions.

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

- Hardening can block feature work: Scope each phase to one operational risk class.
- Secret governance can become a vault project: Keep vault/KMS as explicit future decision unless required.
- Production gates can be mistaken for public launch: Keep v0.7 internal readiness only.

## Migration Plan

This roadmap skeleton does not add migrations. Future implementation phases must explicitly propose migrations when schema changes are required and must stop if phase plans and migration needs conflict.

## Open Questions

- Which phases can remain API-only and which require Web work when implementation begins?
- Which phases require new schema versus reuse of existing media/provider/invocation/eval records?
- Which phase should be selected first when the user asks to begin this version?
