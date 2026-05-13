# ComfyUI As Optional Provider Not Core Dependency

## Status

Accepted

## Context

ComfyUI can support image workflows, but Noveland must not require it for core world, conversation, media, or visual state.

## Decision

ComfyUI remains an optional provider adapter under `noveland.providers.adapters.comfyui`, routed by provider integration and capability.

## Consequences

Core media/image/visual services can run with fake/local/OpenAI-compatible providers. ComfyUI absence must not block local gate or core flows.

## Non-goals

- Bundling ComfyUI.
- Deploying workflow engines.
- Treating ComfyUI as a required runtime dependency.

## Related files/tests

- `backend/packages/providers/src/noveland/providers/adapters/comfyui.py`
- `backend/tests/test_comfyui_adapter.py`
- `backend/tests/test_api_images.py`
