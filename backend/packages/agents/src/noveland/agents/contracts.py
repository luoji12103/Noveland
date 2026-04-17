from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class AgentPersonaUpsert(_FrozenContract):
    world_id: uuid.UUID
    agent_id: uuid.UUID
    persona_text: str = Field(default="", max_length=12_000)
    behavior_policy: dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True


class AgentPersonaRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    agent_id: uuid.UUID
    persona_text: str
    behavior_policy: dict[str, Any]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class AgentObservationCreate(_FrozenContract):
    world_id: uuid.UUID
    agent_id: uuid.UUID
    observation_type: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=12_000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_event_id: uuid.UUID | None = None

    @field_validator("observed_at", mode="after")
    @classmethod
    def observed_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value.astimezone(UTC)


class AgentObservationRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    agent_id: uuid.UUID
    source_event_id: uuid.UUID | None
    observation_type: str
    content: str
    metadata: dict[str, Any]
    observed_at: datetime
    consumed_at: datetime | None
    created_at: datetime


class AgentObservationRefreshResult(_FrozenContract):
    created_count: int
    observations: list[AgentObservationRecord]
