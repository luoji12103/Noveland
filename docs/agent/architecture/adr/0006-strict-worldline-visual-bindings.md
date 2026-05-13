# Strict Worldline Visual Bindings

## Status

Accepted

## Context

Sprite/background selection affects presentation state and must not accidentally bleed across forks.

## Decision

Character sprite sets, sprite variants, and scene background profiles require non-null `worldline_id`. They point to existing media assets and never copy storage URI values.

## Consequences

Resolvers are deterministic within one worldline. Shared bytes are possible through media asset reuse, but binding state remains fork-specific.

## Non-goals

- Nullable global visual defaults.
- Dual override tables.
- Web visual manager UI.

## Related files/tests

- `backend/packages/visual/src/noveland/visual/models.py`
- `backend/packages/visual/src/noveland/visual/resolver.py`
- `backend/tests/test_visual_service.py`
- `backend/tests/test_api_visual.py`
