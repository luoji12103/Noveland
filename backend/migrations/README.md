# Migrations

Alembic is the canonical schema migration entrypoint for the backend.

```sh
uv run alembic upgrade head
```

The initial migration defines only the core persistence baseline. The second migration adds world clock state and transition audit tables. Event replay, snapshots, plugin registry data, sessions, calendar entries, memory vectors, and narrative artifacts belong to later migrations.
