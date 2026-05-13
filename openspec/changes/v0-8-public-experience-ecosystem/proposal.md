# Proposal — v0.8 Public Experience & Ecosystem

## Why

Expose safe reader/player experiences, worldline navigation, media playback, world packaging, and plugin/provider packaging after production boundaries are ready.

## What Changes

- Save v0.8 as an OpenSpec roadmap change with 11 independently implementable phases.
- Define phase goals, scope, non-goals, reused systems, acceptance criteria, stop conditions, validation, and deliverables.
- Add capability delta specs for each planned capability.
- Preserve Phase 13 architecture freeze boundaries while planning future implementation.

## Capabilities

### New Capabilities
- `reader-media-delivery`: Provide reader-visible media delivery without leaking storage_uri or filesystem paths.
- `conversation-playback-ui`: Render image, sprite, background, voice, subtitles, and turn presentation playback.
- `player-interaction-ui`: Expose choices, interventions, journal, notifications, and route feedback to players.
- `worldline-browser`: Support branch viewing, rollback/switch review, and worldline comparison.
- `scene-view-galgame-view`: Provide a basic galgame reading surface with scene background, sprites, dialogue, audio, and basic transitions.
- `player-privacy-data-controls`: Support export/delete requests, player profile visibility, and conversation data controls.
- `world-packaging`: Define world bundle manifest, media bundle manifest, import, and export.
- `plugin-provider-package-contract`: Define adapter packaging, capability schema, safety review, and config export without secrets.
- `sample-world-release-package`: Package a complete demonstrable sample world with content, media bundle, and regression fixture linkage.
- `moderation-incident-workflow`: Support reports, rollback, disable world/provider, and incident records.
- `public-launch-gate`: Define public launch readiness checklist separate from internal production readiness.

### Modified Capabilities
- None.

## Impact

- Future backend, Web, docs, and test work will be driven by this change's `phase-plan.md`, `tasks.md`, and capability specs.
- Current implementation behavior is unchanged by this roadmap skeleton.
- Future implementation phases must run targeted tests and the full local gate before merge.
