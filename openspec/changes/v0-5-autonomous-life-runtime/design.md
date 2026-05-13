## Context

Current runtime loops support clocks, agents, conversations, memory jobs, and narrative artifacts. Asset generation preview/apply is admin-controlled and must not become hidden daemon spend. Future autonomous life should build on world events, schedules, and diagnostics.

## Goals / Non-Goals

Goals:

- Track character presence and daily routines.
- Queue and resolve offscreen events.
- Add GM agenda and event proposal records before committed events.
- Preserve replay, diagnostics, provider, media, and memory boundaries.

Non-goals:

- Hidden provider execution.
- Automatic media generation spend.
- Multi-machine scheduler architecture.
- Real-time player intervention.

## Decisions

- Runtime may propose world changes before committing them.
- Event resolution must be deterministic for the same input state.
- Memory writes remain explicit through `MemoryService`.
- Runtime diagnostics should explain skipped or blocked autonomous actions.

## Risks / Trade-offs

- Autonomy can create runaway events. Mitigation: budget, caps, proposal states, and loop guards.
- Offscreen events can contradict canon or relationships. Mitigation: require continuity and relationship context inputs.
- Replay can break if randomness is uncontrolled. Mitigation: deterministic seeds and event evidence.

## Migration Plan

This proposal is planning-only. Future implementation should start with admin-visible proposals and diagnostics before enabling runtime automation.

## Open Questions

- Whether GM agenda should be one table or separate agenda item/proposal tables.
- Which autonomous flows can run without provider calls in v0.5.
