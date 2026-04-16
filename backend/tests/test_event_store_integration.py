from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from noveland.events import WorldEventAppend, WorldEventStore, WorldSnapshotCreate
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

TEST_DATABASE_URL = os.environ.get("NOVELAND_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="NOVELAND_TEST_DATABASE_URL is not set",
)


@pytest.fixture()
def engine() -> Iterator[Engine]:
    if TEST_DATABASE_URL is None:
        pytest.skip("NOVELAND_TEST_DATABASE_URL is not set")
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session
        session.rollback()


def test_world_event_store_appends_lists_and_records_snapshots(session: Session) -> None:
    world_id = _insert_world(session)
    store = WorldEventStore(session)
    correlation_id = uuid.uuid4()
    wall_time = datetime(2026, 4, 16, 10, 0, tzinfo=UTC)

    first_event = store.append_event(
        WorldEventAppend(
            world_id=world_id,
            event_name="agent.observation_emitted",
            payload={"message": "hello"},
            wall_time=wall_time,
            actor_ref="agent:test",
            correlation_id=correlation_id,
        ),
    )
    second_event = store.append_event(
        WorldEventAppend(
            world_id=world_id,
            event_name="narrative.chapter_generated",
            payload={"chapter": 1},
            wall_time=wall_time,
            world_time=datetime(2180, 1, 1, 8, 0, tzinfo=UTC),
            actor_ref="narrative:test",
            causation_event_id=first_event.id,
            correlation_id=correlation_id,
        ),
    )

    assert first_event.sequence == 1
    assert second_event.sequence == 2
    assert store.list_events_after(world_id, 0) == [first_event, second_event]
    assert store.list_events_after(world_id, 1) == [second_event]

    snapshot = store.record_snapshot(
        WorldSnapshotCreate(
            world_id=world_id,
            covers_event_sequence=second_event.sequence,
            schema_version="integration-test.v1",
            payload={"state": "snapshotted"},
            metadata={"source": "integration-test"},
            actor_ref="runtime:test",
            correlation_id=correlation_id,
        ),
    )
    snapshot_event = store.list_events_after(world_id, 2)[0]
    latest_snapshot = store.latest_snapshot(world_id)

    assert snapshot.covers_event_sequence == 2
    assert snapshot.created_by_event_id == snapshot_event.id
    assert snapshot_event.sequence == 3
    assert snapshot_event.event_name == "world.snapshot_created"
    assert snapshot_event.actor_ref == "runtime:test"
    assert latest_snapshot is not None
    assert latest_snapshot.id == snapshot.id


def _insert_world(session: Session) -> uuid.UUID:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
    session.execute(
        text(
            """
            INSERT INTO users (id, email, display_name)
            VALUES (CAST(:user_id AS uuid), :email, :display_name)
            """,
        ),
        {
            "user_id": str(user_id),
            "email": f"{user_id}@example.test",
            "display_name": "Integration User",
        },
    )
    session.execute(
        text(
            """
            INSERT INTO worlds (id, owner_user_id, slug, name)
            VALUES (
                CAST(:world_id AS uuid),
                CAST(:owner_user_id AS uuid),
                :slug,
                :name
            )
            """,
        ),
        {
            "world_id": str(world_id),
            "owner_user_id": str(user_id),
            "slug": f"world-{world_id}",
            "name": "Integration World",
        },
    )
    return world_id
