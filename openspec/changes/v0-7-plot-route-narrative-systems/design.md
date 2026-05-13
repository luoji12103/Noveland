## Context

The current system can record events, conversations, narrative artifacts, media, presentation, and diagnostics. It does not yet model unresolved promises, route progress, event conditions, secrets, knowledge flow, or emotional state as first-class story systems.

## Goals / Non-Goals

Goals:

- Add explicit plot/route/secret/knowledge/emotion records.
- Convert events into scene beat inputs for narrative generation.
- Preserve character knowledge boundaries in prompts and outputs.
- Provide diagnostics for continuity and route progression.

Non-goals:

- Automatic content moderation unless a later policy layer requires it.
- Public launch reader UX.
- Streaming conversation/media.
- Replacing the narrative artifact workflow.

## Decisions

- Plot and route state should reference world events and player choices.
- Knowledge and secrets should filter agent observations and prompt context.
- Scene beat composer should produce structured inputs before narrative drafts.
- Daily episodes and suggestions should remain proposal-like before publication.

## Risks / Trade-offs

- Plot systems can overfit one genre. Mitigation: keep keys/config extensible while preserving galgame defaults.
- Secret leakage can break story logic. Mitigation: knowledge-state tests and diagnostics.
- Emotional state can become unstable. Mitigation: explicit decay/repair rules and audit evidence.

## Migration Plan

This proposal is planning-only. Future implementation should begin with passive records and diagnostics before generation or runtime use.

## Open Questions

- Whether route affinity should live near relationship graph or plot threads.
- How much event condition logic should be declarative in v0.7.
