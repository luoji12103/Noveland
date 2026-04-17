from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CalendarEntryStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class ScheduleRuleKind(StrEnum):
    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    TIMETABLE = "timetable"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class CalendarEntryCreate(_FrozenContract):
    world_id: uuid.UUID
    agent_id: uuid.UUID
    title: str = Field(min_length=1, max_length=160)
    description: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    recurrence_rule: str | None = Field(default=None, max_length=240)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("starts_at", "ends_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("calendar datetimes must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_time_range(self) -> CalendarEntryCreate:
        if self.ends_at is not None and self.ends_at < self.starts_at:
            raise ValueError("ends_at must be greater than or equal to starts_at")
        return self


class CalendarEntryUpdate(_FrozenContract):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    recurrence_rule: str | None = Field(default=None, max_length=240)
    status: CalendarEntryStatus | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("starts_at", "ends_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("calendar datetimes must be timezone-aware")
        return value.astimezone(UTC)


class CalendarEntryRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    agent_id: uuid.UUID
    title: str
    description: str | None
    starts_at: datetime
    ends_at: datetime | None
    recurrence_rule: str | None
    status: CalendarEntryStatus
    metadata: dict[str, Any]


class ScheduleRuleCreate(_FrozenContract):
    world_id: uuid.UUID
    rule_key: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$", max_length=80)
    name: str = Field(min_length=1, max_length=160)
    kind: ScheduleRuleKind
    config: dict[str, Any] = Field(default_factory=dict)


class ScheduleRuleUpdate(_FrozenContract):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    kind: ScheduleRuleKind | None = None
    config: dict[str, Any] | None = None
    is_enabled: bool | None = None


class ScheduleRuleRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    rule_key: str
    name: str
    kind: ScheduleRuleKind
    config: dict[str, Any]
    is_enabled: bool
