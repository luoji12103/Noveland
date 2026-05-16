from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlayerPrivacyRequestStatus(StrEnum):
    REQUESTED = "requested"
    UNDER_REVIEW = "under_review"
    APPROVED_FOR_REDACTION = "approved_for_redaction"
    REJECTED = "rejected"
    COMPLETED = "completed"


class PlayerPrivacyRequestKind(StrEnum):
    EXPORT = "export"
    DELETE = "delete"


class PlayerPrivacyTargetKind(StrEnum):
    PLAYER_PROFILE = "player_profile"
    PLAYER_CHOICES = "player_choices"
    PLAYER_JOURNAL = "player_journal"
    NOTIFICATIONS = "notifications"
    INTERVENTIONS = "interventions"
    CONVERSATION_REFERENCES = "conversation_references"
    ALL_PLAYER_DATA = "all_player_data"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class PlayerPrivacyProfile(_FrozenContract):
    user_id: uuid.UUID
    email: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    world_role: str | None = None


class PlayerPrivacyActorExport(_FrozenContract):
    id: uuid.UUID
    worldline_id: uuid.UUID
    display_name: str = Field(min_length=1)
    current_scene_id: uuid.UUID | None = None
    profile: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PlayerPrivacyChoiceExport(_FrozenContract):
    id: uuid.UUID
    worldline_id: uuid.UUID
    player_actor_id: uuid.UUID
    choice_key: str = Field(min_length=1)
    choice_kind: str = Field(min_length=1)
    selected_option: str = Field(min_length=1)
    applied_event_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class PlayerPrivacyJournalExport(_FrozenContract):
    id: uuid.UUID
    worldline_id: uuid.UUID
    player_actor_id: uuid.UUID | None = None
    entry_kind: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    source_ref: str | None = None
    visibility: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime


class PlayerPrivacyNotificationExport(_FrozenContract):
    id: uuid.UUID
    worldline_id: uuid.UUID
    notification_kind: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    source_ref: str | None = None
    status: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime


class PlayerPrivacyInterventionExport(_FrozenContract):
    id: uuid.UUID
    worldline_id: uuid.UUID
    player_actor_id: uuid.UUID
    intervention_kind: str = Field(min_length=1)
    target_agent_id: uuid.UUID | None = None
    target_scene_id: uuid.UUID | None = None
    choice_id: uuid.UUID | None = None
    event_id: uuid.UUID | None = None
    status: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime


class PlayerPrivacyConversationReference(_FrozenContract):
    id: uuid.UUID
    worldline_id: uuid.UUID
    session_key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    scope_type: str = Field(min_length=1)
    mode: str = Field(min_length=1)
    status: str = Field(min_length=1)
    scene_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class PlayerPrivacyExport(_FrozenContract):
    request_id: uuid.UUID | None = None
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    user_id: uuid.UUID
    generated_at: datetime
    profile: PlayerPrivacyProfile
    counts: dict[str, int]
    player_actors: tuple[PlayerPrivacyActorExport, ...]
    choices: tuple[PlayerPrivacyChoiceExport, ...]
    journal_entries: tuple[PlayerPrivacyJournalExport, ...]
    notifications: tuple[PlayerPrivacyNotificationExport, ...]
    interventions: tuple[PlayerPrivacyInterventionExport, ...]
    conversation_references: tuple[PlayerPrivacyConversationReference, ...]
    safeguards: tuple[str, ...]


class PlayerPrivacyRequestCreate(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    target_ref_kind: PlayerPrivacyTargetKind = PlayerPrivacyTargetKind.ALL_PLAYER_DATA
    target_ref_id: uuid.UUID | None = None
    reason: str | None = Field(default=None, max_length=500)


class PlayerPrivacyRequestReview(_FrozenContract):
    status: PlayerPrivacyRequestStatus
    review_note: str | None = Field(default=None, max_length=500)


class PlayerPrivacyRequestRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    user_id: uuid.UUID
    request_kind: PlayerPrivacyRequestKind
    status: PlayerPrivacyRequestStatus
    target_ref_kind: str | None = None
    target_ref_id: uuid.UUID | None = None
    reason: str | None = None
    summary: dict[str, Any]
    redaction_plan: dict[str, Any]
    created_by_actor_ref: str
    reviewed_by_actor_ref: str | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", "reviewed_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
