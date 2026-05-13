# Worldline-First Multimodal State

## Status

Accepted

## Context

Visual, speech, media, invocation, conversation, and asset-generation state can diverge after forks. Nullable defaults would make fork behavior ambiguous.

## Decision

Worldline-scoped multimodal state must treat `world_id` and `worldline_id` as first-class identifiers. Strict visual bindings require non-null `worldline_id`.

## Consequences

Fork-specific state is explicit. Cross-worldline inheritance must be designed later instead of inferred from nullable records.

## Non-goals

- Historical backfill.
- Cross-worldline visual inheritance.
- Dual default/override visual tables.

## Related files/tests

- `backend/packages/visual/src/noveland/visual/models.py`
- `backend/packages/conversations/src/noveland/conversations/models.py`
- `backend/tests/test_visual_service.py`
- `backend/tests/test_conversation_presentation_service.py`
