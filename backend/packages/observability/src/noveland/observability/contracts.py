from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DiagnosticComponent(StrEnum):
    RUNTIME = "runtime"
    PROVIDER = "provider"
    AGENT = "agent"
    EVENT_PUBLISHER = "event_publisher"
    API = "api"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class RuntimeDiagnosticCreate(_FrozenContract):
    severity: DiagnosticSeverity
    component: DiagnosticComponent
    event_type: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=500)
    details: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None
    world_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    run_id: uuid.UUID | None = None
    provider_profile_id: uuid.UUID | None = None

    @field_validator("occurred_at", mode="after")
    @classmethod
    def normalize_occurred_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value.astimezone(UTC)


class RuntimeDiagnosticRecord(_FrozenContract):
    id: uuid.UUID
    severity: DiagnosticSeverity
    component: DiagnosticComponent
    event_type: str
    message: str
    details: dict[str, Any]
    occurred_at: datetime
    world_id: uuid.UUID | None
    agent_id: uuid.UUID | None
    run_id: uuid.UUID | None
    provider_profile_id: uuid.UUID | None
    created_at: datetime
