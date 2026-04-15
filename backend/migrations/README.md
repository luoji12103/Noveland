# Migrations

Alembic is the canonical schema migration entrypoint for the backend.

```sh
uv run alembic upgrade head
```

The initial migration defines only the core persistence baseline. Event replay, world clock state, plugin registry data, sessions, calendar entries, memory vectors, and narrative artifacts belong to later migrations.
