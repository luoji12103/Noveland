# Sample World Release Package

The v0.8 sample world release package is a deterministic backend regression artifact. It maps the Phase 13 multimodal sample-world fixture into a safe world package manifest and verifies import preview/apply behavior through the existing world packaging service.

## Scope

- Source fixture: `backend/tests/fixtures/multimodal_sample_world.py`
- Release package helper: `backend/tests/fixtures/sample_world_release_package.py`
- Test entrypoint: `backend/tests/test_sample_world_release_package.py`
- Package key: `phase13-sample-world-release`
- Fixture key: `phase13_multimodal_sample_world`

## Included Shape

- One world and one primary worldline.
- One scene.
- Media manifest entries for background, neutral/happy/sad sprites, TTS audio, STT source audio, and composite image.
- Explicit rights metadata for every media manifest entry.
- Reader-visible manifest entries for playback and scene-view media.
- Fixture linkage and expected record counts.
- Multimodal diagnostics evidence by eval key and status only.

## Guardrails

- No production seed framework.
- No real provider calls.
- No media byte copy during package import apply.
- No public marketplace behavior.
- No storage URI, filesystem path, bytes, base64, raw prompt, raw output, prompt snapshot internals, or resolved secrets in manifests or preview/apply responses.

## Test Command

```bash
cd backend && uv run pytest tests/test_sample_world_release_package.py
```
