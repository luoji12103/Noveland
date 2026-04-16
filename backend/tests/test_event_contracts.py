from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import cast

import pytest
from noveland.events import (
    EventValidationError,
    SnapshotValidationError,
    WorldEventAppend,
    WorldEventStore,
    WorldSnapshotCreate,
)
from pydantic import ValidationError
from sqlalchemy.orm import Session


def test_event_append_contract_accepts_stable_event_shape() -> None:
    world_id = uuid.uuid4()
    correlation_id = uuid.uuid4()
    event = WorldEventAppend(
        world_id=world_id,
        event_name="agent.observation_emitted",
        payload={"message": "hello"},
        wall_time=datetime(2026, 4, 16, 10, 0, tzinfo=UTC),
        world_time=datetime(2180, 1, 1, 8, 0, tzinfo=UTC),
        actor_ref="agent:test",
        correlation_id=correlation_id,
    )

    assert event.world_id == world_id
    assert event.event_name == "agent.observation_emitted"
    assert event.wall_time.tzinfo is UTC
    assert event.world_time is not None
    assert event.world_time.tzinfo is UTC
    assert event.correlation_id == correlation_id


def test_event_append_rejects_non_dotted_event_name() -> None:
    with pytest.raises(ValidationError):
        WorldEventAppend(
            world_id=uuid.uuid4(),
            event_name="WorldBad",
            wall_time=datetime(2026, 4, 16, 10, 0, tzinfo=UTC),
            actor_ref="user:test",
        )


def test_event_append_rejects_naive_wall_time() -> None:
    with pytest.raises(ValidationError):
        WorldEventAppend(
            world_id=uuid.uuid4(),
            event_name="world.tick_advanced",
            wall_time=datetime(2026, 4, 16, 10, 0),
            actor_ref="runtime:test",
        )


def test_event_append_rejects_non_json_payload() -> None:
    with pytest.raises(ValidationError):
        WorldEventAppend(
            world_id=uuid.uuid4(),
            event_name="world.tick_advanced",
            payload={"not_json": object()},
            wall_time=datetime(2026, 4, 16, 10, 0, tzinfo=UTC),
            actor_ref="runtime:test",
        )


def test_event_store_wraps_invalid_event_input_in_typed_error() -> None:
    store = WorldEventStore(cast(Session, object()))

    with pytest.raises(EventValidationError):
        store.append_event(
            {
                "world_id": str(uuid.uuid4()),
                "event_name": "BadName",
                "wall_time": datetime(2026, 4, 16, 10, 0, tzinfo=UTC),
                "actor_ref": "user:test",
            },
        )


def test_snapshot_contract_requires_payload_or_uri() -> None:
    with pytest.raises(ValidationError):
        WorldSnapshotCreate(
            world_id=uuid.uuid4(),
            covers_event_sequence=1,
            schema_version="test.v1",
            actor_ref="runtime:test",
        )


def test_snapshot_contract_accepts_inline_payload() -> None:
    snapshot = WorldSnapshotCreate(
        world_id=uuid.uuid4(),
        covers_event_sequence=1,
        schema_version="test.v1",
        payload={"state": "ready"},
        metadata={"source": "unit-test"},
        actor_ref="runtime:test",
    )

    assert snapshot.payload == {"state": "ready"}
    assert snapshot.payload_uri is None
    assert snapshot.metadata == {"source": "unit-test"}


def test_event_store_wraps_invalid_snapshot_input_in_typed_error() -> None:
    store = WorldEventStore(cast(Session, object()))

    with pytest.raises(SnapshotValidationError):
        store.record_snapshot(
            {
                "world_id": str(uuid.uuid4()),
                "covers_event_sequence": 1,
                "schema_version": "test.v1",
                "actor_ref": "runtime:test",
            },
        )
