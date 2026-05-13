## Context

The current system already has worlds, worldlines, agents, scenes, schedules, events, media, and multimodal presentation state. It does not yet make the richer galgame living-world model explicit enough for organizations, durable relationships, canon boundaries, or location graph behavior.

## Goals / Non-Goals

Goals:

- Establish normalized or well-scoped records for world bible, continuity, character profiles, relationships, organizations, memberships, faction progress, and location graph semantics.
- Preserve worldline isolation and existing event/media/provider boundaries.
- Prefer extending current world, agent, scene, event, memory, and Web surfaces.

Non-goals:

- Runtime autonomous GM behavior.
- Player choice/worldline branching UI.
- New providers, media delivery, or streaming.
- Replacing existing world/event/agent models.

## Decisions

- Use existing `worlds`, `agents`, `events`, `calendar`, and `memory` package boundaries as integration points.
- Treat relationship, organization, and location changes as worldline-scoped state with typed event evidence.
- Keep memory backend access behind `MemoryService`.
- Keep Web work incremental and admin-focused if implementation later adds UI.

## Risks / Trade-offs

- Over-normalization can slow roadmap delivery. Mitigation: add only records needed by explicit scenarios.
- Relationship and organization semantics can become vague. Mitigation: require deterministic update and audit scenarios.
- Cross-worldline leakage is easy in graph data. Mitigation: require worldline scope on state and tests.

## Migration Plan

This proposal is planning-only. A future implementation would add migrations in small capability slices and update tests before widening API use.

## Open Questions

- Whether relationship edges should be pairwise only at first or allow group/organization targets.
- Whether location graph should extend scenes directly or use a dedicated graph table.
