from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from noveland.media.contracts import (
    MediaAssetKind,
    MediaAssetRecord,
    MediaAssetRole,
    MediaAssetStatus,
    MediaJobRecord,
    MediaObjectRecord,
    MediaObjectRole,
    MediaSourceKind,
    MediaVisibility,
)
from pydantic import BaseModel, ConfigDict, Field, field_validator


class VisualRecordStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


class SpriteBindingVisibility(StrEnum):
    PRIVATE = "private"
    WORLD_ADMIN = "world_admin"
    WORLD_MEMBER = "world_member"
    DEVELOPER_ONLY = "developer_only"
    HIDDEN = "hidden"


class BackgroundVisibility(StrEnum):
    PRIVATE = "private"
    WORLD_ADMIN = "world_admin"
    WORLD_MEMBER = "world_member"
    DEVELOPER_ONLY = "developer_only"
    HIDDEN = "hidden"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class SpriteSetCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    agent_id: uuid.UUID
    style_key: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=200)
    default_variant_id: uuid.UUID | None = None
    status: VisualRecordStatus = VisualRecordStatus.ACTIVE
    visibility: SpriteBindingVisibility = SpriteBindingVisibility.WORLD_ADMIN
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("style_key", mode="after")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("style_key must not be empty")
        return normalized

    @field_validator("metadata_json", mode="after")
    @classmethod
    def validate_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value)
        return value


class SpriteSetUpdate(_FrozenContract):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    default_variant_id: uuid.UUID | None = None
    status: VisualRecordStatus | None = None
    visibility: SpriteBindingVisibility | None = None
    metadata_json: dict[str, Any] | None = None

    @field_validator("metadata_json", mode="after")
    @classmethod
    def validate_json(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            _assert_json_serializable(value)
        return value


class SpriteSetRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    agent_id: uuid.UUID
    style_key: str
    display_name: str
    default_variant_id: uuid.UUID | None
    status: VisualRecordStatus
    visibility: SpriteBindingVisibility
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class SpriteVariantCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    sprite_set_id: uuid.UUID
    asset_id: uuid.UUID
    expression_key: str = Field(default="neutral", min_length=1, max_length=80)
    pose_key: str | None = Field(default=None, min_length=1, max_length=80)
    outfit_key: str | None = Field(default=None, min_length=1, max_length=80)
    mood_tags: tuple[str, ...] = ()
    priority: int = Field(default=100, ge=0)
    is_default: bool = False
    status: VisualRecordStatus = VisualRecordStatus.ACTIVE
    visibility: SpriteBindingVisibility = SpriteBindingVisibility.WORLD_ADMIN
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("expression_key", "pose_key", "outfit_key", mode="after")
    @classmethod
    def normalize_optional_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("sprite variant key must not be empty")
        return normalized

    @field_validator("mood_tags", mode="after")
    @classmethod
    def normalize_mood_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted({item.strip().lower() for item in value if item.strip()}))

    @field_validator("metadata_json", mode="after")
    @classmethod
    def validate_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value)
        return value


class SpriteVariantUpdate(_FrozenContract):
    asset_id: uuid.UUID | None = None
    expression_key: str | None = Field(default=None, min_length=1, max_length=80)
    pose_key: str | None = Field(default=None, min_length=1, max_length=80)
    outfit_key: str | None = Field(default=None, min_length=1, max_length=80)
    mood_tags: tuple[str, ...] | None = None
    priority: int | None = Field(default=None, ge=0)
    is_default: bool | None = None
    status: VisualRecordStatus | None = None
    visibility: SpriteBindingVisibility | None = None
    metadata_json: dict[str, Any] | None = None

    @field_validator("metadata_json", mode="after")
    @classmethod
    def validate_json(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            _assert_json_serializable(value)
        return value


class SpriteVariantRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    sprite_set_id: uuid.UUID
    asset_id: uuid.UUID
    expression_key: str
    pose_key: str | None
    outfit_key: str | None
    mood_tags: tuple[str, ...]
    priority: int
    is_default: bool
    status: VisualRecordStatus
    visibility: SpriteBindingVisibility
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class SceneBackgroundCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    scene_id: uuid.UUID | None = None
    location_key: str = Field(min_length=1, max_length=120)
    time_of_day: str | None = Field(default=None, min_length=1, max_length=40)
    weather_key: str | None = Field(default=None, min_length=1, max_length=80)
    asset_id: uuid.UUID
    priority: int = Field(default=100, ge=0)
    is_default: bool = False
    status: VisualRecordStatus = VisualRecordStatus.ACTIVE
    visibility: BackgroundVisibility = BackgroundVisibility.WORLD_ADMIN
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("location_key", "time_of_day", "weather_key", mode="after")
    @classmethod
    def normalize_location_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("background key must not be empty")
        return normalized

    @field_validator("metadata_json", mode="after")
    @classmethod
    def validate_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value)
        return value


class SceneBackgroundUpdate(_FrozenContract):
    scene_id: uuid.UUID | None = None
    location_key: str | None = Field(default=None, min_length=1, max_length=120)
    time_of_day: str | None = Field(default=None, min_length=1, max_length=40)
    weather_key: str | None = Field(default=None, min_length=1, max_length=80)
    asset_id: uuid.UUID | None = None
    priority: int | None = Field(default=None, ge=0)
    is_default: bool | None = None
    status: VisualRecordStatus | None = None
    visibility: BackgroundVisibility | None = None
    metadata_json: dict[str, Any] | None = None

    @field_validator("metadata_json", mode="after")
    @classmethod
    def validate_json(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            _assert_json_serializable(value)
        return value


class SceneBackgroundRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    scene_id: uuid.UUID | None
    location_key: str
    time_of_day: str | None
    weather_key: str | None
    asset_id: uuid.UUID
    priority: int
    is_default: bool
    status: VisualRecordStatus
    visibility: BackgroundVisibility
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class VisualAssetRef(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    asset_kind: MediaAssetKind
    asset_role: MediaAssetRole
    source_kind: MediaSourceKind
    status: MediaAssetStatus
    visibility: MediaVisibility
    mime_type: str | None
    file_ext: str | None
    size_bytes: int | None
    checksum_sha256: str | None
    width: int | None
    height: int | None
    has_alpha: bool | None
    title: str | None
    description: str | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class VisualObjectRef(_FrozenContract):
    id: uuid.UUID
    asset_id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    object_role: MediaObjectRole
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    width: int | None
    height: int | None
    duration_ms: int | None
    sample_rate_hz: int | None
    audio_channels: int | None
    frame_rate: float | None
    metadata: dict[str, Any]
    created_at: datetime

    @field_validator("created_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class SpriteResolveRequest(_FrozenContract):
    worldline_id: uuid.UUID
    agent_id: uuid.UUID
    expression_key: str | None = Field(default=None, min_length=1, max_length=80)
    pose_key: str | None = Field(default=None, min_length=1, max_length=80)
    outfit_key: str | None = Field(default=None, min_length=1, max_length=80)
    mood_tags: tuple[str, ...] = ()
    style_key: str | None = Field(default=None, min_length=1, max_length=120)
    include_restricted: bool = False


class SpriteResolveResult(_FrozenContract):
    sprite_set: SpriteSetRead
    variant: SpriteVariantRead
    asset: VisualAssetRef
    fallback_reason: str | None
    confidence: float


class BackgroundResolveRequest(_FrozenContract):
    worldline_id: uuid.UUID
    scene_id: uuid.UUID | None = None
    location_key: str = Field(min_length=1, max_length=120)
    time_of_day: str | None = Field(default=None, min_length=1, max_length=40)
    weather_key: str | None = Field(default=None, min_length=1, max_length=80)
    include_restricted: bool = False


class BackgroundResolveResult(_FrozenContract):
    background: SceneBackgroundRead
    asset: VisualAssetRef
    fallback_reason: str | None
    confidence: float


class SceneLayer(_FrozenContract):
    asset_id: uuid.UUID
    x: int
    y: int
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    z_index: int = 0
    blend_mode: str | None = Field(default=None, min_length=1, max_length=40)


class SceneComposeRequest(_FrozenContract):
    worldline_id: uuid.UUID
    background_asset_id: uuid.UUID
    layers: tuple[SceneLayer, ...] = ()
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata_json", mode="after")
    @classmethod
    def validate_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value)
        return value


class SceneComposeResult(_FrozenContract):
    media_job: MediaJobRecord
    output_asset: VisualAssetRef
    output_objects: list[VisualObjectRef]


def visual_asset_ref(record: MediaAssetRecord) -> VisualAssetRef:
    return VisualAssetRef(
        id=record.id,
        world_id=record.world_id,
        worldline_id=record.worldline_id,
        asset_kind=record.asset_kind,
        asset_role=record.asset_role,
        source_kind=record.source_kind,
        status=record.status,
        visibility=record.visibility,
        mime_type=record.mime_type,
        file_ext=record.file_ext,
        size_bytes=record.size_bytes,
        checksum_sha256=record.checksum_sha256,
        width=record.width,
        height=record.height,
        has_alpha=record.has_alpha,
        title=record.title,
        description=record.description,
        metadata=record.metadata,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def visual_object_ref(record: MediaObjectRecord) -> VisualObjectRef:
    return VisualObjectRef(
        id=record.id,
        asset_id=record.asset_id,
        world_id=record.world_id,
        worldline_id=record.worldline_id,
        object_role=record.object_role,
        mime_type=record.mime_type,
        size_bytes=record.size_bytes,
        checksum_sha256=record.checksum_sha256,
        width=record.width,
        height=record.height,
        duration_ms=record.duration_ms,
        sample_rate_hz=record.sample_rate_hz,
        audio_channels=record.audio_channels,
        frame_rate=record.frame_rate,
        metadata=record.metadata,
        created_at=record.created_at,
    )


def _assert_json_serializable(value: dict[str, Any]) -> None:
    json.dumps(value)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
