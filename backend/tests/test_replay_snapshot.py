from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import cast

from noveland.auth.models import User
from noveland.events import (
    CLOCK_ADVANCED_EVENT_NAME,
    WORLD_STATE_SCHEMA_VERSION,
    WorldEventAppend,
    WorldEventStore,
    WorldReplayService,
    WorldSnapshotCreate,
)
from noveland.events.models import WorldEventModel, WorldSnapshotModel
from noveland.worlds.models import World
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_replay_state_starts_empty_without_snapshot_or_events() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id, "empty-replay")

    with Session(engine) as session:
        state = WorldReplayService(session).replay_state(world_id)

    assert state.schema_version == WORLD_STATE_SCHEMA_VERSION
    assert state.source_sequence == 0
    assert state.clock is None
    assert state.applied_event_count == 0
    assert state.unhandled_event_count == 0


def test_replay_applies_latest_snapshot_and_incremental_events() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id, "snapshot-replay")

    with Session(engine) as session:
        event_store = WorldEventStore(session)
        first_event = event_store.append_event(
            _clock_event(world_id, revision=1, sequence_time="2030-01-01T00:00:00+00:00"),
        )
        event_store.record_snapshot(
            WorldSnapshotCreate(
                world_id=world_id,
                covers_event_sequence=first_event.sequence,
                schema_version=WORLD_STATE_SCHEMA_VERSION,
                payload={
                    "schema_version": WORLD_STATE_SCHEMA_VERSION,
                    "source_sequence": first_event.sequence,
                    "clock": {
                        "status": "running",
                        "current_world_time": "2030-01-01T00:00:00Z",
                        "effective_world_time": "2030-01-01T00:00:00Z",
                        "wall_time_anchor": "2026-04-17T12:00:00Z",
                        "speed_multiplier": "1",
                        "revision": 1,
                        "last_event_id": str(first_event.id),
                        "last_event_sequence": first_event.sequence,
                    },
                    "applied_event_count": 1,
                    "unhandled_event_count": 0,
                },
                actor_ref="system:test",
            ),
        )
        second_event = event_store.append_event(
            _clock_event(world_id, revision=2, sequence_time="2030-01-01T00:01:00+00:00"),
        )
        event_store.append_event(
            WorldEventAppend(
                world_id=world_id,
                event_name="world.unknown_event",
                payload={},
                wall_time=datetime(2026, 4, 17, 12, 2, tzinfo=UTC),
                actor_ref="system:test",
            ),
        )
        session.commit()

    with Session(engine) as session:
        state = WorldReplayService(session).replay_state(world_id)

    assert state.source_sequence == 4
    assert state.clock is not None
    assert state.clock.revision == 2
    assert state.clock.last_event_id == second_event.id
    assert state.applied_event_count == 2
    assert state.unhandled_event_count == 1


def test_replay_service_creates_inline_snapshot_from_current_state() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id, "create-snapshot")

    with Session(engine) as session:
        WorldEventStore(session).append_event(
            _clock_event(world_id, revision=1, sequence_time="2030-01-01T00:00:00+00:00"),
        )
        session.commit()

    with Session(engine) as session:
        snapshot = WorldReplayService(session).create_snapshot(world_id, "user:test")
        session.commit()

    assert snapshot.schema_version == WORLD_STATE_SCHEMA_VERSION
    assert snapshot.covers_event_sequence == 1
    assert snapshot.payload is not None
    assert snapshot.payload["source_sequence"] == 1
    assert snapshot.payload["applied_event_count"] == 1


def _clock_event(
    world_id: uuid.UUID,
    *,
    revision: int,
    sequence_time: str,
) -> WorldEventAppend:
    return WorldEventAppend(
        world_id=world_id,
        event_name=CLOCK_ADVANCED_EVENT_NAME,
        payload={
            "status": "running",
            "current_world_time": sequence_time,
            "effective_world_time": sequence_time,
            "wall_time_anchor": "2026-04-17T12:00:00+00:00",
            "speed_multiplier": "1",
            "revision": revision,
        },
        wall_time=datetime(2026, 4, 17, 12, revision, tzinfo=UTC),
        world_time=datetime(2030, 1, 1, 0, revision - 1, tzinfo=UTC),
        actor_ref="system:test",
    )


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        cast(Table, User.__table__),
        cast(Table, World.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, WorldSnapshotModel.__table__),
    ):
        table.create(engine)
    return engine


def _seed_user(engine: Engine) -> uuid.UUID:
    user_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(User(id=user_id, email=f"{user_id}@example.test", display_name="User"))
        session.commit()
    return user_id


def _seed_world(engine: Engine, user_id: uuid.UUID, slug: str) -> uuid.UUID:
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug=slug,
                name=slug.replace("-", " ").title(),
                rules_config={},
            ),
        )
        session.commit()
    return world_id
