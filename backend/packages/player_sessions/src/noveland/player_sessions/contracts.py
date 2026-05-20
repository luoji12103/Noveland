from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlayerRecoveryStatus(StrEnum):
    READY = "ready"
    STALE_CONVERSATION = "stale_conversation"
    MISSING_MEDIA = "missing_media"
    PROVIDER_FAILURE = "provider_failure"
    MEDIA_FAILURE = "media_failure"
    PRESENTATION_UNAVAILABLE = "presentation_unavailable"


class PlayerSessionStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class PlayerSessionUpsert(_FrozenContract):
    worldline_id: uuid.UUID
    player_actor_id: uuid.UUID
    conversation_session_id: uuid.UUID | None = None
    scene_id: uuid.UUID | None = None
    last_turn_id: uuid.UUID | None = None
    last_presentation_id: uuid.UUID | None = None
    route_state: dict[str, Any] = Field(default_factory=dict)
    resume_state: dict[str, Any] = Field(default_factory=dict)
    recovery_status: PlayerRecoveryStatus = PlayerRecoveryStatus.READY
    status: PlayerSessionStatus = PlayerSessionStatus.ACTIVE


class PlayerSessionRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    user_id: uuid.UUID
    player_actor_id: uuid.UUID
    conversation_session_id: uuid.UUID | None
    scene_id: uuid.UUID | None
    last_turn_id: uuid.UUID | None
    last_presentation_id: uuid.UUID | None
    route_state: dict[str, Any]
    resume_state: dict[str, Any]
    recovery_status: PlayerRecoveryStatus
    recovery_label: str
    available_actions: tuple[str, ...]
    status: PlayerSessionStatus
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    @field_validator("last_seen_at", "created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetimes must be timezone-aware")
        return value.astimezone(UTC)
