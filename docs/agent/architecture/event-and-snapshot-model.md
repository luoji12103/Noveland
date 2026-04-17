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

## Implemented baseline

- `world_events` is the canonical append-only world event log table.
- `world_events.sequence` is allocated per world and is unique within that world.
- `world_snapshots` stores snapshot metadata and links each snapshot to the `world.snapshot_created` event that created it.
- Snapshot payloads may be inline JSONB or referenced by `payload_uri`; this baseline does not write object storage objects.
- `noveland.events.WorldEventStore` provides append, list-after, record-snapshot, and latest-valid-snapshot helpers.
- `noveland.events.publisher` defines world event envelopes, an in-memory test publisher, and a NATS publisher.
- Runtime ticks append `world.clock_advanced` events for running clocks and publish them to `noveland.world.{world_id}.events`.
- PostgreSQL remains canonical; NATS is only the broadcast layer.
- `noveland.events.WorldReplayService` reconstructs a diagnostic `world_state.v1` view from the latest valid snapshot plus incremental events.
- Replay currently understands `world.clock_advanced`, ignores `world.snapshot_created`, and counts unknown event names as unhandled instead of failing.
- The API exposes replay state, latest valid snapshot, and admin-only inline snapshot creation under `/worlds/{world_id}`.
- The Web dashboard includes a replay/snapshot panel for the selected world.

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

The current baseline intentionally does not implement destructive restore, infinite runtime loops, scheduler integration, agent behavior, permission-policy expansion, object-storage snapshot writes, or narrative-specific event semantics.
