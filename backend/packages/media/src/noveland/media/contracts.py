from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CHECKSUM_PATTERN = re.compile(r"^[a-f0-9]{64}$")
IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
AUDIO_MIME_TYPES = {"audio/mpeg", "audio/wav", "audio/ogg", "audio/webm"}


class MediaAssetKind(StrEnum):
    IMAGE = "image"
    AUDIO = "audio"


class MediaAssetRole(StrEnum):
    ORIGINAL_IMAGE = "original_image"
    REFERENCE_IMAGE = "reference_image"
    MASK_IMAGE = "mask_image"
    TRANSPARENT_PNG = "transparent_png"
    COMPOSITE_IMAGE = "composite_image"
    SCENE_BACKGROUND = "scene_background"
    CHARACTER_SPRITE = "character_sprite"
    CHARACTER_EXPRESSION = "character_expression"
    CHARACTER_POSE = "character_pose"
    EVENT_CG = "event_cg"
    SPEECH_AUDIO = "speech_audio"
    VOICE_FILE = "voice_file"
    VOICE_SAMPLE = "voice_sample"
    TRANSCRIPT_AUDIO = "transcript_audio"


class MediaSourceKind(StrEnum):
    PROVIDER_GENERATED = "provider_generated"
    MANUAL_UPLOAD = "manual_upload"
    IMPORTED_ORIGINAL = "imported_original"
    COMPOSED = "composed"
    BACKGROUND_REMOVED = "background_removed"


class MediaAssetStatus(StrEnum):
    REGISTERED = "registered"
    AVAILABLE = "available"
    FAILED = "failed"
    DELETED = "deleted"


class MediaVisibility(StrEnum):
    PRIVATE = "private"
    WORLD_ADMIN = "world_admin"
    WORLD_MEMBER = "world_member"
    PLAYER_VISIBLE = "player_visible"
    READER_VISIBLE = "reader_visible"
    DEVELOPER_ONLY = "developer_only"
    HIDDEN = "hidden"


class MediaJobKind(StrEnum):
    IMAGE_GENERATION = "image_generation"
    IMAGE_EDIT = "image_edit"
    SPEECH_GENERATION = "speech_generation"
    SPEECH_TRANSCRIPTION = "speech_transcription"
    BACKGROUND_REMOVAL = "background_removal"
    COMPOSITION = "composition"
    UPLOAD_IMPORT = "upload_import"
    VISION_ANALYSIS = "vision_analysis"


class MediaJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MediaContextRole(StrEnum):
    SOURCE = "source"
    ATTACHMENT = "attachment"
    PREVIEW = "preview"
    OUTPUT = "output"
    EVIDENCE = "evidence"
    REFERENCE = "reference"


class MediaInputRole(StrEnum):
    SOURCE = "source"
    REFERENCE = "reference"
    MASK = "mask"
    BACKGROUND = "background"
    LAYER = "layer"
    AUDIO_SOURCE = "audio_source"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class MediaAssetCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    asset_kind: MediaAssetKind
    asset_role: MediaAssetRole
    source_kind: MediaSourceKind
    status: MediaAssetStatus = MediaAssetStatus.REGISTERED
    visibility: MediaVisibility = MediaVisibility.PRIVATE
    filename: str | None = Field(default=None, min_length=1, max_length=220)
    storage_uri: str | None = Field(default=None, min_length=1, max_length=500)
    preview_uri: str | None = Field(default=None, min_length=1, max_length=500)
    thumbnail_uri: str | None = Field(default=None, min_length=1, max_length=500)
    mime_type: str | None = Field(default=None, min_length=1, max_length=120)
    file_ext: str | None = Field(default=None, min_length=1, max_length=20)
    size_bytes: int | None = Field(default=None, ge=0)
    checksum_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    width: int | None = Field(default=None, ge=0)
    height: int | None = Field(default=None, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    sample_rate_hz: int | None = Field(default=None, ge=0)
    audio_channels: int | None = Field(default=None, ge=0)
    has_alpha: bool | None = None
    color_mode: str | None = Field(default=None, min_length=1, max_length=40)
    provider_kind: str | None = Field(default=None, min_length=1, max_length=64)
    source_job_id: uuid.UUID | None = None
    source_event_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("checksum_sha256", mode="after")
    @classmethod
    def validate_checksum(cls, value: str | None) -> str | None:
        if value is not None and CHECKSUM_PATTERN.fullmatch(value) is None:
            raise ValueError("checksum_sha256 must be a lowercase 64-character SHA-256 hex digest")
        return value

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "metadata")
        return value

    @model_validator(mode="after")
    def validate_media_shape(self) -> MediaAssetCreate:
        _validate_asset_metadata(self.asset_kind, self.mime_type, self.has_alpha)
        return self


class MediaAssetUpdate(_FrozenContract):
    visibility: MediaVisibility | None = None
    status: MediaAssetStatus | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            _assert_json_serializable(value, "metadata")
        return value


class MediaAssetRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    asset_kind: MediaAssetKind
    asset_role: MediaAssetRole
    source_kind: MediaSourceKind
    status: MediaAssetStatus
    visibility: MediaVisibility
    storage_uri: str | None = None
    preview_uri: str | None = None
    thumbnail_uri: str | None = None
    mime_type: str | None = None
    file_ext: str | None = None
    size_bytes: int | None = None
    checksum_sha256: str | None = None
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    sample_rate_hz: int | None = None
    audio_channels: int | None = None
    has_alpha: bool | None = None
    color_mode: str | None = None
    provider_kind: str | None = None
    source_job_id: uuid.UUID | None = None
    source_event_id: uuid.UUID | None = None
    title: str | None = None
    description: str | None = None
    created_by_actor_ref: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class MediaAssetListFilters(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    asset_kind: MediaAssetKind | None = None
    asset_role: MediaAssetRole | None = None
    status: MediaAssetStatus | None = None
    visibility: MediaVisibility | None = None
    limit: int = Field(default=100, ge=1, le=500)


class MediaContextCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    turn_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    world_event_id: uuid.UUID | None = None
    narrative_artifact_id: uuid.UUID | None = None
    context_role: MediaContextRole = MediaContextRole.ATTACHMENT
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "metadata")
        return value

    @model_validator(mode="after")
    def require_context(self) -> MediaContextCreate:
        if not any(
            (
                self.conversation_id,
                self.turn_id,
                self.agent_id,
                self.world_event_id,
                self.narrative_artifact_id,
            )
        ):
            raise ValueError("media context requires at least one reference")
        return self


class MediaContextRecord(MediaContextCreate):
    id: uuid.UUID
    asset_id: uuid.UUID
    worldline_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class MediaAssetInputCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    input_asset_id: uuid.UUID
    source_job_id: uuid.UUID | None = None
    input_role: MediaInputRole = MediaInputRole.SOURCE
    display_order: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "metadata")
        return value


class MediaAssetInputRecord(MediaAssetInputCreate):
    id: uuid.UUID
    output_asset_id: uuid.UUID
    worldline_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class MediaAssetReferences(_FrozenContract):
    asset_id: uuid.UUID
    contexts: list[MediaContextRecord]
    input_count: int
    output_count: int


class MediaAssetLineage(_FrozenContract):
    asset_id: uuid.UUID
    inputs: list[MediaAssetInputRecord]
    outputs: list[MediaAssetInputRecord]


class MediaJobCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    turn_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    job_kind: MediaJobKind
    provider_kind: str | None = Field(default=None, min_length=1, max_length=64)
    priority: int = Field(default=0, ge=0)
    cancel_policy: str | None = Field(default=None, min_length=1, max_length=40)
    deadline_hint: datetime | None = None
    dedupe_key: str | None = Field(default=None, min_length=1, max_length=160)
    invalidation_key: str | None = Field(default=None, min_length=1, max_length=160)
    request_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("deadline_hint", mode="after")
    @classmethod
    def normalize_deadline(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _utc(value)

    @field_validator("request_json", mode="after")
    @classmethod
    def validate_request_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "request_json")
        return value


class MediaJobRecord(MediaJobCreate):
    id: uuid.UUID
    worldline_id: uuid.UUID
    status: MediaJobStatus
    result_json: dict[str, Any]
    error_text: str | None = None
    created_by_actor_ref: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("started_at", "finished_at", "created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _utc(value)


def _validate_asset_metadata(
    asset_kind: MediaAssetKind,
    mime_type: str | None,
    has_alpha: bool | None,
) -> None:
    if mime_type is not None:
        allowed = IMAGE_MIME_TYPES if asset_kind == MediaAssetKind.IMAGE else AUDIO_MIME_TYPES
        if mime_type not in allowed:
            raise ValueError(f"mime_type is not allowed for {asset_kind.value} assets")
    if has_alpha is not None and asset_kind != MediaAssetKind.IMAGE:
        raise ValueError("has_alpha is only valid for image assets")


def _assert_json_serializable(value: dict[str, Any], field_name: str) -> None:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be JSON serializable") from exc


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
