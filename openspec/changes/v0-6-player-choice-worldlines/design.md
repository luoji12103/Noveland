## Context

The current system has worldlines and strict worldline-scoped multimodal records. It also has event logging, snapshots, replay, and memory isolation foundations. Player-facing choices are not yet first-class worldline inputs.

## Goals / Non-Goals

Goals:

- Represent players as in-world actors.
- Persist structured choices and consequences.
- Fork worldlines from snapshots/events.
- Ensure memory and multimodal state isolation across branches.
- Compare timelines for admin review.

Non-goals:

- Public launch gate changes.
- Real-time multiplayer collaboration.
- Full visual novel route UI.
- Cross-worldline visual inheritance.

## Decisions

- Choices append typed world events and may create consequence records.
- Forks must copy or reference baseline state without nullable worldline defaults.
- Memory operations must include worldline scope.
- Branch comparison should read state and events rather than mutate branches.

## Risks / Trade-offs

- Forking can duplicate too much data. Mitigation: explicit copy/reference rules per table.
- Consequences can become opaque. Mitigation: preview and evidence records.
- Memory contamination is high risk. Mitigation: tests at service and fixture levels.

## Migration Plan

This proposal is planning-only. Future implementation should start with player actor and choice records, then fork mechanics, then comparison surfaces.

## Open Questions

- Which multimodal records should be cloned during fork versus lazily recreated.
- Whether player actor should be world member linked or independent role agent.
