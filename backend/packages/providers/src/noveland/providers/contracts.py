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


class ProviderBudgetPolicyStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


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
    auth_ref: str | None = None
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


class ProviderReliabilityMode(StrEnum):
    NORMAL = "normal"
    AT_RISK = "at_risk"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class ProviderFallbackMode(StrEnum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class ProviderReliabilityProviderRef(_FrozenContract):
    id: uuid.UUID
    provider_key: str
    provider_kind: ProviderKind
    adapter_kind: ProviderAdapterKind
    status: ProviderIntegrationStatus
    auth_ref_configured: bool


class ProviderReliabilityEvidenceRef(_FrozenContract):
    evidence_kind: str = Field(min_length=1, max_length=80)
    ref_id: uuid.UUID | None = None
    status: str | None = Field(default=None, max_length=40)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "provider reliability evidence JSON")
        return value


class ProviderReliabilityReportRead(_FrozenContract):
    provider: ProviderReliabilityProviderRef
    reliability_mode: ProviderReliabilityMode
    degraded_mode_active: bool
    recent_health_count: int = Field(ge=0)
    recent_unhealthy_count: int = Field(ge=0)
    recent_degraded_count: int = Field(ge=0)
    recent_failed_invocation_count: int = Field(ge=0)
    manual_fallback_enabled: bool
    automatic_fallback_enabled: bool = False
    fallback_provider_ids: tuple[uuid.UUID, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[ProviderReliabilityEvidenceRef, ...] = Field(default_factory=tuple)
    blocked_reasons: tuple[str, ...] = Field(default_factory=tuple)


class ProviderFallbackPlanRequest(_FrozenContract):
    fallback_provider_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    capability_key: str | None = Field(default=None, min_length=1, max_length=120)
    player_actor_id: uuid.UUID | None = None
    fallback_mode: ProviderFallbackMode = ProviderFallbackMode.MANUAL
    reason: str | None = Field(default=None, min_length=1, max_length=240)


class ProviderFallbackPlanRead(_FrozenContract):
    allowed: bool
    primary_provider: ProviderReliabilityProviderRef
    fallback_provider: ProviderReliabilityProviderRef | None = None
    fallback_mode: ProviderFallbackMode
    capability_key: str
    degraded_mode_active: bool
    quota_checked: bool
    auth_checked: bool
    audit_required: bool = True
    automatic_fallback_enabled: bool = False
    blocked_reasons: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[ProviderReliabilityEvidenceRef, ...] = Field(default_factory=tuple)
    audit_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("audit_metadata", mode="after")
    @classmethod
    def validate_audit_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "provider fallback audit metadata")
        return value


class ProviderMediaJobRequeueRequest(_FrozenContract):
    reason: str | None = Field(default=None, min_length=1, max_length=240)


class ProviderMediaJobRequeueResult(_FrozenContract):
    original_job: MediaJobRecord
    requeued_job: MediaJobRecord
    audit_metadata: dict[str, Any]
    provider_execution: bool = False

    @field_validator("audit_metadata", mode="after")
    @classmethod
    def validate_requeue_audit_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "provider requeue audit metadata")
        return value


class ProviderBudgetPolicyCreate(_FrozenContract):
    world_id: uuid.UUID
    provider_id: uuid.UUID | None = None
    policy_key: str = Field(min_length=1, max_length=120)
    status: ProviderBudgetPolicyStatus = ProviderBudgetPolicyStatus.ACTIVE
    emergency_stop_enabled: bool = False
    limits_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("policy_key", mode="after")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized == "":
            raise ValueError("policy_key must not be empty")
        return normalized

    @field_validator("limits_json", "metadata_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "provider budget policy JSON")
        return value


class ProviderBudgetPolicyUpdate(_FrozenContract):
    status: ProviderBudgetPolicyStatus | None = None
    emergency_stop_enabled: bool | None = None
    limits_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None

    @field_validator("limits_json", "metadata_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            _assert_json_serializable(value, "provider budget policy JSON")
        return value


class ProviderBudgetPolicyRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    provider_id: uuid.UUID | None
    policy_key: str
    status: ProviderBudgetPolicyStatus
    emergency_stop_enabled: bool
    limits_json: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class ProviderQuotaStatusRead(_FrozenContract):
    world_id: uuid.UUID
    provider_id: uuid.UUID | None = None
    player_actor_id: uuid.UUID | None = None
    capability_key: str | None = None
    emergency_stop_active: bool
    blocked_reasons: list[str] = Field(default_factory=list)
    active_policy_ids: list[uuid.UUID] = Field(default_factory=list)
    daily_invocation_count: int = Field(ge=0)
    daily_media_job_count: int = Field(ge=0)
    daily_estimated_cost: float = Field(ge=0)
    limits_json: dict[str, Any] = Field(default_factory=dict)


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
    player_actor_id: uuid.UUID | None = None
    actor_ref: str | None = Field(default=None, min_length=1, max_length=160)
    platform_admin: bool = True
    fallback_provider_id: uuid.UUID | None = None
    fallback_mode: ProviderFallbackMode = ProviderFallbackMode.MANUAL
    fallback_reason: str | None = Field(default=None, min_length=1, max_length=240)

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
    player_actor_id: uuid.UUID | None = None
    fallback_provider_id: uuid.UUID | None = None
    fallback_mode: ProviderFallbackMode = ProviderFallbackMode.MANUAL
    fallback_reason: str | None = Field(default=None, min_length=1, max_length=240)

    @field_validator("input_json", "request_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "provider test invocation JSON")
        return value


class ProviderTestInvocationResult(ProviderExecutionResult):
    pass


class ProviderSmokeTestRequest(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    capability_key: str | None = Field(default=None, min_length=1, max_length=120)
    input_text: str | None = None
    input_json: dict[str, Any] = Field(default_factory=dict)
    request_json: dict[str, Any] = Field(default_factory=dict)
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    media_job_id: uuid.UUID | None = None
    media_asset_id: uuid.UUID | None = None
    player_actor_id: uuid.UUID | None = None
    fallback_provider_id: uuid.UUID | None = None
    fallback_mode: ProviderFallbackMode = ProviderFallbackMode.MANUAL
    fallback_reason: str | None = Field(default=None, min_length=1, max_length=240)

    @field_validator("input_json", "request_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "provider smoke test JSON")
        return value


class ProviderSmokeTestResult(ProviderExecutionResult):
    smoke_status: str


class ProviderTemplateRead(_FrozenContract):
    template_key: str
    display_name: str
    provider_kind: ProviderKind
    adapter_kind: ProviderAdapterKind
    description: str
    base_url_placeholder: str | None = None
    model_name_placeholder: str | None = None
    auth_ref_placeholder: str | None = None
    config_json: dict[str, Any] = Field(default_factory=dict)
    default_params_json: dict[str, Any] = Field(default_factory=dict)
    capabilities: tuple[ProviderCapabilityCreate, ...] = ()
    model_discovery: dict[str, Any] = Field(default_factory=dict)


class ProviderModelDiscoveryRequest(_FrozenContract):
    provider_id: uuid.UUID | None = None
    provider_kind: ProviderKind | None = None
    adapter_kind: ProviderAdapterKind | None = None
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    auth_ref: str | None = Field(default=None, min_length=1, max_length=200)
    config_json: dict[str, Any] = Field(default_factory=dict)
    default_params_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("config_json", "default_params_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "provider model discovery JSON")
        return value


class ProviderModelDiscoveryRead(_FrozenContract):
    provider_id: uuid.UUID | None = None
    provider_kind: ProviderKind
    adapter_kind: ProviderAdapterKind
    discovery_status: str
    models: list[str] = Field(default_factory=list)
    manual_fallback_allowed: bool = True
    error_code: str | None = None
    error_message: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


def _assert_json_serializable(value: dict[str, Any], field_name: str) -> None:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be JSON serializable") from exc


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
