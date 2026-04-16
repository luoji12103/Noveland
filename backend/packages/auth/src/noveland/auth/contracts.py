from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class AuthRole(StrEnum):
    PLATFORM_ADMIN = "platform_admin"
    WORLD_ADMIN = "world_admin"
    HUMAN_USER = "human_user"
    AGENT_RUNTIME = "agent_runtime"


class AuthSessionStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class PasswordCredentialSet(_FrozenContract):
    user_id: uuid.UUID
    password: SecretStr

    @field_validator("password", mode="after")
    @classmethod
    def password_has_minimum_length(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 8:
            raise ValueError("password must be at least 8 characters")
        return value


class PasswordCredentialRecord(_FrozenContract):
    id: uuid.UUID
    user_id: uuid.UUID
    password_hash: str = Field(min_length=1, max_length=500)
    password_set_at: datetime
    password_updated_at: datetime
    disabled_at: datetime | None = None

    @field_validator("password_set_at", "password_updated_at", "disabled_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _normalize_datetime(value)


class AuthSessionCreate(_FrozenContract):
    user_id: uuid.UUID
    expires_at: datetime
    user_agent: str | None = Field(default=None, max_length=500)
    ip_address: str | None = Field(default=None, max_length=64)

    @field_validator("expires_at", mode="after")
    @classmethod
    def normalize_expires_at(cls, value: datetime) -> datetime:
        return _normalize_datetime(value)


class AuthSessionRecord(_FrozenContract):
    id: uuid.UUID
    user_id: uuid.UUID
    token_hash: str = Field(min_length=64, max_length=64)
    status: AuthSessionStatus
    expires_at: datetime
    revoked_at: datetime | None = None
    last_seen_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime

    @field_validator("expires_at", "revoked_at", "last_seen_at", "created_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _normalize_datetime(value)


class CreatedAuthSession(_FrozenContract):
    token: str = Field(min_length=32)
    session: AuthSessionRecord


class AuthenticatedSubject(_FrozenContract):
    user_id: uuid.UUID
    session_id: uuid.UUID
    roles: frozenset[AuthRole] = Field(default_factory=frozenset)
    authenticated_at: datetime

    @field_validator("authenticated_at", mode="after")
    @classmethod
    def normalize_authenticated_at(cls, value: datetime) -> datetime:
        return _normalize_datetime(value)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetimes must be timezone-aware")
    return value.astimezone(UTC)
