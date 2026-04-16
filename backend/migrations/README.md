# Migrations

Alembic is the canonical schema migration entrypoint for the backend.

```sh
uv run alembic upgrade head
```

The initial migration defines only the core persistence baseline. The second migration adds world clock state and transition audit tables. The third migration adds the append-only world event log and snapshot metadata baseline. The fourth migration adds local password credentials, opaque auth sessions, and platform role assignments. Event replay, plugin registry data, calendar entries, memory vectors, and narrative artifacts belong to later migrations.
