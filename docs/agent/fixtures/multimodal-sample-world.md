# Multimodal Sample World Fixture

The multimodal sample world is a backend regression fixture, not a content-quality fixture. It verifies that Phase 3-12 contracts still compose correctly.

## Shape

- One world.
- One primary worldline.
- Two role agents.
- One scene.
- One conversation session and one agent turn.
- One scene background media asset/object.
- One character sprite set for the speaking agent.
- Three sprite variants: `neutral`, `happy`, and `sad`.
- One voice profile and one default agent voice binding.
- One TTS media asset/object.
- One STT source audio media asset/object and one transcript.
- One composite image media asset/object.
- One conversation turn presentation referencing sprite, background, voice, audio, composite, and transcript records.
- One asset generation policy, preview run, apply run, proposal, and queued media job.
- One model invocation and one prompt snapshot with redacted request evidence.
- One multimodal eval run input state that can pass diagnostics.

## Regression Goals

- Prove fixture records share the same world.
- Prove worldline-scoped records use the primary worldline.
- Prove visual binding records never use nullable worldline defaults.
- Prove sprite/background resolvers return deterministic results.
- Prove media objects exist and checksums validate.
- Prove provider secret values are not present in safe provider outputs or health metadata.
- Prove member/reader routes do not expose prompt snapshots.
- Prove STT transcript creation does not enqueue memory writes.
- Prove asset generation remains admin-controlled.
- Prove `world_events.payload` does not contain storage URIs, filesystem paths, bytes, base64, raw prompts, or raw outputs.
- Prove multimodal diagnostics pass.

## Test Entrypoint

Run:

```bash
cd backend && uv run pytest tests/test_multimodal_sample_world_regression.py
```

The fixture helper lives at:

- `backend/tests/fixtures/multimodal_sample_world.py`

The fixture is intentionally local to tests. It must not become a production seed framework.
