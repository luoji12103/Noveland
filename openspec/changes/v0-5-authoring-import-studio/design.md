# Design — v0.5 Authoring & Import Studio

## Context

World admins can ingest source materials, preview extracted canon, characters, relationships, memories, and assets, resolve conflicts, and selectively apply reviewed imports into a target worldline.

Current `openspec/specs/` files describe the implemented Phase 3-13 baseline. This change is proposed future work and must remain under `openspec/changes/` until implemented and archived.

## Goals / Non-Goals

Goals:

- Define a roadmap-level architecture for v0.5 Authoring & Import Studio.
- Split the version into 8 independently implementable, testable, mergeable phases.
- Create a dedicated authoring package/router boundary for v0.5 implementation.
- Put import run, proposal, review, source traceability, preview, and apply foundations in Phase 1.
- Preserve the Phase 13 architecture freeze.

Non-goals:

- Unreviewed automatic writes to canonical world state
- One-pass perfect parsing
- Bypassing preview/apply
- Automatic memory writes without migration proposal/apply
- Long-term runtime prompts containing full raw copyrighted sources
- Provider outputs directly mutating world state

## Decisions

- Create `backend/packages/authoring/` and `backend/services/api/src/noveland/services/api/authoring.py` for v0.5.
- Register the authoring router at the app level; do not continue expanding `worlds.py` for authoring/import logic.
- Treat existing `authoring_templates`, `authoring_import_jobs`, and world composition import as legacy-compatible inputs or references only.
- Treat imported material as source assets and proposals before apply.
- Persist traceability from applied records back to source fragments.
- Use media assets for imported images/audio and never narrative_artifacts as binary storage.
- Keep target worldline explicit for all import runs and proposals.
- Keep lore/world-bible import proposal-only until a later accepted architecture decision defines safe global/worldline canon apply behavior.
- Reuse provider execution, invocation ledger, media, memory, visual, speech, worldline, and eval/diagnostics services instead of duplicating them.

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
- v0.5 authoring routes are admin/reviewer surfaces unless a later accepted change defines reader-facing import visibility

## Risks / Trade-offs

- Parsing can overclaim uncertain facts: Classify claims as canon, inferred, or uncertain and require admin review.
- Copyrighted source can leak into runtime prompts: Store source assets with controlled visibility and summarized extraction outputs.
- Import apply can pollute a worldline: Use preview/apply, conflict review, and rollback hints.
- Legacy authoring routes in `worlds.py` already exist: keep them compatible but avoid further route growth there.
- Global `WorldBible` and several canon tables are not strict-worldline records: v0.5 lore extraction must stay proposal-only until apply semantics are explicitly accepted.

## Migration Plan

This roadmap skeleton does not add migrations. Future implementation phases must explicitly propose migrations when schema changes are required and must stop if phase plans and migration needs conflict.

Expected implementation migration direction:

- Phase 1 likely requires the core authoring schema: source batches/assets/fragments, import runs, proposals, review decisions, and traceability records.
- Later phases should prefer reusing Phase 1 proposal/review/apply tables and existing media/provider/invocation/memory/visual/speech tables.
- World-bible/lore extraction should not add direct apply/backfill schema unless a separate architecture decision accepts the global-vs-worldline canon boundary.

## Open Questions

- Which phases can remain API-only and which require Web work when implementation begins?
- Which proposal kinds need first-class columns versus safe JSON evidence in the Phase 1 authoring schema?
- Should legacy `authoring_templates` be importable into the new source registry through a compatibility action, or only referenced/read?
