from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from noveland.core.settings import AppSettings, load_settings
from noveland.events.contracts import (
    SNAPSHOT_EVENT_NAME,
    WorldEventRecord,
    WorldSnapshotCreate,
    WorldSnapshotRecord,
)
from noveland.events.event_store import WorldEventStore
from noveland.storage import LocalObjectStorage, ObjectStorageError
from pydantic import BaseModel, ConfigDict, Field, ValidationError
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
    worldline_id: uuid.UUID | None = None
    schema_version: str = WORLD_STATE_SCHEMA_VERSION
    source_sequence: int = Field(ge=0)
    clock: ClockReplayState | None = None
    applied_event_count: int = Field(ge=0)
    unhandled_event_count: int = Field(ge=0)

    def snapshot_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"world_id"})


class SnapshotIntegrityStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


class WorldSnapshotIntegrityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    world_id: uuid.UUID
    status: SnapshotIntegrityStatus
    latest_event_sequence: int = Field(ge=0)
    latest_snapshot_id: uuid.UUID | None = None
    covers_event_sequence: int | None = Field(default=None, ge=0)
    schema_version: str | None = None
    payload_location: str | None = None
    event_gap: int | None = Field(default=None, ge=0)
    issues: list[str] = Field(default_factory=list)


class WorldReplayService:
    def __init__(self, session: Session, settings: AppSettings | None = None) -> None:
        self._event_store = WorldEventStore(session)
        self._settings = settings or load_settings()
        self._object_storage = LocalObjectStorage(self._settings.object_storage_root)

    def replay_state(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None = None,
    ) -> WorldReplayState:
        resolved_worldline_id = (
            self._event_store.primary_worldline_id(world_id)
            if worldline_id is None
            else worldline_id
        )
        latest_snapshot = self._event_store.latest_snapshot(world_id, resolved_worldline_id)
        state = self._state_from_snapshot(world_id, resolved_worldline_id, latest_snapshot)
        events = self._event_store.list_events_after(
            world_id,
            state.source_sequence,
            worldline_id=resolved_worldline_id,
        )

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
            worldline_id=resolved_worldline_id,
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
        worldline_id: uuid.UUID | None = None,
    ) -> WorldSnapshotRecord:
        state = self.replay_state(world_id, worldline_id)
        resolved_worldline_id = state.worldline_id
        if resolved_worldline_id is None:
            resolved_worldline_id = self._event_store.primary_worldline_id(world_id)
        object_record = self._object_storage.write_json(
            _snapshot_object_key(world_id, resolved_worldline_id, state.source_sequence),
            state.snapshot_payload(),
        )
        return self._event_store.record_snapshot(
            WorldSnapshotCreate(
                world_id=world_id,
                worldline_id=resolved_worldline_id,
                covers_event_sequence=state.source_sequence,
                schema_version=WORLD_STATE_SCHEMA_VERSION,
                payload=None,
                payload_uri=object_record.uri,
                metadata={
                    "source": "replay",
                    "storage": "local_object",
                    "payload_size_bytes": object_record.size_bytes,
                },
                actor_ref=actor_ref,
                correlation_id=correlation_id,
            ),
        )

    def latest_snapshot(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None = None,
    ) -> WorldSnapshotRecord | None:
        return self._event_store.latest_snapshot(world_id, worldline_id)

    def snapshot_integrity(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None = None,
    ) -> WorldSnapshotIntegrityReport:
        resolved_worldline_id = (
            self._event_store.primary_worldline_id(world_id)
            if worldline_id is None
            else worldline_id
        )
        latest_event_sequence = self._event_store.latest_event_sequence(
            world_id,
            resolved_worldline_id,
        )
        latest_snapshot = self._event_store.latest_snapshot(world_id, resolved_worldline_id)
        if latest_snapshot is None:
            return WorldSnapshotIntegrityReport(
                world_id=world_id,
                status=SnapshotIntegrityStatus.WARNING,
                latest_event_sequence=latest_event_sequence,
                issues=["No valid snapshot exists."],
            )

        issues: list[str] = []
        if latest_snapshot.schema_version != WORLD_STATE_SCHEMA_VERSION:
            issues.append(
                f"Snapshot schema version `{latest_snapshot.schema_version}` "
                f"does not match `{WORLD_STATE_SCHEMA_VERSION}`.",
            )
        payload = self._snapshot_payload(latest_snapshot)
        if payload is None:
            issues.append("Snapshot payload is missing.")
        elif not _snapshot_payload_is_valid(world_id, latest_snapshot, payload):
            issues.append("Snapshot payload is not a valid replay payload.")
        if latest_snapshot.covers_event_sequence > latest_event_sequence:
            issues.append("Snapshot covers a future event sequence.")

        event_gap = _replay_relevant_event_gap(
            latest_snapshot.covers_event_sequence,
            self._event_store.list_events_after(
                world_id,
                latest_snapshot.covers_event_sequence,
                worldline_id=resolved_worldline_id,
            ),
        )
        if any(_is_error_issue(issue) for issue in issues):
            integrity_status = SnapshotIntegrityStatus.ERROR
        elif event_gap > 0:
            integrity_status = SnapshotIntegrityStatus.WARNING
            issues.append("Snapshot is stale relative to the latest event.")
        else:
            integrity_status = SnapshotIntegrityStatus.OK

        return WorldSnapshotIntegrityReport(
            world_id=world_id,
            status=integrity_status,
            latest_event_sequence=latest_event_sequence,
            latest_snapshot_id=latest_snapshot.id,
            covers_event_sequence=latest_snapshot.covers_event_sequence,
            schema_version=latest_snapshot.schema_version,
            payload_location=_payload_location(latest_snapshot),
            event_gap=event_gap,
            issues=issues,
        )

    def _snapshot_payload(self, snapshot: WorldSnapshotRecord) -> dict[str, Any] | None:
        if snapshot.payload is not None:
            return snapshot.payload
        if snapshot.payload_uri is None:
            return None
        try:
            return self._object_storage.read_json(snapshot.payload_uri)
        except ObjectStorageError:
            return None

    def _state_from_snapshot(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        snapshot: WorldSnapshotRecord | None,
    ) -> WorldReplayState:
        if snapshot is None or snapshot.schema_version != WORLD_STATE_SCHEMA_VERSION:
            return WorldReplayState(
                world_id=world_id,
                worldline_id=worldline_id,
                source_sequence=0,
                applied_event_count=0,
                unhandled_event_count=0,
            )

        payload = self._snapshot_payload(snapshot)
        if payload is None:
            return WorldReplayState(
                world_id=world_id,
                worldline_id=worldline_id,
                source_sequence=0,
                applied_event_count=0,
                unhandled_event_count=0,
            )
        clock_payload = payload.get("clock")
        clock = (
            ClockReplayState.model_validate(clock_payload)
            if isinstance(clock_payload, dict)
            else None
        )
        return WorldReplayState(
            world_id=world_id,
            worldline_id=worldline_id,
            source_sequence=snapshot.covers_event_sequence,
            clock=clock,
            applied_event_count=_nonnegative_int(payload.get("applied_event_count")),
            unhandled_event_count=_nonnegative_int(payload.get("unhandled_event_count")),
        )


def _snapshot_payload_is_valid(
    world_id: uuid.UUID,
    snapshot: WorldSnapshotRecord,
    payload: dict[str, Any],
) -> bool:
    try:
        state = WorldReplayState.model_validate({**payload, "world_id": world_id})
    except ValidationError:
        return False
    return state.source_sequence == snapshot.covers_event_sequence


def _snapshot_object_key(
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    source_sequence: int,
) -> str:
    return f"worlds/{world_id}/worldlines/{worldline_id}/snapshots/{source_sequence}.json"


def _payload_location(snapshot: WorldSnapshotRecord) -> str | None:
    if snapshot.payload_uri is not None:
        return "object"
    if snapshot.payload is not None:
        return "inline"
    return None


def _replay_relevant_event_gap(
    covers_event_sequence: int,
    events: list[WorldEventRecord],
) -> int:
    latest_relevant_sequence = covers_event_sequence
    for event in events:
        if event.event_name != SNAPSHOT_EVENT_NAME:
            latest_relevant_sequence = event.sequence
    return max(latest_relevant_sequence - covers_event_sequence, 0)


def _is_error_issue(issue: str) -> bool:
    return "schema version" in issue or "payload" in issue or "future event sequence" in issue


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
