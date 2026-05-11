from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CONTAINS_TEXT_MAX_LENGTH = 200


class InvocationKind(StrEnum):
    AGENT_RUNTIME = "agent_runtime"
    CONVERSATION_TURN = "conversation_turn"
    NARRATIVE_GENERATION = "narrative_generation"
    GM_GENERATION = "gm_generation"
    EVAL = "eval"
    IMAGE_GENERATION = "image_generation"
    IMAGE_EDIT = "image_edit"
    IMAGE_ANALYSIS = "image_analysis"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_SPEECH = "text_to_speech"
    VOICE_CLONE = "voice_clone"
    TOOL_PLANNING = "tool_planning"
    REPAIR = "repair"
    CRITIQUE = "critique"
    OTHER = "other"


class InvocationActorKind(StrEnum):
    SYSTEM = "system"
    PLATFORM_ADMIN = "platform_admin"
    WORLD_ADMIN = "world_admin"
    AGENT = "agent"
    PLAYER = "player"
    RUNTIME = "runtime"
    SERVICE = "service"


class InvocationProviderKind(StrEnum):
    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC_COMPATIBLE = "anthropic_compatible"
    OPENAI_IMAGE = "openai_image"
    OPENAI_AUDIO = "openai_audio"
    CUSTOM_HTTP = "custom_http"
    COMFYUI = "comfyui"
    MIMO_TTS = "mimo_tts"
    MIMO_ASR = "mimo_asr"
    OMNIVOICE = "omnivoice"
    GPT_SOVITS = "gpt_sovits"
    LOCAL_STUB = "local_stub"
    OTHER = "other"


class InvocationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REDACTED = "redacted"


class InvocationVisibility(StrEnum):
    PRIVATE = "private"
    WORLD_ADMIN = "world_admin"
    DEVELOPER_ONLY = "developer_only"
    HIDDEN = "hidden"


class InvocationRedactionStatus(StrEnum):
    RAW = "raw"
    REDACTED = "redacted"
    HIDDEN = "hidden"
    CHECKSUM_ONLY = "checksum_only"


class InvocationRetentionPolicy(StrEnum):
    LOCAL_DEBUG = "local_debug"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EVAL_ONLY = "eval_only"
    PURGE_AFTER_DAYS = "purge_after_days"


class PromptTemplateScopeKind(StrEnum):
    GLOBAL = "global"
    WORLD = "world"


class PromptTemplateStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class InvocationRole(StrEnum):
    PRIMARY = "primary"
    RETRY = "retry"
    FALLBACK = "fallback"
    REPAIR = "repair"
    CRITIQUE = "critique"
    TOOL_PLANNING = "tool_planning"
    VISION_ANALYSIS = "vision_analysis"
    IMAGE_GENERATION = "image_generation"
    SPEECH_GENERATION = "speech_generation"
    OTHER = "other"


class RedactionMode(StrEnum):
    CLEAR_RAW_PAYLOADS = "clear_raw_payloads"
    CHECKSUM_ONLY = "checksum_only"
    HIDE = "hide"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class PromptSnapshotCreate(_FrozenContract):
    template_id: uuid.UUID | None = None
    template_key: str | None = Field(default=None, min_length=1, max_length=120)
    template_version: int | None = Field(default=None, ge=1)
    raw_prompt_text: str | None = None
    raw_messages_json: list[dict[str, Any]] | None = None
    raw_request_json: dict[str, Any] | None = None
    raw_response_json: dict[str, Any] | None = None
    raw_output_text: str | None = None
    normalized_output_json: dict[str, Any] | None = None
    prompt_context_snapshot_json: dict[str, Any] | None = None
    tool_definitions_json: dict[str, Any] | None = None
    context_pack_refs_json: dict[str, Any] | None = None
    input_asset_refs_json: list[dict[str, Any]] | None = None
    visibility: InvocationVisibility = InvocationVisibility.WORLD_ADMIN
    redaction_status: InvocationRedactionStatus = InvocationRedactionStatus.RAW
    contains_sensitive_context: bool = False

    @field_validator(
        "raw_messages_json",
        "raw_request_json",
        "raw_response_json",
        "normalized_output_json",
        "prompt_context_snapshot_json",
        "tool_definitions_json",
        "context_pack_refs_json",
        "input_asset_refs_json",
        mode="after",
    )
    @classmethod
    def validate_json_values(cls, value: Any) -> Any:
        _assert_json_serializable(value, "prompt snapshot JSON")
        return value


class InvocationRecordCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    trace_id: uuid.UUID | None = None
    parent_invocation_id: uuid.UUID | None = None
    invocation_kind: InvocationKind
    actor_kind: InvocationActorKind
    actor_ref: str | None = Field(default=None, min_length=1, max_length=160)
    agent_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    turn_id: uuid.UUID | None = None
    world_event_id: uuid.UUID | None = None
    media_job_id: uuid.UUID | None = None
    media_asset_id: uuid.UUID | None = None
    memory_write_job_id: uuid.UUID | None = None
    provider_kind: InvocationProviderKind
    provider_profile_id: uuid.UUID | None = None
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    model_version: str | None = Field(default=None, min_length=1, max_length=80)
    prompt_template_key: str | None = Field(default=None, min_length=1, max_length=120)
    prompt_template_version: int | None = Field(default=None, ge=1)
    input_text: str | None = None
    output_text: str | None = None
    input_json: dict[str, Any] | None = None
    output_json: dict[str, Any] | None = None
    request_params_json: dict[str, Any] | None = None
    response_metadata_json: dict[str, Any] | None = None
    usage_json: dict[str, Any] | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    estimated_cost: Decimal | None = Field(default=None, ge=Decimal("0"))
    status: InvocationStatus = InvocationStatus.PENDING
    error_text: str | None = None
    visibility: InvocationVisibility = InvocationVisibility.WORLD_ADMIN
    redaction_status: InvocationRedactionStatus = InvocationRedactionStatus.RAW
    retention_policy: InvocationRetentionPolicy = InvocationRetentionPolicy.LOCAL_DEBUG
    contains_sensitive_context: bool = False
    purge_after: datetime | None = None
    prompt_snapshot: PromptSnapshotCreate | None = None

    @field_validator("purge_after", mode="after")
    @classmethod
    def normalize_purge_after(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)

    @field_validator(
        "input_json",
        "output_json",
        "request_params_json",
        "response_metadata_json",
        "usage_json",
        mode="after",
    )
    @classmethod
    def validate_json_values(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        _assert_json_serializable(value, "invocation JSON")
        return value


class InvocationStatusUpdate(_FrozenContract):
    status: InvocationStatus
    output_text: str | None = None
    output_json: dict[str, Any] | None = None
    response_metadata_json: dict[str, Any] | None = None
    usage_json: dict[str, Any] | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    estimated_cost: Decimal | None = Field(default=None, ge=Decimal("0"))
    error_text: str | None = None

    @field_validator(
        "output_json",
        "response_metadata_json",
        "usage_json",
        mode="after",
    )
    @classmethod
    def validate_json_values(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        _assert_json_serializable(value, "invocation status JSON")
        return value


class PromptSnapshotUpdate(_FrozenContract):
    raw_response_json: dict[str, Any] | None = None
    raw_output_text: str | None = None
    normalized_output_json: dict[str, Any] | None = None

    @field_validator("raw_response_json", "normalized_output_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        _assert_json_serializable(value, "prompt snapshot update JSON")
        return value


class InvocationRedactRequest(_FrozenContract):
    redaction_status: InvocationRedactionStatus
    reason: str = Field(min_length=1, max_length=200)
    mode: RedactionMode


class InvocationTagFilter(_FrozenContract):
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
    def parse(cls, encoded: str) -> InvocationTagFilter:
        pieces = encoded.split(":", 2)
        if len(pieces) != 3:
            raise ValueError("tag filter must use tag_type:tag_key:tag_value")
        return cls(tag_type=pieces[0], tag_key=pieces[1], tag_value=pieces[2])


class InvocationTagCreate(InvocationTagFilter):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    invocation_id: uuid.UUID


class InvocationSearchFilters(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    trace_id: uuid.UUID | None = None
    parent_invocation_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    turn_id: uuid.UUID | None = None
    world_event_id: uuid.UUID | None = None
    media_job_id: uuid.UUID | None = None
    media_asset_id: uuid.UUID | None = None
    memory_write_job_id: uuid.UUID | None = None
    invocation_kind: InvocationKind | None = None
    provider_kind: InvocationProviderKind | None = None
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    status: InvocationStatus | None = None
    visibility: InvocationVisibility | None = None
    redaction_status: InvocationRedactionStatus | None = None
    retention_policy: InvocationRetentionPolicy | None = None
    contains_sensitive_context: bool | None = None
    contains_text: str | None = Field(default=None, max_length=CONTAINS_TEXT_MAX_LENGTH)
    tags: tuple[InvocationTagFilter, ...] = ()
    limit: int = Field(default=50, ge=1, le=200)
    cursor: datetime | None = None
    order: SortOrder = SortOrder.DESC

    @field_validator("created_after", "created_before", "cursor", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)

    @field_validator("contains_text", mode="after")
    @classmethod
    def normalize_contains_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if normalized == "":
            raise ValueError("contains_text must not be empty")
        if len(normalized) > CONTAINS_TEXT_MAX_LENGTH:
            raise ValueError("contains_text is too long")
        return normalized


class PromptTemplateCreate(_FrozenContract):
    scope_kind: PromptTemplateScopeKind
    world_id: uuid.UUID | None = None
    template_key: str = Field(min_length=1, max_length=120)
    version: int = Field(ge=1)
    invocation_kind: InvocationKind
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    input_schema_json: dict[str, Any] | None = None
    output_schema_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None
    status: PromptTemplateStatus = PromptTemplateStatus.DRAFT

    @model_validator(mode="after")
    def validate_scope(self) -> PromptTemplateCreate:
        if self.scope_kind == PromptTemplateScopeKind.GLOBAL and self.world_id is not None:
            raise ValueError("global prompt templates must not include world_id")
        if self.scope_kind == PromptTemplateScopeKind.WORLD and self.world_id is None:
            raise ValueError("world prompt templates require world_id")
        return self


class PromptTemplateUpdate(_FrozenContract):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    input_schema_json: dict[str, Any] | None = None
    output_schema_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None
    status: PromptTemplateStatus | None = None


class AgentRuntimeRunInvocationLinkCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    agent_runtime_run_id: uuid.UUID
    model_invocation_id: uuid.UUID
    invocation_role: InvocationRole = InvocationRole.PRIMARY
    sequence_index: int = Field(default=0, ge=0)


class InvocationTagRecord(InvocationTagFilter):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    invocation_id: uuid.UUID
    created_at: datetime

    @field_validator("created_at", mode="after")
    @classmethod
    def normalize_created(cls, value: datetime) -> datetime:
        return _utc(value)


class PromptSnapshotRecord(_FrozenContract):
    id: uuid.UUID
    invocation_id: uuid.UUID
    template_id: uuid.UUID | None
    template_key: str | None
    template_version: int | None
    raw_prompt_text: str | None
    raw_messages_json: list[dict[str, Any]] | None
    raw_request_json: dict[str, Any] | None
    raw_response_json: dict[str, Any] | None
    raw_output_text: str | None
    normalized_output_json: dict[str, Any] | None
    prompt_context_snapshot_json: dict[str, Any] | None
    tool_definitions_json: dict[str, Any] | None
    context_pack_refs_json: dict[str, Any] | None
    input_asset_refs_json: list[dict[str, Any]] | None
    prompt_checksum_sha256: str
    request_checksum_sha256: str | None
    response_checksum_sha256: str | None
    output_checksum_sha256: str | None
    visibility: InvocationVisibility
    redaction_status: InvocationRedactionStatus
    contains_sensitive_context: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_dt(cls, value: datetime) -> datetime:
        return _utc(value)


class InvocationRecordView(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    trace_id: uuid.UUID
    parent_invocation_id: uuid.UUID | None
    invocation_kind: InvocationKind
    actor_kind: InvocationActorKind
    actor_ref: str | None
    agent_id: uuid.UUID | None
    conversation_id: uuid.UUID | None
    turn_id: uuid.UUID | None
    world_event_id: uuid.UUID | None
    media_job_id: uuid.UUID | None
    media_asset_id: uuid.UUID | None
    memory_write_job_id: uuid.UUID | None
    provider_kind: InvocationProviderKind
    provider_profile_id: uuid.UUID | None
    model_name: str | None
    model_version: str | None
    prompt_template_key: str | None
    prompt_template_version: int | None
    input_text: str | None
    output_text: str | None
    input_json: dict[str, Any] | None
    output_json: dict[str, Any] | None
    request_params_json: dict[str, Any] | None
    response_metadata_json: dict[str, Any] | None
    usage_json: dict[str, Any] | None
    latency_ms: int | None
    estimated_cost: Decimal | None
    status: InvocationStatus
    error_text: str | None
    visibility: InvocationVisibility
    redaction_status: InvocationRedactionStatus
    retention_policy: InvocationRetentionPolicy
    contains_sensitive_context: bool
    purge_after: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", "purge_after", mode="after")
    @classmethod
    def normalize_dt(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)


class InvocationSearchResult(_FrozenContract):
    invocations: list[InvocationRecordView]


class PromptTemplateRecord(_FrozenContract):
    id: uuid.UUID
    scope_kind: PromptTemplateScopeKind
    world_id: uuid.UUID | None
    scope_key: str
    template_key: str
    version: int
    invocation_kind: InvocationKind
    title: str
    content: str
    input_schema_json: dict[str, Any] | None
    output_schema_json: dict[str, Any] | None
    metadata_json: dict[str, Any] | None
    status: PromptTemplateStatus
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_dt(cls, value: datetime) -> datetime:
        return _utc(value)


class AgentRuntimeRunInvocationLinkRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    agent_runtime_run_id: uuid.UUID
    model_invocation_id: uuid.UUID
    invocation_role: InvocationRole
    sequence_index: int
    created_at: datetime

    @field_validator("created_at", mode="after")
    @classmethod
    def normalize_dt(cls, value: datetime) -> datetime:
        return _utc(value)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _assert_json_serializable(value: Any, field_name: str) -> None:
    import json

    try:
        json.dumps(value)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be JSON serializable") from exc
