from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EVENT_NAME_PATTERN = r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$"
SNAPSHOT_EVENT_NAME = "world.snapshot_created"


class WorldSnapshotStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"


class WorldEventImportance(StrEnum):
    SYSTEM = "system"
    DAILY = "daily"
    RELATIONSHIP = "relationship"
    ORGANIZATION = "organization"
    ROUTE = "route"
    MAIN_PLOT = "main_plot"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class WorldEventAppend(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    event_name: str = Field(min_length=3, max_length=120, pattern=EVENT_NAME_PATTERN)
    payload: dict[str, Any] = Field(default_factory=dict)
    importance: WorldEventImportance = WorldEventImportance.SYSTEM
    wall_time: datetime
    world_time: datetime | None = None
    actor_ref: str = Field(min_length=1, max_length=120)
    causation_event_id: uuid.UUID | None = None
    correlation_id: uuid.UUID | None = None

    @field_validator("wall_time", "world_time", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetimes must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("payload", mode="after")
    @classmethod
    def payload_must_be_json_serializable(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "payload")
        return value


class WorldEventRecord(WorldEventAppend):
    id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    sequence: int = Field(gt=0)
    created_at: datetime

    @field_validator("created_at", mode="after")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(UTC)


class WorldSnapshotCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    covers_event_sequence: int = Field(ge=0)
    schema_version: str = Field(min_length=1, max_length=80)
    payload: dict[str, Any] | None = None
    payload_uri: str | None = Field(default=None, min_length=1, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
    actor_ref: str = Field(min_length=1, max_length=120)
    correlation_id: uuid.UUID | None = None
    status: WorldSnapshotStatus = WorldSnapshotStatus.VALID

    @field_validator("payload", "metadata", mode="after")
    @classmethod
    def json_fields_must_be_serializable(
        cls,
        value: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if value is not None:
            _assert_json_serializable(value, "snapshot JSON fields")
        return value

    @model_validator(mode="after")
    def require_payload_or_uri(self) -> WorldSnapshotCreate:
        if self.payload is None and self.payload_uri is None:
            raise ValueError("snapshot requires either payload or payload_uri")
        return self


class WorldSnapshotRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    covers_event_sequence: int = Field(ge=0)
    schema_version: str = Field(min_length=1, max_length=80)
    status: WorldSnapshotStatus = WorldSnapshotStatus.VALID
    payload: dict[str, Any] | None = None
    payload_uri: str | None = Field(default=None, min_length=1, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_by_event_id: uuid.UUID
    created_at: datetime

    @field_validator("payload", "metadata", mode="after")
    @classmethod
    def json_fields_must_be_serializable(
        cls,
        value: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if value is not None:
            _assert_json_serializable(value, "snapshot JSON fields")
        return value

    @field_validator("created_at", mode="after")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_payload_or_uri(self) -> WorldSnapshotRecord:
        if self.payload is None and self.payload_uri is None:
            raise ValueError("snapshot requires either payload or payload_uri")
        return self


def _assert_json_serializable(value: dict[str, Any], field_name: str) -> None:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be JSON serializable") from exc
