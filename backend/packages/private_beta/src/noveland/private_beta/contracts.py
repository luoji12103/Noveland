from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PrivateBetaInviteStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    WAITLISTED = "waitlisted"
    REDEEMED = "redeemed"
    EXPIRED = "expired"
    REVOKED = "revoked"


class PrivateBetaRole(StrEnum):
    TESTER = "tester"
    PLAYER_TESTER = "player_tester"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class PrivateBetaInviteCreate(_FrozenContract):
    invited_email: str | None = Field(default=None, max_length=320)
    invited_user_id: uuid.UUID | None = None
    worldline_id: uuid.UUID | None = None
    status: PrivateBetaInviteStatus = PrivateBetaInviteStatus.PENDING
    beta_role: PrivateBetaRole = PrivateBetaRole.TESTER
    expires_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("expires_at", mode="after")
    @classmethod
    def normalize_expires_at(cls, value: datetime) -> datetime:
        return _normalize_datetime(value)

    @field_validator("invited_email", mode="after")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None


class PrivateBetaInviteRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None
    invited_email: str | None
    invited_user_id: uuid.UUID | None
    status: PrivateBetaInviteStatus
    intended_world_role: str
    beta_role: PrivateBetaRole
    expires_at: datetime
    accepted_at: datetime | None
    redeemed_at: datetime | None
    redeemed_by_user_id: uuid.UUID | None
    revoked_at: datetime | None
    revoked_by_actor_ref: str | None
    revocation_reason: str | None
    created_by_actor_ref: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator(
        "expires_at",
        "accepted_at",
        "redeemed_at",
        "revoked_at",
        "created_at",
        "updated_at",
        mode="after",
    )
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _normalize_datetime(value)


class PrivateBetaInviteCreated(_FrozenContract):
    invite: PrivateBetaInviteRead
    token: str = Field(min_length=32)


class PrivateBetaInviteRevoke(_FrozenContract):
    reason: str = Field(min_length=1, max_length=500)


class PrivateBetaInviteRedeem(_FrozenContract):
    token: str = Field(min_length=32)


class PrivateBetaPlayerProfileRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    user_id: uuid.UUID
    actor_ref: str
    display_name: str
    current_scene_id: uuid.UUID | None
    profile: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _normalize_datetime(value)


class PrivateBetaAccessRead(_FrozenContract):
    invite_id: uuid.UUID
    world_id: uuid.UUID
    world_name: str
    worldline_id: uuid.UUID | None
    worldline_name: str | None
    status: PrivateBetaInviteStatus
    beta_role: PrivateBetaRole
    expires_at: datetime
    redeemed_at: datetime | None
    player_profile: PrivateBetaPlayerProfileRead | None = None

    @field_validator("expires_at", "redeemed_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _normalize_datetime(value)


class PrivateBetaRedeemResult(_FrozenContract):
    access: PrivateBetaAccessRead
    membership_role: str
    idempotent: bool = False


class PrivateBetaOnboardingStatus(_FrozenContract):
    access: tuple[PrivateBetaAccessRead, ...]
    guidance: tuple[str, ...]


class PrivateBetaPlayerProfileCreate(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    display_name: str = Field(min_length=1, max_length=160)
    current_scene_id: uuid.UUID | None = None
    profile: dict[str, Any] = Field(default_factory=dict)


class PrivateBetaPlayerProfileResult(_FrozenContract):
    access: PrivateBetaAccessRead
    player_profile: PrivateBetaPlayerProfileRead


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetimes must be timezone-aware")
    return value.astimezone(UTC)
