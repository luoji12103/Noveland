# Event and Snapshot Model

## Source of truth

The source of truth is the append-only world event log plus durable world snapshots.

Current materialized state is derived.

## Event model principles

- append-only
- world-scoped
- timestamped with both wall-clock and world-time context where relevant
- explicit actor identity
- explicit causation/correlation metadata where possible

## Snapshot principles

- snapshots are explicit, versioned, and world-scoped
- snapshot creation is an operational event
- snapshot metadata is stored in PostgreSQL
- snapshot payload may be stored in object storage

## Recovery model

- restore from latest valid snapshot
- replay incremental events after the snapshot point
- never mutate historical events in place

## Replay rules

- replay must be deterministic within documented limits
- replay behavior changes require regression tests
- event schema changes require migration strategy documentation

## v1 constraint

Do not implement fake replay by reconstructing from ad hoc chat logs.
