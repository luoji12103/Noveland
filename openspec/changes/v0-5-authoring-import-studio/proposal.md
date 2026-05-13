# Proposal — v0.5 Authoring & Import Studio

## Why

Import galgame scripts, lore, character data, images, and audio into reviewable Noveland world proposals.

## What Changes

- Save v0.5 as an OpenSpec roadmap change with 9 independently implementable phases.
- Define phase goals, scope, non-goals, reused systems, acceptance criteria, stop conditions, validation, and deliverables.
- Add capability delta specs for each planned capability.
- Preserve Phase 13 architecture freeze boundaries while planning future implementation.

## Capabilities

### New Capabilities
- `authoring-source-registry`: Manage script, lore, character sheet, location sheet, image, and audio source assets.
- `script-parser-dialogue-extractor`: Parse dialogue, speaker, scene, choice, route, and event candidates.
- `character-relationship-extractor`: Extract characters, relationships, names, factions, identities, and emotional baselines.
- `world-bible-lore-extractor`: Extract locations, organizations, world rules, secrets, and knowledge boundaries.
- `canon-conflict-review`: Identify conflicting facts, duplicate characters, relationship contradictions, timeline conflicts, and OOC risk.
- `memory-migration-pipeline`: Convert source content into fact, episodic, relationship, preference, and style memory proposals.
- `asset-import-matching`: Import sprites, variants, backgrounds, CGs, and voice references and match them to characters or scenes.
- `import-preview-apply-workflow`: Unify import run lifecycle, proposal review, selective apply, rollback hints, and audit records.
- `authoring-regression-fixture`: Create a small galgame import fixture for regression of scripts, characters, relationships, assets, and memory migration.

### Modified Capabilities
- None.

## Impact

- Future backend, Web, docs, and test work will be driven by this change's `phase-plan.md`, `tasks.md`, and capability specs.
- Current implementation behavior is unchanged by this roadmap skeleton.
- Future implementation phases must run targeted tests and the full local gate before merge.
