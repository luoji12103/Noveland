# Naming Conventions

## Domain vocabulary

Use these canonical domain terms:
- world
- scene
- agent
- calendar
- narrative
- event
- snapshot
- plugin
- provider
- adapter

Do not drift into synonyms for the same concept unless a new concept is truly different.

## File naming

Prefer domain + responsibility:
- `world_clock.py`
- `scene_visibility.py`
- `agent_registry.py`
- `event_store.py`

## Event naming

Use stable explicit names such as:
- `world.tick_advanced`
- `agent.observation_emitted`
- `calendar.entry_created`
- `narrative.chapter_generated`

## Prompt files

Prompt files should describe purpose in the filename:
- `bootstrap-primary.md`
- `bugfix-debug.md`
