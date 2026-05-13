# Proposal — v0.6 Runtime Narrative Quality

## Why

Improve multi-agent runtime, dialogue, GM proposals, narrative continuity, pacing, route quality, and evaluation.

## What Changes

- Save v0.6 as an OpenSpec roadmap change with 10 independently implementable phases.
- Define phase goals, scope, non-goals, reused systems, acceptance criteria, stop conditions, validation, and deliverables.
- Add capability delta specs for each planned capability.
- Preserve Phase 13 architecture freeze boundaries while planning future implementation.

## Capabilities

### New Capabilities
- `runtime-context-contract-v2`: Distinguish agent, conversation, GM, narrative, and eval context contracts.
- `provider-backed-gm-proposal`: Use providers to generate GM proposals without directly mutating world state.
- `dialogue-style-ooc-review`: Check character speech style, relationship consistency, and out-of-character risk.
- `emotion-sprite-voice-alignment`: Check and suggest fixes for emotion tag, sprite variant, and voice style alignment.
- `narrative-writer-v2`: Generate chapters from world events and conversation turns with worldline, visibility, and reader-safe filtering.
- `continuity-review-v2`: Check causality, secret leakage, timeline conflicts, relationship jumps, and route conflicts.
- `runtime-pacing-controller`: Control world evolution speed, reading speed, lookahead, offscreen compression, and asset generation budget.
- `route-relationship-progression-quality`: Review route progression, affection/conflict/repair, and relationship state changes.
- `long-run-living-world-simulation-eval`: Run multi-day/multi-turn simulations to detect character drift, narrative breaks, and world state pollution.
- `narrative-quality-dashboard-api`: Expose quality metrics, blockers, and repair recommendations to admins.

### Modified Capabilities
- None.

## Impact

- Future backend, Web, docs, and test work will be driven by this change's `phase-plan.md`, `tasks.md`, and capability specs.
- Current implementation behavior is unchanged by this roadmap skeleton.
- Future implementation phases must run targeted tests and the full local gate before merge.
