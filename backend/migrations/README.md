# Migrations

Alembic is the canonical schema migration entrypoint for the backend.

```sh
uv run alembic upgrade head
```

The initial migration defines only the core persistence baseline. The second migration adds world clock state and transition audit tables. The third migration adds the append-only world event log and snapshot metadata baseline. The fourth migration adds local password credentials, opaque auth sessions, and platform role assignments. The fifth migration adds agent calendar entries and world schedule rules. The sixth migration adds local pgvector-backed agent memory. The seventh migration adds provider profiles, runtime control state, agent run records, and narrative artifacts. The eighth migration adds runtime diagnostics. The ninth migration adds provider reliability and test-call health fields. The tenth migration adds agent persona and filtered observation records.
