from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from noveland.invocations.contracts import InvocationRecordView
from noveland.media.contracts import MediaAssetRecord, MediaJobRecord, MediaObjectRecord
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VoiceProfileStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


class VoiceProfileVisibility(StrEnum):
    PRIVATE = "private"
    WORLD_ADMIN = "world_admin"
    WORLD_MEMBER = "world_member"
    DEVELOPER_ONLY = "developer_only"
    HIDDEN = "hidden"


class VoiceProfileOwnerKind(StrEnum):
    WORLD = "world"
    AGENT = "agent"
    USER = "user"
    PROVIDER = "provider"
    OTHER = "other"


class VoiceKind(StrEnum):
    PRESET = "preset"
    CLONED = "cloned"
    DESIGNED = "designed"
    IMPORTED = "imported"
    GENERATED = "generated"
    EXTERNAL_PROVIDER = "external_provider"
    OTHER = "other"


class VoiceConsentStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    USER_OWNED_OR_AUTHORIZED = "user_owned_or_authorized"
    ADMIN_AUTHORIZED = "admin_authorized"
    PENDING_REVIEW = "pending_review"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class VoiceBindingRole(StrEnum):
    DEFAULT = "default"
    NARRATION = "narration"
    INNER_VOICE = "inner_voice"
    PHONE_CALL = "phone_call"
    DISGUISE = "disguise"
    ALTERNATE = "alternate"
    OTHER = "other"


class SpeechTranscriptStatus(StrEnum):
    AVAILABLE = "available"
    FAILED = "failed"
    DELETED = "deleted"


class SpeechTranscriptVisibility(StrEnum):
    PRIVATE = "private"
    WORLD_ADMIN = "world_admin"
    WORLD_MEMBER = "world_member"
    DEVELOPER_ONLY = "developer_only"
    HIDDEN = "hidden"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class VoiceProfileCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    profile_key: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: VoiceProfileStatus = VoiceProfileStatus.ACTIVE
    visibility: VoiceProfileVisibility = VoiceProfileVisibility.WORLD_ADMIN
    owner_kind: VoiceProfileOwnerKind = VoiceProfileOwnerKind.WORLD
    owner_agent_id: uuid.UUID | None = None
    provider_integration_id: uuid.UUID | None = None
    provider_voice_id: str | None = Field(default=None, min_length=1, max_length=200)
    default_language: str | None = Field(default=None, min_length=1, max_length=40)
    supported_languages: list[str] = Field(default_factory=list)
    voice_kind: VoiceKind = VoiceKind.PRESET
    reference_asset_id: uuid.UUID | None = None
    consent_status: VoiceConsentStatus = VoiceConsentStatus.NOT_REQUIRED
    usage_policy_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("profile_key", mode="after")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("profile_key must not be empty")
        return normalized

    @field_validator("supported_languages", mode="after")
    @classmethod
    def normalize_languages(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    @field_validator("usage_policy_json", "metadata_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "voice profile JSON")
        return value


class VoiceProfileUpdate(_FrozenContract):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: VoiceProfileStatus | None = None
    visibility: VoiceProfileVisibility | None = None
    provider_integration_id: uuid.UUID | None = None
    provider_voice_id: str | None = Field(default=None, min_length=1, max_length=200)
    default_language: str | None = Field(default=None, min_length=1, max_length=40)
    supported_languages: list[str] | None = None
    reference_asset_id: uuid.UUID | None = None
    consent_status: VoiceConsentStatus | None = None
    usage_policy_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None

    @field_validator("usage_policy_json", "metadata_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            _assert_json_serializable(value, "voice profile JSON")
        return value


class VoiceProfileRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None
    profile_key: str
    display_name: str
    description: str | None
    status: VoiceProfileStatus
    visibility: VoiceProfileVisibility
    owner_kind: VoiceProfileOwnerKind
    owner_agent_id: uuid.UUID | None
    provider_integration_id: uuid.UUID | None
    provider_voice_id: str | None
    default_language: str | None
    supported_languages: list[str]
    voice_kind: VoiceKind
    reference_asset_id: uuid.UUID | None
    consent_status: VoiceConsentStatus
    usage_policy_json: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class AgentVoiceProfileBindingCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    agent_id: uuid.UUID
    voice_profile_id: uuid.UUID
    binding_role: VoiceBindingRole = VoiceBindingRole.DEFAULT
    priority: int = Field(default=100, ge=0)
    is_default: bool = False
    style_overrides_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("style_overrides_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "style_overrides_json")
        return value


class AgentVoiceProfileBindingRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None
    agent_id: uuid.UUID
    voice_profile_id: uuid.UUID
    binding_role: VoiceBindingRole
    priority: int
    is_default: bool
    style_overrides_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class SpeechStyleMappingCreate(_FrozenContract):
    world_id: uuid.UUID
    mapping_key: str = Field(min_length=1, max_length=120)
    provider_kind: str = Field(min_length=1, max_length=80)
    emotion_key: str = Field(min_length=1, max_length=80)
    style_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("mapping_key", "provider_kind", "emotion_key", mode="after")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("mapping keys must not be empty")
        return normalized

    @field_validator("style_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "style_json")
        return value


class SpeechStyleMappingUpdate(_FrozenContract):
    style_json: dict[str, Any] | None = None

    @field_validator("style_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            _assert_json_serializable(value, "style_json")
        return value


class SpeechStyleMappingRead(SpeechStyleMappingCreate):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class TTSRequest(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    provider_id: uuid.UUID
    player_actor_id: uuid.UUID | None = None
    voice_profile_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    allow_provider_default_voice: bool = False
    text: str = Field(min_length=1)
    language: str | None = Field(default=None, min_length=1, max_length=40)
    emotion: str | None = Field(default=None, min_length=1, max_length=80)
    intensity: float | None = Field(default=None, ge=0.0, le=2.0)
    style_overrides_json: dict[str, Any] = Field(default_factory=dict)
    output_format: str = Field(default="wav", min_length=1, max_length=20)
    conversation_id: uuid.UUID | None = None
    turn_id: uuid.UUID | None = None
    media_job_id: uuid.UUID | None = None

    @field_validator("style_overrides_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "style_overrides_json")
        return value

    @model_validator(mode="after")
    def validate_voice_resolution(self) -> TTSRequest:
        if (
            self.voice_profile_id is None
            and self.agent_id is None
            and not self.allow_provider_default_voice
        ):
            raise ValueError(
                "voice_profile_id, agent_id, or allow_provider_default_voice is required"
            )
        return self


class TTSResult(_FrozenContract):
    media_job: MediaJobRecord
    output_asset: MediaAssetRecord
    output_objects: list[MediaObjectRecord]
    model_invocation: InvocationRecordView
    model_invocation_id: uuid.UUID


class STTRequest(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    provider_id: uuid.UUID
    player_actor_id: uuid.UUID | None = None
    source_asset_id: uuid.UUID
    language: str | None = Field(default=None, min_length=1, max_length=40)
    diarization: bool = False
    timestamps: bool = False
    conversation_id: uuid.UUID | None = None
    turn_id: uuid.UUID | None = None
    speaker_actor_ref: str | None = Field(default=None, min_length=1, max_length=160)


class STTResult(_FrozenContract):
    media_job: MediaJobRecord
    transcript: SpeechTranscriptRead
    model_invocation: InvocationRecordView
    model_invocation_id: uuid.UUID


class SpeechTranscriptCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    source_asset_id: uuid.UUID
    media_job_id: uuid.UUID | None = None
    model_invocation_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    turn_id: uuid.UUID | None = None
    speaker_actor_ref: str | None = Field(default=None, min_length=1, max_length=160)
    language: str | None = Field(default=None, min_length=1, max_length=40)
    transcript_text: str
    segments_json: list[dict[str, Any]] | None = None
    confidence_json: dict[str, Any] | None = None
    status: SpeechTranscriptStatus = SpeechTranscriptStatus.AVAILABLE
    visibility: SpeechTranscriptVisibility = SpeechTranscriptVisibility.WORLD_ADMIN

    @field_validator("segments_json", "confidence_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: Any) -> Any:
        _assert_json_serializable(value, "transcript JSON")
        return value


class SpeechTranscriptRead(SpeechTranscriptCreate):
    id: uuid.UUID
    worldline_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


def _assert_json_serializable(value: Any, field_name: str) -> None:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be JSON serializable") from exc


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
