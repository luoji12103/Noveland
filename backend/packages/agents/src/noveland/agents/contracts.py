from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from noveland.plugins.constants import BUILTIN_DEFAULT_PERSONA_POLICY
from pydantic import BaseModel, ConfigDict, Field, field_validator


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class AgentPersonaUpsert(_FrozenContract):
    world_id: uuid.UUID
    agent_id: uuid.UUID
    persona_text: str = Field(default="", max_length=12_000)
    behavior_policy: dict[str, Any] = Field(default_factory=dict)
    policy_plugin_identifier: str = Field(
        default=BUILTIN_DEFAULT_PERSONA_POLICY,
        min_length=1,
        max_length=120,
    )
    policy_plugin_config: dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True


class AgentPersonaRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    agent_id: uuid.UUID
    persona_text: str
    behavior_policy: dict[str, Any]
    policy_plugin_identifier: str
    policy_plugin_config: dict[str, Any]
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
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    review_status: str = Field(default="unreviewed", pattern="^(unreviewed|approved|rejected)$")

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
    confidence_score: float | None
    review_status: str
    runtime_use_count: int
    last_used_run_id: uuid.UUID | None
    created_at: datetime


class AgentObservationRefreshResult(_FrozenContract):
    created_count: int
    observations: list[AgentObservationRecord]


class AgentPresetCalendarEntry(_FrozenContract):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    recurrence_rule: str | None = Field(default=None, max_length=240)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("starts_at", "ends_at", mode="after")
    @classmethod
    def calendar_times_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("calendar blueprint times must be timezone-aware")
        return value.astimezone(UTC)


class AgentPresetUpsert(_FrozenContract):
    preset_key: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    default_kind: str = Field(pattern="^(role_agent|narrative_agent)$")
    default_provider_profile_key: str | None = Field(default=None, max_length=80)
    persona_text: str = Field(default="", max_length=12_000)
    behavior_policy: dict[str, Any] = Field(default_factory=dict)
    calendar_blueprint: list[AgentPresetCalendarEntry] = Field(default_factory=list)
    advanced_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class AgentPresetRecord(_FrozenContract):
    id: uuid.UUID
    preset_key: str
    name: str
    description: str | None
    default_kind: str
    default_provider_profile_key: str | None
    persona_text: str
    behavior_policy: dict[str, Any]
    calendar_blueprint: list[AgentPresetCalendarEntry]
    advanced_config: dict[str, Any]
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
