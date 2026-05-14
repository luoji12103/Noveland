# Design — v0.4 Operator/Admin UX

## Context

Admin/operator users can inspect, configure, validate, and troubleshoot providers, media assets, visual assets, speech assets, invocation ledger records, and multimodal diagnostics through controlled admin UI without exposing secrets, storage paths, raw prompt data, or hidden/developer-only records.

Current `openspec/specs/` files describe the implemented Phase 3-13 baseline. This change is proposed future work and must remain under `openspec/changes/` until implemented and archived.

## Goals / Non-Goals

Goals:

- Define a roadmap-level architecture for v0.4 Operator/Admin UX.
- Split the version into 7 independently implementable, testable, mergeable phases.
- Preserve the Phase 13 architecture freeze.

Non-goals:

- Public reader/player UI.
- Public media delivery.
- New provider capabilities or adapters.
- Runtime daemon automation or streaming.
- Core schema changes unless a later phase proposal explicitly approves a small field addition.
- Exposure of resolved secrets, storage_uri, filesystem paths, raw prompts, or raw outputs.

## Decisions

- Extend existing Web admin routes and API proxy patterns instead of creating a second admin app.
- Backend APIs remain the authority; Web UI does not bypass service ACLs or validation.
- Sensitive evidence displays must use safe summaries, redaction state, and admin-only permission checks.
- Each console is independently implementable and may ship phase by phase.

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

- Admin UI can accidentally expose internal evidence: Use safe DTOs, permission gates, and fixture-backed leak checks.
- Operator workflows can drift from API contracts: Base each screen on current API contracts and tests.
- Dashboard scope can grow into product UI: Keep v0.4 admin-only and defer reader/player surfaces to v0.8.

## Migration Plan

This roadmap skeleton does not add migrations. Future implementation phases must explicitly propose migrations when schema changes are required and must stop if phase plans and migration needs conflict.

## Open Questions

- Which phases can remain API-only and which require Web work when implementation begins?
- Which phases require new schema versus reuse of existing media/provider/invocation/eval records?
- Which phase should be selected first when the user asks to begin this version?
