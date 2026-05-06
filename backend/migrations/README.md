# Migrations

Alembic is the canonical schema migration entrypoint for the backend.

```sh
uv run alembic upgrade head
```

Migration versions are intentionally linear. Each version module must expose both `upgrade()` and `downgrade()`, and `tests/test_alembic_config.py` verifies the current single head.

Current sequence:

- `20260415_0001` through `20260417_0010`: core schema, clock/events/snapshots, auth sessions, calendar, memory, runtime, diagnostics, provider reliability, and persona/observations.
- `20260419_0011` through `20260422_0015`: conversation workspace, conversation policies, narrative writer, composition presets, and plugin runtime wiring.
- `20260423_0016` through `20260423_0018`: Mem0 OSS memory foundation, memory context integration, and memory profile forget/eval ops.
- `20260503_0019` through `20260505_0025`: observation traceability, narrative publications, agent preset versioning, plugin diagnostics, living-world character foundation, autonomous systems, and GM/choice/worldline state.
