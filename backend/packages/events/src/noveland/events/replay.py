from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from noveland.events.contracts import SNAPSHOT_EVENT_NAME, WorldSnapshotCreate, WorldSnapshotRecord
from noveland.events.event_store import WorldEventStore
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

WORLD_STATE_SCHEMA_VERSION = "world_state.v1"
CLOCK_ADVANCED_EVENT_NAME = "world.clock_advanced"


class ClockReplayState(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    current_world_time: datetime | None = None
    effective_world_time: datetime | None = None
    wall_time_anchor: datetime | None = None
    speed_multiplier: str | None = None
    revision: int | None = None
    last_event_id: uuid.UUID | None = None
    last_event_sequence: int | None = None


class WorldReplayState(BaseModel):
    model_config = ConfigDict(frozen=True)

    world_id: uuid.UUID
    schema_version: str = WORLD_STATE_SCHEMA_VERSION
    source_sequence: int = Field(ge=0)
    clock: ClockReplayState | None = None
    applied_event_count: int = Field(ge=0)
    unhandled_event_count: int = Field(ge=0)

    def snapshot_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"world_id"})


class WorldReplayService:
    def __init__(self, session: Session) -> None:
        self._event_store = WorldEventStore(session)

    def replay_state(self, world_id: uuid.UUID) -> WorldReplayState:
        latest_snapshot = self._event_store.latest_snapshot(world_id)
        state = _state_from_snapshot(world_id, latest_snapshot)
        events = self._event_store.list_events_after(world_id, state.source_sequence)

        source_sequence = state.source_sequence
        clock = state.clock
        applied_event_count = state.applied_event_count
        unhandled_event_count = state.unhandled_event_count

        for event in events:
            source_sequence = event.sequence
            if event.event_name == CLOCK_ADVANCED_EVENT_NAME:
                clock = _clock_from_event(event.id, event.sequence, event.payload)
                applied_event_count += 1
            elif event.event_name == SNAPSHOT_EVENT_NAME:
                continue
            else:
                unhandled_event_count += 1

        return WorldReplayState(
            world_id=world_id,
            source_sequence=source_sequence,
            clock=clock,
            applied_event_count=applied_event_count,
            unhandled_event_count=unhandled_event_count,
        )

    def create_snapshot(
        self,
        world_id: uuid.UUID,
        actor_ref: str,
        correlation_id: uuid.UUID | None = None,
    ) -> WorldSnapshotRecord:
        state = self.replay_state(world_id)
        return self._event_store.record_snapshot(
            WorldSnapshotCreate(
                world_id=world_id,
                covers_event_sequence=state.source_sequence,
                schema_version=WORLD_STATE_SCHEMA_VERSION,
                payload=state.snapshot_payload(),
                metadata={"source": "replay"},
                actor_ref=actor_ref,
                correlation_id=correlation_id,
            ),
        )

    def latest_snapshot(self, world_id: uuid.UUID) -> WorldSnapshotRecord | None:
        return self._event_store.latest_snapshot(world_id)


def _state_from_snapshot(
    world_id: uuid.UUID,
    snapshot: WorldSnapshotRecord | None,
) -> WorldReplayState:
    if (
        snapshot is None
        or snapshot.schema_version != WORLD_STATE_SCHEMA_VERSION
        or snapshot.payload is None
    ):
        return WorldReplayState(
            world_id=world_id,
            source_sequence=0,
            applied_event_count=0,
            unhandled_event_count=0,
        )

    payload = snapshot.payload
    clock_payload = payload.get("clock")
    clock = (
        ClockReplayState.model_validate(clock_payload)
        if isinstance(clock_payload, dict)
        else None
    )
    return WorldReplayState(
        world_id=world_id,
        source_sequence=snapshot.covers_event_sequence,
        clock=clock,
        applied_event_count=_nonnegative_int(payload.get("applied_event_count")),
        unhandled_event_count=_nonnegative_int(payload.get("unhandled_event_count")),
    )


def _clock_from_event(
    event_id: uuid.UUID,
    sequence: int,
    payload: dict[str, Any],
) -> ClockReplayState:
    return ClockReplayState(
        status=str(payload.get("status", "unknown")),
        current_world_time=_optional_datetime(payload.get("current_world_time")),
        effective_world_time=_optional_datetime(payload.get("effective_world_time")),
        wall_time_anchor=_optional_datetime(payload.get("wall_time_anchor")),
        speed_multiplier=None
        if payload.get("speed_multiplier") is None
        else str(payload.get("speed_multiplier")),
        revision=_optional_int(payload.get("revision")),
        last_event_id=event_id,
        last_event_sequence=sequence,
    )


def _optional_datetime(value: object) -> datetime | None:
    if value is None or not isinstance(value, str):
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int | str | bytes | bytearray):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _nonnegative_int(value: object) -> int:
    parsed = _optional_int(value)
    if parsed is None or parsed < 0:
        return 0
    return parsed
