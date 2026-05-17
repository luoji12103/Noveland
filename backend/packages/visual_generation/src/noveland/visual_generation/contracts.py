from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from noveland.providers.contracts import ProviderAdapterKind, ProviderKind
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VisualWorkflowIntent(StrEnum):
    CHARACTER_SPRITE = "character_sprite"
    EXPRESSION_VARIANT = "expression_variant"
    SCENE_BACKGROUND = "scene_background"
    EVENT_CG = "event_cg"
    MULTI_CHARACTER_CG = "multi_character_cg"
    INPAINT = "inpaint"
    POSE_VARIANT = "pose_variant"
    STYLE_REFERENCE = "style_reference"
    IMAGE_EDIT = "image_edit"
    IMAGE_COMPOSITION = "image_composition"
    OTHER = "other"


class VisualGenerationVisibility(StrEnum):
    PRIVATE = "private"
    WORLD_ADMIN = "world_admin"
    WORLD_MEMBER = "world_member"
    DEVELOPER_ONLY = "developer_only"
    HIDDEN = "hidden"


class VisualWorkflowTemplateStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


class WorkflowTemplateVersionValidationStatus(StrEnum):
    DRAFT = "draft"
    VALID = "valid"
    INVALID = "invalid"
    DISABLED = "disabled"


class VisualModelInventoryKind(StrEnum):
    CHECKPOINT = "checkpoint"
    LORA = "lora"
    VAE = "vae"
    EMBEDDING = "embedding"
    CONTROLNET = "controlnet"
    IP_ADAPTER = "ip_adapter"
    WORKFLOW_TEMPLATE = "workflow_template"
    PROMPT_PRESET = "prompt_preset"
    OTHER = "other"


class CharacterVisualProfileReviewStatus(StrEnum):
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    DISABLED = "disabled"
    DELETED = "deleted"


class VisualGenerationPlanStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"
    DRY_RUN_SUCCEEDED = "dry_run_succeeded"
    DRY_RUN_FAILED = "dry_run_failed"
    QUEUED = "queued"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELED = "canceled"
    DELETED = "deleted"


class VisualGenerationReferenceKind(StrEnum):
    MEDIA_ASSET = "media_asset"
    WORKFLOW_TEMPLATE = "workflow_template"
    MODEL_ASSET = "model_asset"
    CHARACTER_PROFILE = "character_profile"
    SOURCE_FRAGMENT = "source_fragment"
    SOURCE_ASSET = "source_asset"
    SCENE = "scene"
    AGENT = "agent"
    OTHER = "other"


class VisualGenerationReferenceRole(StrEnum):
    CHARACTER_REFERENCE = "character_reference"
    STYLE_REFERENCE = "style_reference"
    POSE_REFERENCE = "pose_reference"
    MASK = "mask"
    CONTROL_IMAGE = "control_image"
    INPUT_IMAGE = "input_image"
    SOURCE = "source"
    EVIDENCE = "evidence"
    OUTPUT = "output"
    OTHER = "other"


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class ValidationIssue(_FrozenContract):
    code: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=500)
    field: str | None = Field(default=None, min_length=1, max_length=200)
    severity: ValidationSeverity = ValidationSeverity.ERROR
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class VisualGenerationPlanValidationResult(_FrozenContract):
    plan_id: uuid.UUID | None = None
    passed: bool
    issues: tuple[ValidationIssue, ...] = ()
    normalized_slot_values_json: dict[str, Any] = Field(default_factory=dict)
    mapping_kind: str | None = None
    provider_call_made: bool = False


class VisualGenerationDryRunResult(_FrozenContract):
    plan_id: uuid.UUID
    validation: VisualGenerationPlanValidationResult
    dry_run_status: str
    mapping_kind: str | None = None
    mapped_request_json: dict[str, Any] = Field(default_factory=dict)
    provider_call_made: bool = False


class WorkflowTemplateCreate(_FrozenContract):
    world_id: uuid.UUID
    provider_id: uuid.UUID | None = None
    provider_kind: ProviderKind
    adapter_kind: ProviderAdapterKind
    workflow_key: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=200)
    intent: VisualWorkflowIntent = VisualWorkflowIntent.OTHER
    status: VisualWorkflowTemplateStatus = VisualWorkflowTemplateStatus.DRAFT
    visibility: VisualGenerationVisibility = VisualGenerationVisibility.WORLD_ADMIN

    @field_validator("workflow_key", mode="after")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        return _normalize_key(value, field_name="workflow_key")


class WorkflowTemplateUpdate(_FrozenContract):
    provider_id: uuid.UUID | None = None
    provider_kind: ProviderKind | None = None
    adapter_kind: ProviderAdapterKind | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    intent: VisualWorkflowIntent | None = None
    status: VisualWorkflowTemplateStatus | None = None
    visibility: VisualGenerationVisibility | None = None


class WorkflowTemplateRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    provider_id: uuid.UUID | None
    provider_kind: ProviderKind
    adapter_kind: ProviderAdapterKind
    workflow_key: str
    display_name: str
    intent: VisualWorkflowIntent
    status: VisualWorkflowTemplateStatus
    visibility: VisualGenerationVisibility
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class WorkflowTemplateVersionCreate(_FrozenContract):
    template_id: uuid.UUID
    version: str = Field(min_length=1, max_length=40)
    parameter_schema_json: dict[str, Any] = Field(default_factory=dict)
    required_capabilities_json: dict[str, Any] = Field(default_factory=dict)
    allowed_asset_roles_json: dict[str, Any] = Field(default_factory=dict)
    safety_constraints_json: dict[str, Any] = Field(default_factory=dict)
    template_payload_json: dict[str, Any] = Field(default_factory=dict)
    validation_status: WorkflowTemplateVersionValidationStatus = (
        WorkflowTemplateVersionValidationStatus.DRAFT
    )
    validation_error_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "parameter_schema_json",
        "required_capabilities_json",
        "allowed_asset_roles_json",
        "safety_constraints_json",
        "template_payload_json",
        "validation_error_json",
        mode="after",
    )
    @classmethod
    def validate_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "workflow template version JSON")
        return value


class WorkflowTemplateVersionRead(_FrozenContract):
    id: uuid.UUID
    template_id: uuid.UUID
    version: str
    parameter_schema_json: dict[str, Any]
    required_capabilities_json: dict[str, Any]
    allowed_asset_roles_json: dict[str, Any]
    safety_constraints_json: dict[str, Any]
    template_payload_configured: bool
    validation_status: WorkflowTemplateVersionValidationStatus
    validation_error_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class VisualModelAssetCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    provider_id: uuid.UUID
    inventory_kind: VisualModelInventoryKind
    display_name: str = Field(min_length=1, max_length=200)
    provider_model_name: str = Field(min_length=1, max_length=240)
    file_name: str | None = Field(default=None, min_length=1, max_length=240)
    trigger_words: tuple[str, ...] = ()
    compatible_base_models: tuple[str, ...] = ()
    recommended_weight: float | None = Field(default=None, ge=-10.0, le=10.0)
    style_tags: tuple[str, ...] = ()
    character_tags: tuple[str, ...] = ()
    visibility: VisualGenerationVisibility = VisualGenerationVisibility.WORLD_ADMIN
    source_note: str | None = Field(default=None, max_length=500)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "trigger_words",
        "compatible_base_models",
        "style_tags",
        "character_tags",
        mode="after",
    )
    @classmethod
    def normalize_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_string_tuple(value)

    @field_validator("metadata_json", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "model asset metadata_json")
        return value


class VisualModelAssetUpdate(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    provider_id: uuid.UUID | None = None
    inventory_kind: VisualModelInventoryKind | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    provider_model_name: str | None = Field(default=None, min_length=1, max_length=240)
    file_name: str | None = Field(default=None, min_length=1, max_length=240)
    trigger_words: tuple[str, ...] | None = None
    compatible_base_models: tuple[str, ...] | None = None
    recommended_weight: float | None = Field(default=None, ge=-10.0, le=10.0)
    style_tags: tuple[str, ...] | None = None
    character_tags: tuple[str, ...] | None = None
    visibility: VisualGenerationVisibility | None = None
    source_note: str | None = Field(default=None, max_length=500)
    metadata_json: dict[str, Any] | None = None

    @field_validator(
        "trigger_words",
        "compatible_base_models",
        "style_tags",
        "character_tags",
        mode="after",
    )
    @classmethod
    def normalize_tuple(cls, value: tuple[str, ...] | None) -> tuple[str, ...] | None:
        return None if value is None else _normalize_string_tuple(value)

    @field_validator("metadata_json", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            _assert_json_serializable(value, "model asset metadata_json")
        return value


class VisualModelAssetRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None
    provider_id: uuid.UUID
    inventory_kind: VisualModelInventoryKind
    display_name: str
    provider_model_name: str
    file_name: str | None
    trigger_words: tuple[str, ...]
    compatible_base_models: tuple[str, ...]
    recommended_weight: float | None
    style_tags: tuple[str, ...]
    character_tags: tuple[str, ...]
    visibility: VisualGenerationVisibility
    source_note: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class CharacterVisualGenerationProfileCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    agent_id: uuid.UUID
    preferred_checkpoint_id: uuid.UUID | None = None
    allowed_lora_ids: tuple[uuid.UUID, ...] = ()
    default_lora_ids: tuple[uuid.UUID, ...] = ()
    banned_lora_ids: tuple[uuid.UUID, ...] = ()
    prompt_fragments_json: dict[str, Any] = Field(default_factory=dict)
    negative_prompt_fragments_json: dict[str, Any] = Field(default_factory=dict)
    reference_asset_ids: tuple[uuid.UUID, ...] = ()
    default_workflow_template_id: uuid.UUID | None = None
    expression_workflow_template_id: uuid.UUID | None = None
    cg_workflow_template_id: uuid.UUID | None = None
    outfit_policy_json: dict[str, Any] = Field(default_factory=dict)
    pose_policy_json: dict[str, Any] = Field(default_factory=dict)
    review_status: CharacterVisualProfileReviewStatus = CharacterVisualProfileReviewStatus.PROPOSED
    visibility: VisualGenerationVisibility = VisualGenerationVisibility.WORLD_ADMIN

    @field_validator(
        "prompt_fragments_json",
        "negative_prompt_fragments_json",
        "outfit_policy_json",
        "pose_policy_json",
        mode="after",
    )
    @classmethod
    def validate_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "character visual profile JSON")
        return value

    @model_validator(mode="after")
    def validate_lora_sets(self) -> CharacterVisualGenerationProfileCreate:
        _validate_lora_sets(self.allowed_lora_ids, self.default_lora_ids, self.banned_lora_ids)
        return self


class CharacterVisualGenerationProfileUpdate(_FrozenContract):
    preferred_checkpoint_id: uuid.UUID | None = None
    allowed_lora_ids: tuple[uuid.UUID, ...] | None = None
    default_lora_ids: tuple[uuid.UUID, ...] | None = None
    banned_lora_ids: tuple[uuid.UUID, ...] | None = None
    prompt_fragments_json: dict[str, Any] | None = None
    negative_prompt_fragments_json: dict[str, Any] | None = None
    reference_asset_ids: tuple[uuid.UUID, ...] | None = None
    default_workflow_template_id: uuid.UUID | None = None
    expression_workflow_template_id: uuid.UUID | None = None
    cg_workflow_template_id: uuid.UUID | None = None
    outfit_policy_json: dict[str, Any] | None = None
    pose_policy_json: dict[str, Any] | None = None
    review_status: CharacterVisualProfileReviewStatus | None = None
    visibility: VisualGenerationVisibility | None = None

    @field_validator(
        "prompt_fragments_json",
        "negative_prompt_fragments_json",
        "outfit_policy_json",
        "pose_policy_json",
        mode="after",
    )
    @classmethod
    def validate_json(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            _assert_json_serializable(value, "character visual profile JSON")
        return value


class CharacterVisualGenerationProfileRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    agent_id: uuid.UUID
    preferred_checkpoint_id: uuid.UUID | None
    allowed_lora_ids: tuple[uuid.UUID, ...]
    default_lora_ids: tuple[uuid.UUID, ...]
    banned_lora_ids: tuple[uuid.UUID, ...]
    prompt_fragments_json: dict[str, Any]
    negative_prompt_fragments_json: dict[str, Any]
    reference_asset_ids: tuple[uuid.UUID, ...]
    default_workflow_template_id: uuid.UUID | None
    expression_workflow_template_id: uuid.UUID | None
    cg_workflow_template_id: uuid.UUID | None
    outfit_policy_json: dict[str, Any]
    pose_policy_json: dict[str, Any]
    review_status: CharacterVisualProfileReviewStatus
    visibility: VisualGenerationVisibility
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class VisualGenerationPlanReferenceCreate(_FrozenContract):
    reference_kind: VisualGenerationReferenceKind
    reference_id: uuid.UUID
    reference_role: VisualGenerationReferenceRole = VisualGenerationReferenceRole.OTHER
    display_order: int = Field(default=0, ge=0)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata_json", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "plan reference metadata_json")
        return value


class VisualGenerationPlanCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    intent: VisualWorkflowIntent
    provider_id: uuid.UUID
    workflow_template_id: uuid.UUID | None = None
    workflow_template_version_id: uuid.UUID | None = None
    character_ids: tuple[uuid.UUID, ...] = ()
    scene_id: uuid.UUID | None = None
    prompt_plan_json: dict[str, Any] = Field(default_factory=dict)
    model_plan_json: dict[str, Any] = Field(default_factory=dict)
    output_plan_json: dict[str, Any] = Field(default_factory=dict)
    source_context_json: dict[str, Any] = Field(default_factory=dict)
    references: tuple[VisualGenerationPlanReferenceCreate, ...] = ()

    @field_validator(
        "prompt_plan_json",
        "model_plan_json",
        "output_plan_json",
        "source_context_json",
        mode="after",
    )
    @classmethod
    def validate_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "visual generation plan JSON")
        return value


class VisualGenerationPlanReferenceRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    plan_id: uuid.UUID
    reference_kind: VisualGenerationReferenceKind
    reference_id: uuid.UUID
    reference_role: VisualGenerationReferenceRole
    display_order: int
    metadata_json: dict[str, Any]
    created_at: datetime

    @field_validator("created_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class VisualGenerationPlanRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    intent: VisualWorkflowIntent
    provider_id: uuid.UUID
    workflow_template_id: uuid.UUID | None
    workflow_template_version_id: uuid.UUID | None
    status: VisualGenerationPlanStatus
    character_ids: tuple[uuid.UUID, ...]
    scene_id: uuid.UUID | None
    prompt_plan_json: dict[str, Any]
    model_plan_json: dict[str, Any]
    output_plan_json: dict[str, Any]
    validation_results_json: dict[str, Any]
    source_context_json: dict[str, Any]
    model_invocation_id: uuid.UUID | None
    media_job_id: uuid.UUID | None
    output_media_asset_id: uuid.UUID | None
    references: tuple[VisualGenerationPlanReferenceRead, ...] = ()
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


def _assert_json_serializable(value: dict[str, Any], field_name: str) -> None:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be JSON serializable") from exc


def _normalize_key(value: str, *, field_name: str) -> str:
    normalized = value.strip().lower().replace(" ", "-")
    if normalized == "":
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _normalize_string_tuple(value: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({item.strip() for item in value if item.strip()}))


def _validate_lora_sets(
    allowed_lora_ids: tuple[uuid.UUID, ...],
    default_lora_ids: tuple[uuid.UUID, ...],
    banned_lora_ids: tuple[uuid.UUID, ...],
) -> None:
    allowed = set(allowed_lora_ids)
    defaults = set(default_lora_ids)
    banned = set(banned_lora_ids)
    if defaults and not defaults.issubset(allowed):
        raise ValueError("default LoRAs must be included in allowed LoRAs")
    if allowed.intersection(banned):
        raise ValueError("allowed LoRAs and banned LoRAs must not overlap")
    if defaults.intersection(banned):
        raise ValueError("default LoRAs and banned LoRAs must not overlap")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
