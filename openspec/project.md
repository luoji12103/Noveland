# Noveland OpenSpec Project

## Purpose

Noveland is a persistent galgame-style living world system. The backend models worlds, worldlines, agents, conversations, events, memory, narrative artifacts, media assets, provider executions, visual/speech presentation state, and regression diagnostics. The Web app currently provides world, agent, conversation, narrative, reader, runtime, provider, preset, and memory administration surfaces.

## Current Source Of Truth

The `openspec/specs/` directory describes behavior that exists on current `main`. It is seeded from:

- `docs/agent/architecture/current-system-contracts.md`
- `docs/agent/architecture/api-contract-inventory.md`
- `docs/agent/architecture/data-model-inventory.md`
- `docs/agent/architecture/adr/`
- `docs/agent/fixtures/multimodal-sample-world.md`
- Backend packages, API routers, migrations, and tests.
- Web routes, proxy clients, features, and tests.

Current specs must not contain future roadmap work. Future plans belong under `openspec/changes/`.

## Conventions

- Backend package boundaries are authoritative: provider logic belongs under `noveland.providers`; media logic under `noveland.media`; speech logic under `noveland.speech`; visual bindings under `noveland.visual`; multimodal diagnostics under `noveland.multimodal_eval`.
- Product modules must reuse existing services instead of calling external provider SDKs, storage backends, or memory backends directly.
- `world_id` and `worldline_id` are first-class parameters for worldline-scoped state.
- Provider calls must write `model_invocations` and `prompt_snapshots`.
- Image/audio files must write `media_assets`, `media_objects`, `media_jobs`, and references as appropriate.
- `world_events.payload` must not store storage URIs, filesystem paths, bytes, base64, raw prompts, raw model outputs, or provider secrets.
- OpenSpec change specs must use `## ADDED Requirements`, `## MODIFIED Requirements`, `## REMOVED Requirements`, or `## RENAMED Requirements`.
- Main specs must use `## Purpose`, `## Requirements`, and `## Non-goals`.

## Validation

Use these checks for OpenSpec-only updates:

```bash
openspec validate --specs --strict
openspec validate --changes --strict
git diff --check
```

Backend and Web gates are not required for documentation-only OpenSpec roadmap updates unless implementation files change.
