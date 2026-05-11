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
CONTAINS_TEXT_MAX_LENGTH = 120


class MediaAssetKind(StrEnum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    OTHER = "other"


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
    VIDEO_CLIP = "video_clip"
    DOCUMENT = "document"
    THUMBNAIL = "thumbnail"
    OTHER = "other"


class MediaSourceKind(StrEnum):
    PROVIDER_GENERATED = "provider_generated"
    MANUAL_UPLOAD = "manual_upload"
    IMPORTED_ORIGINAL = "imported_original"
    COMPOSED = "composed"
    BACKGROUND_REMOVED = "background_removed"
    CROPPED = "cropped"
    CONVERTED = "converted"
    SYSTEM_GENERATED = "system_generated"
    TEST_FIXTURE = "test_fixture"
    OTHER = "other"


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
    TRANSCODE = "transcode"
    THUMBNAIL = "thumbnail"
    IMPORT = "import"
    OTHER = "other"


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


class MediaTagSourceKind(StrEnum):
    MANUAL = "manual"
    IMPORTED = "imported"
    SYSTEM = "system"
    PROVIDER = "provider"
    DERIVED = "derived"


class MediaCollectionStatus(StrEnum):
    ACTIVE = "active"
    DELETED = "deleted"


class MediaObjectRole(StrEnum):
    ORIGINAL = "original"
    PRIMARY = "primary"
    THUMBNAIL = "thumbnail"
    PREVIEW = "preview"
    MASK = "mask"
    ALPHA = "alpha"
    TRANSPARENT = "transparent"
    COMPOSED = "composed"
    WAVEFORM = "waveform"
    TRANSCRIPT_SOURCE = "transcript_source"
    DERIVED = "derived"
    OTHER = "other"


class MediaReferenceKind(StrEnum):
    CONVERSATION_TURN = "conversation_turn"
    CONVERSATION_SESSION = "conversation_session"
    WORLD_EVENT = "world_event"
    NARRATIVE_ARTIFACT = "narrative_artifact"
    AGENT = "agent"
    SCENE = "scene"
    WORLD = "world"
    MODEL_INVOCATION = "model_invocation"
    MEDIA_JOB = "media_job"
    MEMORY_WRITE_JOB = "memory_write_job"
    OTHER = "other"


class MediaReferenceRole(StrEnum):
    ATTACHMENT = "attachment"
    INPUT = "input"
    OUTPUT = "output"
    EVIDENCE = "evidence"
    PREVIEW = "preview"
    THUMBNAIL = "thumbnail"
    BACKGROUND = "background"
    FOREGROUND = "foreground"
    CHARACTER_SPRITE = "character_sprite"
    VOICE_REFERENCE = "voice_reference"
    SOURCE = "source"
    DERIVED_FROM = "derived_from"
    OTHER = "other"


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
    source_invocation_id: uuid.UUID | None = None
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
    source_invocation_id: uuid.UUID | None = None
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
    source_kind: MediaSourceKind | None = None
    status: MediaAssetStatus | None = None
    visibility: MediaVisibility | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    source_event_id: uuid.UUID | None = None
    source_invocation_id: uuid.UUID | None = None
    ref_kind: MediaReferenceKind | None = None
    ref_id: uuid.UUID | None = None
    contains_text: str | None = Field(default=None, max_length=CONTAINS_TEXT_MAX_LENGTH)
    limit: int = Field(default=100, ge=1, le=500)

    @field_validator("created_after", "created_before", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)

    @field_validator("contains_text", mode="after")
    @classmethod
    def normalize_contains_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("contains_text must not be empty")
        return normalized


class MediaAssetTagFilter(_FrozenContract):
    tag_type: str = Field(min_length=1, max_length=40)
    tag_key: str = Field(min_length=1, max_length=80)
    tag_value: str = Field(min_length=1, max_length=220)

    @field_validator("tag_type", "tag_key", mode="after")
    @classmethod
    def normalize_type_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("tag_type and tag_key must not be empty")
        if ":" in normalized:
            raise ValueError("tag_type and tag_key must not contain ':'")
        return normalized

    @field_validator("tag_value", mode="after")
    @classmethod
    def normalize_value(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("tag_value must not be empty")
        return normalized

    @classmethod
    def parse(cls, encoded: str) -> MediaAssetTagFilter:
        pieces = encoded.split(":", 2)
        if len(pieces) != 3:
            raise ValueError("tag filter must use tag_type:tag_key:tag_value")
        return cls(tag_type=pieces[0], tag_key=pieces[1], tag_value=pieces[2])


class MediaAssetTagCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    tag_type: str = Field(min_length=1, max_length=40)
    tag_key: str = Field(min_length=1, max_length=80)
    tag_value: str = Field(min_length=1, max_length=220)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_kind: MediaTagSourceKind = MediaTagSourceKind.MANUAL
    visibility: MediaVisibility = MediaVisibility.WORLD_ADMIN
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tag_type", "tag_key", mode="after")
    @classmethod
    def normalize_type_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("tag_type and tag_key must not be empty")
        if ":" in normalized:
            raise ValueError("tag_type and tag_key must not contain ':'")
        return normalized

    @field_validator("tag_value", mode="after")
    @classmethod
    def normalize_value(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("tag_value must not be empty")
        return normalized

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "metadata")
        return value


class MediaAssetTagUpdate(_FrozenContract):
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    visibility: MediaVisibility | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            _assert_json_serializable(value, "metadata")
        return value


class MediaAssetTagRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    asset_id: uuid.UUID
    tag_type: str
    tag_key: str
    tag_value: str
    confidence: float
    source_kind: MediaTagSourceKind
    visibility: MediaVisibility
    created_by_actor_ref: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class MediaAssetCollectionCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    collection_kind: str = Field(min_length=1, max_length=60)
    title: str = Field(min_length=1, max_length=160)
    description: str | None = None
    owner_agent_id: uuid.UUID | None = None
    visibility: MediaVisibility = MediaVisibility.WORLD_ADMIN
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("collection_kind", mode="after")
    @classmethod
    def normalize_collection_kind(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("collection_kind must not be empty")
        return normalized

    @field_validator("title", mode="after")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title must not be empty")
        return normalized

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "metadata")
        return value


class MediaAssetCollectionUpdate(_FrozenContract):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    visibility: MediaVisibility | None = None
    status: MediaCollectionStatus | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("title", mode="after")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("title must not be empty")
        return normalized

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            _assert_json_serializable(value, "metadata")
        return value


class MediaAssetCollectionRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    collection_kind: str
    title: str
    description: str | None = None
    owner_agent_id: uuid.UUID | None = None
    visibility: MediaVisibility
    status: MediaCollectionStatus
    created_by_actor_ref: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class MediaAssetCollectionItemCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    asset_id: uuid.UUID
    role: str = Field(default="member", min_length=1, max_length=40)
    display_order: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("role", mode="after")
    @classmethod
    def normalize_role(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("role must not be empty")
        return normalized

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "metadata")
        return value


class MediaAssetCollectionItemUpdate(_FrozenContract):
    display_order: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] | None = None

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            _assert_json_serializable(value, "metadata")
        return value


class MediaAssetCollectionItemRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    collection_id: uuid.UUID
    asset_id: uuid.UUID
    role: str
    display_order: int
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class MediaAssetSearchFilters(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    asset_kind: MediaAssetKind | None = None
    asset_role: MediaAssetRole | None = None
    source_kind: MediaSourceKind | None = None
    status: MediaAssetStatus | None = None
    visibility: MediaVisibility | None = None
    has_alpha: bool | None = None
    mime_type: str | None = Field(default=None, min_length=1, max_length=120)
    provider_kind: str | None = Field(default=None, min_length=1, max_length=64)
    used_by_agent_id: uuid.UUID | None = None
    used_in_conversation_id: uuid.UUID | None = None
    used_in_turn_id: uuid.UUID | None = None
    used_in_world_event_id: uuid.UUID | None = None
    collection_id: uuid.UUID | None = None
    contains_text: str | None = Field(default=None, max_length=CONTAINS_TEXT_MAX_LENGTH)
    tags: tuple[MediaAssetTagFilter, ...] = ()
    limit: int = Field(default=100, ge=1, le=500)

    @field_validator("contains_text", mode="after")
    @classmethod
    def normalize_contains_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("contains_text must not be empty")
        if len(normalized) > CONTAINS_TEXT_MAX_LENGTH:
            raise ValueError("contains_text is too long")
        return normalized


class MediaAssetSearchResult(_FrozenContract):
    assets: list[MediaAssetRecord]


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


class MediaObjectCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    object_role: MediaObjectRole = MediaObjectRole.ORIGINAL
    storage_uri: str = Field(min_length=1, max_length=500)
    filename: str | None = Field(default=None, min_length=1, max_length=220)
    mime_type: str = Field(min_length=1, max_length=120)
    size_bytes: int = Field(ge=0)
    checksum_sha256: str = Field(min_length=64, max_length=64)
    width: int | None = Field(default=None, ge=0)
    height: int | None = Field(default=None, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    sample_rate_hz: int | None = Field(default=None, ge=0)
    audio_channels: int | None = Field(default=None, ge=0)
    frame_rate: float | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("checksum_sha256", mode="after")
    @classmethod
    def validate_checksum(cls, value: str) -> str:
        if CHECKSUM_PATTERN.fullmatch(value) is None:
            raise ValueError("checksum_sha256 must be a lowercase 64-character SHA-256 hex digest")
        return value

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "metadata")
        return value


class MediaObjectRecord(_FrozenContract):
    id: uuid.UUID
    asset_id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    object_role: MediaObjectRole
    storage_uri: str
    filename: str | None = None
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    sample_rate_hz: int | None = None
    audio_channels: int | None = None
    frame_rate: float | None = None
    metadata: dict[str, Any]
    created_at: datetime

    @field_validator("created_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class MediaAssetUploadRequest(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    asset_kind: MediaAssetKind
    asset_role: MediaAssetRole
    visibility: MediaVisibility = MediaVisibility.PRIVATE
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "metadata")
        return value


class MediaAssetUploadResponse(_FrozenContract):
    asset: MediaAssetRecord
    object: MediaObjectRecord


class MediaReferenceCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    asset_id: uuid.UUID
    ref_kind: MediaReferenceKind
    ref_id: uuid.UUID
    ref_role: MediaReferenceRole = MediaReferenceRole.ATTACHMENT
    display_order: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "metadata")
        return value


class MediaReferenceRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    asset_id: uuid.UUID
    ref_kind: MediaReferenceKind
    ref_id: uuid.UUID
    ref_role: MediaReferenceRole
    display_order: int
    metadata: dict[str, Any]
    created_at: datetime

    @field_validator("created_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class MediaReferenceListFilters(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    asset_id: uuid.UUID | None = None
    ref_kind: MediaReferenceKind | None = None
    ref_id: uuid.UUID | None = None
    ref_role: MediaReferenceRole | None = None
    limit: int = Field(default=100, ge=1, le=500)


class ConversationTurnMediaAttachmentCreate(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    asset_id: uuid.UUID
    attachment_role: MediaReferenceRole = MediaReferenceRole.ATTACHMENT
    display_order: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "metadata")
        return value


class ConversationTurnMediaAttachmentRecord(_FrozenContract):
    asset: MediaAssetRecord
    reference: MediaReferenceRecord | None = None
    legacy_context: MediaContextRecord | None = None


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
    tags: list[MediaAssetTagRecord] = Field(default_factory=list)
    collections: list[MediaAssetCollectionRecord] = Field(default_factory=list)
    input_count: int
    output_count: int
    tag_count: int = 0
    collection_count: int = 0


class MediaAssetLineage(_FrozenContract):
    asset_id: uuid.UUID
    inputs: list[MediaAssetInputRecord]
    outputs: list[MediaAssetInputRecord]
    related_assets: list[MediaAssetRecord] = Field(default_factory=list)


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
    source_event_id: uuid.UUID | None = None
    source_invocation_id: uuid.UUID | None = None
    provider_config_json: dict[str, Any] = Field(default_factory=dict)
    request_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("deadline_hint", mode="after")
    @classmethod
    def normalize_deadline(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _utc(value)

    @field_validator("provider_config_json", "request_json", mode="after")
    @classmethod
    def validate_request_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "media job JSON")
        return value


class MediaJobUpdate(_FrozenContract):
    status: MediaJobStatus | None = None
    priority: int | None = Field(default=None, ge=0)
    cancel_policy: str | None = Field(default=None, min_length=1, max_length=40)
    deadline_hint: datetime | None = None
    provider_kind: str | None = Field(default=None, min_length=1, max_length=64)
    provider_config_json: dict[str, Any] | None = None
    request_json: dict[str, Any] | None = None
    result_json: dict[str, Any] | None = None
    error_text: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @field_validator("deadline_hint", "started_at", "finished_at", mode="after")
    @classmethod
    def normalize_datetimes(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)

    @field_validator("provider_config_json", "request_json", "result_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            _assert_json_serializable(value, "media job update JSON")
        return value


class MediaJobListFilters(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    job_kind: MediaJobKind | None = None
    status: MediaJobStatus | None = None
    priority_min: int | None = Field(default=None, ge=0)
    priority_max: int | None = Field(default=None, ge=0)
    agent_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    turn_id: uuid.UUID | None = None
    source_event_id: uuid.UUID | None = None
    source_invocation_id: uuid.UUID | None = None
    provider_kind: str | None = Field(default=None, min_length=1, max_length=64)
    invalidation_key: str | None = Field(default=None, min_length=1, max_length=160)
    created_after: datetime | None = None
    created_before: datetime | None = None
    limit: int = Field(default=100, ge=1, le=500)

    @field_validator("created_after", "created_before", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)


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
        if asset_kind == MediaAssetKind.IMAGE:
            allowed: set[str] | None = IMAGE_MIME_TYPES
        elif asset_kind == MediaAssetKind.AUDIO:
            allowed = AUDIO_MIME_TYPES
        else:
            allowed = None
        if allowed is not None and mime_type not in allowed:
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
