# Conversation Turn Presentation API Only First

## Status

Accepted

## Context

Dialogue turns need structured visual/speech presentation metadata before UI rendering can be designed safely.

## Decision

`conversation_turn_presentations` is backend/API-only canonical state for emotion, sprite, voice, background, composite, TTS asset, and transcript references.

## Consequences

Rendering orchestration can be tested through APIs and services. Web preview/playback can be added later against stable contracts.

## Non-goals

- Web preview panel.
- Audio player UI.
- Mutating turn text during render or STT.
- Automatic memory write from STT.

## Related files/tests

- `backend/packages/conversations/src/noveland/conversations/presentation.py`
- `backend/services/api/src/noveland/services/api/conversation_presentations.py`
- `backend/tests/test_conversation_presentation_service.py`
- `backend/tests/test_api_conversation_presentations.py`
