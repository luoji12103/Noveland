# Design — v0.8 Public Experience & Ecosystem

## Context

Noveland should expose safe reader/player experiences, worldline navigation, media playback, world packaging, and plugin/provider packaging while preserving production/security boundaries.

Current `openspec/specs/` files describe the implemented Phase 3-13 baseline. This change is proposed future work and must remain under `openspec/changes/` until implemented and archived.

## Goals / Non-Goals

Goals:

- Define a roadmap-level architecture for v0.8 Public Experience & Ecosystem.
- Split the version into 11 independently implementable, testable, mergeable phases.
- Preserve the Phase 13 architecture freeze.

Non-goals:

- Bypassing production readiness
- Exposing developer_only/hidden media
- Exposing raw invocation prompts/outputs
- Exposing storage_uri/path
- Plugins bypassing provider secret boundary
- Unreviewed public world launch

## Decisions

- Reader/player delivery must use safe public DTOs and visibility checks.
- World packaging must exclude secrets and internal storage references.
- Plugin/provider packaging describes capabilities and safety review before installation.
- Public launch gate builds on v0.7 internal readiness rather than replacing it.

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

- Public media delivery can leak internal paths: Use signed/safe delivery endpoints and visibility checks.
- Plugins can bypass boundaries: Require package contracts and safety review.
- Public launch can outpace moderation: Add moderation and incident workflow before launch gate acceptance.

## Migration Plan

This roadmap skeleton does not add migrations. Future implementation phases must explicitly propose migrations when schema changes are required and must stop if phase plans and migration needs conflict.

## Open Questions

- Which phases can remain API-only and which require Web work when implementation begins?
- Which phases require new schema versus reuse of existing media/provider/invocation/eval records?
- Which phase should be selected first when the user asks to begin this version?
