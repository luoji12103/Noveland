from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from noveland.invocations.contracts import InvocationRecordView
from noveland.media.contracts import MediaAssetRecord, MediaJobRecord, MediaObjectRecord
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProviderScopeKind(StrEnum):
    GLOBAL = "global"
    WORLD = "world"


class ProviderKind(StrEnum):
    TEXT_GENERATION = "text_generation"
    IMAGE_GENERATION = "image_generation"
    IMAGE_EDITING = "image_editing"
    IMAGE_ANALYSIS = "image_analysis"
    IMAGE_COMPOSITION = "image_composition"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_SPEECH = "text_to_speech"
    VOICE_CLONING = "voice_cloning"
    BACKGROUND_REMOVAL = "background_removal"
    WORKFLOW_ENGINE = "workflow_engine"
    EMBEDDING = "embedding"
    RERANKER = "reranker"
    OTHER = "other"


class ProviderAdapterKind(StrEnum):
    FAKE = "fake"
    OPENAI = "openai"
    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC = "anthropic"
    ANTHROPIC_COMPATIBLE = "anthropic_compatible"
    COMFYUI = "comfyui"
    MIMO_TTS = "mimo_tts"
    MIMO_ASR = "mimo_asr"
    OMNIVOICE = "omnivoice"
    GPT_SOVITS = "gpt_sovits"
    REMBG = "rembg"
    SAM2 = "sam2"
    CUSTOM_HTTP = "custom_http"
    LOCAL_STUB = "local_stub"
    OTHER = "other"


class ProviderIntegrationStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


class ProviderVisibility(StrEnum):
    PRIVATE = "private"
    WORLD_ADMIN = "world_admin"
    DEVELOPER_ONLY = "developer_only"
    HIDDEN = "hidden"


class ProviderHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class ProviderCapabilityCreate(_FrozenContract):
    capability_key: str = Field(min_length=1, max_length=120)
    capability_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("capability_key", mode="after")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        normalized = value.strip()
        if normalized == "":
            raise ValueError("capability_key must not be empty")
        return normalized

    @field_validator("capability_json", mode="after")
    @classmethod
    def validate_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "capability_json")
        return value


class ProviderIntegrationCreate(_FrozenContract):
    world_id: uuid.UUID | None = None
    scope_kind: ProviderScopeKind
    provider_kind: ProviderKind
    adapter_kind: ProviderAdapterKind
    provider_key: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=200)
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    auth_ref: str | None = Field(default=None, min_length=1, max_length=200)
    config_json: dict[str, Any] = Field(default_factory=dict)
    default_params_json: dict[str, Any] = Field(default_factory=dict)
    status: ProviderIntegrationStatus = ProviderIntegrationStatus.ACTIVE
    visibility: ProviderVisibility = ProviderVisibility.WORLD_ADMIN
    capabilities: tuple[ProviderCapabilityCreate, ...] = ()

    @field_validator("provider_key", mode="after")
    @classmethod
    def normalize_provider_key(cls, value: str) -> str:
        normalized = value.strip()
        if normalized == "":
            raise ValueError("provider_key must not be empty")
        return normalized

    @field_validator("config_json", "default_params_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "provider integration JSON")
        return value

    @model_validator(mode="after")
    def validate_scope(self) -> ProviderIntegrationCreate:
        if self.scope_kind == ProviderScopeKind.GLOBAL and self.world_id is not None:
            raise ValueError("global providers must not include world_id")
        if self.scope_kind == ProviderScopeKind.WORLD and self.world_id is None:
            raise ValueError("world providers require world_id")
        return self


class ProviderIntegrationUpdate(_FrozenContract):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    auth_ref: str | None = Field(default=None, min_length=1, max_length=200)
    config_json: dict[str, Any] | None = None
    default_params_json: dict[str, Any] | None = None
    status: ProviderIntegrationStatus | None = None
    visibility: ProviderVisibility | None = None
    capabilities: tuple[ProviderCapabilityCreate, ...] | None = None

    @field_validator("config_json", "default_params_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            _assert_json_serializable(value, "provider integration JSON")
        return value


class ProviderIntegrationListFilters(_FrozenContract):
    scope_kind: ProviderScopeKind | None = None
    provider_kind: ProviderKind | None = None
    adapter_kind: ProviderAdapterKind | None = None
    status: ProviderIntegrationStatus | None = None
    visibility: ProviderVisibility | None = None
    capability_key: str | None = Field(default=None, min_length=1, max_length=120)
    include_global: bool = True
    include_hidden: bool = False
    limit: int = Field(default=100, ge=1, le=500)


class ProviderIntegrationRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID | None
    scope_kind: ProviderScopeKind
    scope_key: str
    provider_kind: ProviderKind
    adapter_kind: ProviderAdapterKind
    provider_key: str
    display_name: str
    base_url: str | None
    auth_ref_configured: bool
    config_json: dict[str, Any]
    default_params_json: dict[str, Any]
    status: ProviderIntegrationStatus
    visibility: ProviderVisibility
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class ProviderCapabilityRead(ProviderCapabilityCreate):
    id: uuid.UUID
    provider_integration_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class ProviderHealthCheckRead(_FrozenContract):
    id: uuid.UUID
    provider_integration_id: uuid.UUID
    status: ProviderHealthStatus
    latency_ms: int | None
    checked_at: datetime
    error_text: str | None
    metadata_json: dict[str, Any]

    @field_validator("checked_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class ProviderExecutionRequest(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    provider_id: uuid.UUID | None = None
    provider_kind: ProviderKind | None = None
    capability_key: str | None = Field(default=None, min_length=1, max_length=120)
    input_text: str | None = None
    input_json: dict[str, Any] = Field(default_factory=dict)
    request_json: dict[str, Any] = Field(default_factory=dict)
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    media_job_id: uuid.UUID | None = None
    media_asset_id: uuid.UUID | None = None
    actor_ref: str | None = Field(default=None, min_length=1, max_length=160)

    @field_validator("input_json", "request_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "provider execution JSON")
        return value

    @model_validator(mode="after")
    def validate_provider_selection(self) -> ProviderExecutionRequest:
        if self.provider_id is None and self.provider_kind is None and self.capability_key is None:
            raise ValueError("provider_id, provider_kind, or capability_key is required")
        return self


class ProviderExecutionResult(_FrozenContract):
    provider: ProviderIntegrationRead
    invocation: InvocationRecordView
    output_text: str | None = None
    output_json: dict[str, Any] = Field(default_factory=dict)
    media_job: MediaJobRecord | None = None
    output_asset: MediaAssetRecord | None = None
    output_objects: list[MediaObjectRecord] = Field(default_factory=list)


class ProviderTestInvocationRequest(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    provider_id: uuid.UUID | None = None
    provider_kind: ProviderKind | None = None
    capability_key: str | None = Field(default=None, min_length=1, max_length=120)
    input_text: str | None = None
    input_json: dict[str, Any] = Field(default_factory=dict)
    request_json: dict[str, Any] = Field(default_factory=dict)
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    media_job_id: uuid.UUID | None = None
    media_asset_id: uuid.UUID | None = None

    @field_validator("input_json", "request_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "provider test invocation JSON")
        return value


class ProviderTestInvocationResult(ProviderExecutionResult):
    pass


def _assert_json_serializable(value: dict[str, Any], field_name: str) -> None:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be JSON serializable") from exc


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
