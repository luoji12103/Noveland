from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from noveland.core.database import import_model_modules
from noveland.events.contracts import (
    SNAPSHOT_EVENT_NAME,
    WorldEventAppend,
    WorldEventRecord,
    WorldSnapshotCreate,
    WorldSnapshotRecord,
    WorldSnapshotStatus,
)
from noveland.events.errors import (
    EventAppendError,
    EventStoreError,
    EventValidationError,
    SnapshotValidationError,
)
from noveland.events.models import WorldEventModel, WorldSnapshotModel
from pydantic import ValidationError
from sqlalchemy import desc, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

EventAppendInput = WorldEventAppend | Mapping[str, Any]
SnapshotCreateInput = WorldSnapshotCreate | Mapping[str, Any]


class WorldEventStore:
    def __init__(self, session: Session) -> None:
        import_model_modules()
        self._session = session

    def append_event(self, event: EventAppendInput) -> WorldEventRecord:
        event_input = _coerce_event_append(event)
        try:
            sequence = self._next_sequence(event_input.world_id)
            event_model = WorldEventModel(
                world_id=event_input.world_id,
                sequence=sequence,
                event_name=event_input.event_name,
                payload=event_input.payload,
                wall_time=event_input.wall_time,
                world_time=event_input.world_time,
                actor_ref=event_input.actor_ref,
                causation_event_id=event_input.causation_event_id,
                correlation_id=event_input.correlation_id,
            )
            self._session.add(event_model)
            self._session.flush()
            self._session.refresh(event_model)
        except SQLAlchemyError as exc:
            raise EventAppendError("failed to append world event") from exc

        return _event_record_from_model(event_model)

    def list_events_after(
        self,
        world_id: uuid.UUID,
        sequence: int,
        limit: int | None = None,
    ) -> list[WorldEventRecord]:
        if sequence < 0:
            raise EventValidationError("sequence must be non-negative")
        if limit is not None and limit <= 0:
            raise EventValidationError("limit must be positive when provided")

        statement = (
            select(WorldEventModel)
            .where(
                WorldEventModel.world_id == world_id,
                WorldEventModel.sequence > sequence,
            )
            .order_by(WorldEventModel.sequence.asc())
        )
        if limit is not None:
            statement = statement.limit(limit)

        return [
            _event_record_from_model(event_model)
            for event_model in self._session.scalars(statement).all()
        ]

    def record_snapshot(self, snapshot: SnapshotCreateInput) -> WorldSnapshotRecord:
        snapshot_input = _coerce_snapshot_create(snapshot)
        snapshot_event = self.append_event(
            WorldEventAppend(
                world_id=snapshot_input.world_id,
                event_name=SNAPSHOT_EVENT_NAME,
                payload={
                    "covers_event_sequence": snapshot_input.covers_event_sequence,
                    "schema_version": snapshot_input.schema_version,
                    "status": snapshot_input.status.value,
                    "payload_uri": snapshot_input.payload_uri,
                },
                wall_time=datetime.now(UTC),
                actor_ref=snapshot_input.actor_ref,
                correlation_id=snapshot_input.correlation_id,
            ),
        )

        try:
            snapshot_model = WorldSnapshotModel(
                world_id=snapshot_input.world_id,
                covers_event_sequence=snapshot_input.covers_event_sequence,
                schema_version=snapshot_input.schema_version,
                status=snapshot_input.status.value,
                payload=snapshot_input.payload,
                payload_uri=snapshot_input.payload_uri,
                snapshot_metadata=snapshot_input.metadata,
                created_by_event_id=snapshot_event.id,
            )
            self._session.add(snapshot_model)
            self._session.flush()
            self._session.refresh(snapshot_model)
        except SQLAlchemyError as exc:
            raise EventStoreError("failed to record world snapshot") from exc

        return _snapshot_record_from_model(snapshot_model)

    def latest_snapshot(self, world_id: uuid.UUID) -> WorldSnapshotRecord | None:
        statement = (
            select(WorldSnapshotModel)
            .where(
                WorldSnapshotModel.world_id == world_id,
                WorldSnapshotModel.status == WorldSnapshotStatus.VALID.value,
            )
            .order_by(
                desc(WorldSnapshotModel.covers_event_sequence),
                desc(WorldSnapshotModel.created_at),
            )
            .limit(1)
        )
        snapshot_model = self._session.scalars(statement).first()
        if snapshot_model is None:
            return None
        return _snapshot_record_from_model(snapshot_model)

    def _next_sequence(self, world_id: uuid.UUID) -> int:
        locked_world = self._session.execute(
            text("SELECT id FROM worlds WHERE id = CAST(:world_id AS uuid) FOR UPDATE"),
            {"world_id": str(world_id)},
        ).first()
        if locked_world is None:
            raise EventAppendError("world does not exist")

        latest_sequence = self._session.execute(
            select(func.max(WorldEventModel.sequence)).where(
                WorldEventModel.world_id == world_id,
            ),
        ).scalar_one()
        return int(latest_sequence or 0) + 1


def _coerce_event_append(event: EventAppendInput) -> WorldEventAppend:
    if isinstance(event, WorldEventAppend):
        return event
    try:
        return WorldEventAppend.model_validate(event)
    except ValidationError as exc:
        raise EventValidationError("invalid world event input") from exc


def _coerce_snapshot_create(snapshot: SnapshotCreateInput) -> WorldSnapshotCreate:
    if isinstance(snapshot, WorldSnapshotCreate):
        return snapshot
    try:
        return WorldSnapshotCreate.model_validate(snapshot)
    except ValidationError as exc:
        raise SnapshotValidationError("invalid world snapshot input") from exc


def _event_record_from_model(event_model: WorldEventModel) -> WorldEventRecord:
    return WorldEventRecord(
        id=event_model.id,
        world_id=event_model.world_id,
        sequence=event_model.sequence,
        event_name=event_model.event_name,
        payload=event_model.payload,
        wall_time=event_model.wall_time,
        world_time=event_model.world_time,
        actor_ref=event_model.actor_ref,
        causation_event_id=event_model.causation_event_id,
        correlation_id=event_model.correlation_id,
        created_at=event_model.created_at,
    )


def _snapshot_record_from_model(snapshot_model: WorldSnapshotModel) -> WorldSnapshotRecord:
    return WorldSnapshotRecord(
        id=snapshot_model.id,
        world_id=snapshot_model.world_id,
        covers_event_sequence=snapshot_model.covers_event_sequence,
        schema_version=snapshot_model.schema_version,
        status=WorldSnapshotStatus(snapshot_model.status),
        payload=snapshot_model.payload,
        payload_uri=snapshot_model.payload_uri,
        metadata=snapshot_model.snapshot_metadata,
        created_by_event_id=snapshot_model.created_by_event_id,
        created_at=snapshot_model.created_at,
    )
