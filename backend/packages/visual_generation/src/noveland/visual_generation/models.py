from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


def _json_column() -> JSONB | JSON:
    return JSONB().with_variant(JSON(), "sqlite")


VISUAL_PROVIDER_KIND_CHECK = (
    "'image_generation', 'image_editing', 'image_analysis', 'image_composition', "
    "'workflow_engine', 'other'"
)
VISUAL_ADAPTER_KIND_CHECK = (
    "'fake', 'openai', 'openai_compatible', 'comfyui', 'custom_http', 'local_stub', 'other'"
)
WORKFLOW_INTENT_CHECK = (
    "'character_sprite', 'expression_variant', 'scene_background', 'event_cg', "
    "'multi_character_cg', 'inpaint', 'pose_variant', 'style_reference', "
    "'image_edit', 'image_composition', 'other'"
)
WORKFLOW_TEMPLATE_STATUS_CHECK = "'draft', 'active', 'disabled', 'deleted'"
WORKFLOW_VERSION_STATUS_CHECK = "'draft', 'valid', 'invalid', 'disabled'"
VISUAL_GENERATION_VISIBILITY_CHECK = (
    "'private', 'world_admin', 'world_member', 'developer_only', 'hidden'"
)
MODEL_INVENTORY_KIND_CHECK = (
    "'checkpoint', 'lora', 'vae', 'embedding', 'controlnet', 'ip_adapter', "
    "'workflow_template', 'prompt_preset', 'other'"
)
PROFILE_REVIEW_STATUS_CHECK = (
    "'proposed', 'under_review', 'approved', 'applied', 'rejected', 'disabled', 'deleted'"
)
PLAN_STATUS_CHECK = (
    "'draft', 'validated', 'validation_failed', 'dry_run_succeeded', 'dry_run_failed', "
    "'queued', 'executed', 'failed', 'canceled', 'deleted'"
)
PLAN_REFERENCE_KIND_CHECK = (
    "'media_asset', 'workflow_template', 'model_asset', 'character_profile', "
    "'source_fragment', 'source_asset', 'scene', 'agent', 'other'"
)
PLAN_REFERENCE_ROLE_CHECK = (
    "'character_reference', 'style_reference', 'pose_reference', 'mask', "
    "'control_image', 'input_image', 'source', 'evidence', 'output', 'other'"
)


class VisualWorkflowTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "visual_workflow_templates"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "workflow_key",
            name="uq_visual_workflow_templates_world_key",
        ),
        CheckConstraint(f"provider_kind IN ({VISUAL_PROVIDER_KIND_CHECK})", name="provider_kind"),
        CheckConstraint(f"adapter_kind IN ({VISUAL_ADAPTER_KIND_CHECK})", name="adapter_kind"),
        CheckConstraint(f"intent IN ({WORKFLOW_INTENT_CHECK})", name="intent"),
        CheckConstraint(
            f"status IN ({WORKFLOW_TEMPLATE_STATUS_CHECK})",
            name="status",
        ),
        CheckConstraint(
            f"visibility IN ({VISUAL_GENERATION_VISIBILITY_CHECK})",
            name="visibility",
        ),
        Index("ix_visual_workflow_templates_world_status", "world_id", "status"),
        Index("ix_visual_workflow_templates_provider", "provider_id"),
        Index("ix_visual_workflow_templates_intent", "world_id", "intent", "status"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("provider_integrations.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    adapter_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    workflow_key: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    intent: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text("'draft'"),
        default="draft",
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'world_admin'"),
        default="world_admin",
    )


class VisualWorkflowTemplateVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "visual_workflow_template_versions"
    __table_args__ = (
        UniqueConstraint(
            "template_id",
            "version",
            name="uq_visual_workflow_template_versions_version",
        ),
        CheckConstraint(
            f"validation_status IN ({WORKFLOW_VERSION_STATUS_CHECK})",
            name="validation_status",
        ),
        Index("ix_visual_workflow_template_versions_template", "template_id"),
        Index("ix_visual_workflow_template_versions_status", "template_id", "validation_status"),
    )

    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visual_workflow_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    parameter_schema_json: Mapped[dict[str, Any]] = mapped_column(
        "parameter_schema",
        _json_column(),
        nullable=False,
        default=dict,
    )
    required_capabilities_json: Mapped[dict[str, Any]] = mapped_column(
        "required_capabilities",
        _json_column(),
        nullable=False,
        default=dict,
    )
    allowed_asset_roles_json: Mapped[dict[str, Any]] = mapped_column(
        "allowed_asset_roles",
        _json_column(),
        nullable=False,
        default=dict,
    )
    safety_constraints_json: Mapped[dict[str, Any]] = mapped_column(
        "safety_constraints",
        _json_column(),
        nullable=False,
        default=dict,
    )
    template_payload_json: Mapped[dict[str, Any]] = mapped_column(
        "template_payload",
        _json_column(),
        nullable=False,
        default=dict,
    )
    validation_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text("'draft'"),
        default="draft",
    )
    validation_error_json: Mapped[dict[str, Any]] = mapped_column(
        "validation_error",
        _json_column(),
        nullable=False,
        default=dict,
    )


class VisualModelAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "visual_model_assets"
    __table_args__ = (
        CheckConstraint(
            f"inventory_kind IN ({MODEL_INVENTORY_KIND_CHECK})",
            name="inventory_kind",
        ),
        CheckConstraint(
            f"visibility IN ({VISUAL_GENERATION_VISIBILITY_CHECK})",
            name="visibility",
        ),
        CheckConstraint(
            "recommended_weight IS NULL OR "
            "(recommended_weight >= -10 AND recommended_weight <= 10)",
            name="recommended_weight_range",
        ),
        Index("ix_visual_model_assets_world_kind", "world_id", "inventory_kind"),
        Index(
            "ix_visual_model_assets_worldline_kind",
            "world_id",
            "worldline_id",
            "inventory_kind",
        ),
        Index("ix_visual_model_assets_provider_kind", "provider_id", "inventory_kind"),
        Index("ix_visual_model_assets_visibility", "world_id", "visibility"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=True,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("provider_integrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    inventory_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider_model_name: Mapped[str] = mapped_column(String(240), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    trigger_words_json: Mapped[list[str]] = mapped_column(
        "trigger_words",
        _json_column(),
        nullable=False,
        default=list,
    )
    compatible_base_models_json: Mapped[list[str]] = mapped_column(
        "compatible_base_models",
        _json_column(),
        nullable=False,
        default=list,
    )
    recommended_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    style_tags_json: Mapped[list[str]] = mapped_column(
        "style_tags",
        _json_column(),
        nullable=False,
        default=list,
    )
    character_tags_json: Mapped[list[str]] = mapped_column(
        "character_tags",
        _json_column(),
        nullable=False,
        default=list,
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'world_admin'"),
        default="world_admin",
    )
    source_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        _json_column(),
        nullable=False,
        default=dict,
    )


class CharacterVisualGenerationProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "character_visual_generation_profiles"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "agent_id",
            name="uq_character_visual_generation_profiles_agent",
        ),
        CheckConstraint(
            f"review_status IN ({PROFILE_REVIEW_STATUS_CHECK})",
            name="review_status",
        ),
        CheckConstraint(
            f"visibility IN ({VISUAL_GENERATION_VISIBILITY_CHECK})",
            name="visibility",
        ),
        Index(
            "ix_character_visual_generation_profiles_worldline_agent",
            "world_id",
            "worldline_id",
            "agent_id",
        ),
        Index(
            "ix_character_visual_generation_profiles_review",
            "world_id",
            "worldline_id",
            "review_status",
        ),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    preferred_checkpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visual_model_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    allowed_lora_ids_json: Mapped[list[str]] = mapped_column(
        "allowed_lora_ids",
        _json_column(),
        nullable=False,
        default=list,
    )
    default_lora_ids_json: Mapped[list[str]] = mapped_column(
        "default_lora_ids",
        _json_column(),
        nullable=False,
        default=list,
    )
    banned_lora_ids_json: Mapped[list[str]] = mapped_column(
        "banned_lora_ids",
        _json_column(),
        nullable=False,
        default=list,
    )
    prompt_fragments_json: Mapped[dict[str, Any]] = mapped_column(
        "prompt_fragments",
        _json_column(),
        nullable=False,
        default=dict,
    )
    negative_prompt_fragments_json: Mapped[dict[str, Any]] = mapped_column(
        "negative_prompt_fragments",
        _json_column(),
        nullable=False,
        default=dict,
    )
    reference_asset_ids_json: Mapped[list[str]] = mapped_column(
        "reference_asset_ids",
        _json_column(),
        nullable=False,
        default=list,
    )
    default_workflow_template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visual_workflow_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    expression_workflow_template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visual_workflow_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    cg_workflow_template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visual_workflow_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    outfit_policy_json: Mapped[dict[str, Any]] = mapped_column(
        "outfit_policy",
        _json_column(),
        nullable=False,
        default=dict,
    )
    pose_policy_json: Mapped[dict[str, Any]] = mapped_column(
        "pose_policy",
        _json_column(),
        nullable=False,
        default=dict,
    )
    review_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'proposed'"),
        default="proposed",
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'world_admin'"),
        default="world_admin",
    )


class VisualGenerationPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "visual_generation_plans"
    __table_args__ = (
        CheckConstraint(f"intent IN ({WORKFLOW_INTENT_CHECK})", name="intent"),
        CheckConstraint(f"status IN ({PLAN_STATUS_CHECK})", name="status"),
        Index("ix_visual_generation_plans_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_visual_generation_plans_provider", "provider_id"),
        Index("ix_visual_generation_plans_template", "workflow_template_id"),
        Index("ix_visual_generation_plans_invocation", "model_invocation_id"),
        Index("ix_visual_generation_plans_media_job", "media_job_id"),
        Index("ix_visual_generation_plans_output_asset", "output_media_asset_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    intent: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("provider_integrations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    workflow_template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visual_workflow_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    workflow_template_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visual_workflow_template_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'draft'"),
        default="draft",
    )
    character_ids_json: Mapped[list[str]] = mapped_column(
        "character_ids",
        _json_column(),
        nullable=False,
        default=list,
    )
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
    )
    prompt_plan_json: Mapped[dict[str, Any]] = mapped_column(
        "prompt_plan",
        _json_column(),
        nullable=False,
        default=dict,
    )
    model_plan_json: Mapped[dict[str, Any]] = mapped_column(
        "model_plan",
        _json_column(),
        nullable=False,
        default=dict,
    )
    output_plan_json: Mapped[dict[str, Any]] = mapped_column(
        "output_plan",
        _json_column(),
        nullable=False,
        default=dict,
    )
    validation_results_json: Mapped[dict[str, Any]] = mapped_column(
        "validation_results",
        _json_column(),
        nullable=False,
        default=dict,
    )
    source_context_json: Mapped[dict[str, Any]] = mapped_column(
        "source_context",
        _json_column(),
        nullable=False,
        default=dict,
    )
    model_invocation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("model_invocations.id", ondelete="SET NULL"),
        nullable=True,
    )
    media_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    output_media_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
    )


class VisualGenerationPlanReference(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "visual_generation_plan_references"
    __table_args__ = (
        CheckConstraint(
            f"reference_kind IN ({PLAN_REFERENCE_KIND_CHECK})",
            name="reference_kind",
        ),
        CheckConstraint(
            f"reference_role IN ({PLAN_REFERENCE_ROLE_CHECK})",
            name="reference_role",
        ),
        CheckConstraint("display_order >= 0", name="display_order_nonnegative"),
        Index("ix_visual_generation_plan_references_plan", "plan_id", "display_order"),
        Index(
            "ix_visual_generation_plan_references_worldline",
            "world_id",
            "worldline_id",
            "reference_kind",
        ),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visual_generation_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    reference_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    reference_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    reference_role: Mapped[str] = mapped_column(String(40), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        _json_column(),
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
