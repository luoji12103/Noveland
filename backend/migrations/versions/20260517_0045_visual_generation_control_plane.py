"""Add visual generation control plane.

Revision ID: 20260517_0045
Revises: 20260516_0044
Create Date: 2026-05-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260517_0045"
down_revision: str | None = "20260516_0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "visual_workflow_templates",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=True),
        sa.Column("provider_kind", sa.String(length=40), nullable=False),
        sa.Column("adapter_kind", sa.String(length=40), nullable=False),
        sa.Column("workflow_key", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("intent", sa.String(length=40), nullable=False),
        sa.Column(
            "status", sa.String(length=24), server_default=sa.text("'draft'"), nullable=False
        ),
        sa.Column(
            "visibility",
            sa.String(length=32),
            server_default=sa.text("'world_admin'"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "provider_kind IN ("
            "'image_generation', 'image_editing', 'image_analysis', 'image_composition', "
            "'workflow_engine', 'other'"
            ")",
            name=op.f("ck_visual_workflow_templates_provider_kind"),
        ),
        sa.CheckConstraint(
            "adapter_kind IN ("
            "'fake', 'openai', 'openai_compatible', 'comfyui', 'custom_http', "
            "'local_stub', 'other'"
            ")",
            name=op.f("ck_visual_workflow_templates_adapter_kind"),
        ),
        sa.CheckConstraint(
            "intent IN ("
            "'character_sprite', 'expression_variant', 'scene_background', 'event_cg', "
            "'multi_character_cg', 'inpaint', 'pose_variant', 'style_reference', "
            "'image_edit', 'image_composition', 'other'"
            ")",
            name=op.f("ck_visual_workflow_templates_intent"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'disabled', 'deleted')",
            name=op.f("ck_visual_workflow_templates_status"),
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'world_admin', 'world_member', 'developer_only', 'hidden')",
            name=op.f("ck_visual_workflow_templates_visibility"),
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["provider_integrations.id"],
            name=op.f("fk_visual_workflow_templates_provider_id_provider_integrations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_visual_workflow_templates_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_visual_workflow_templates")),
        sa.UniqueConstraint(
            "world_id",
            "workflow_key",
            name="uq_visual_workflow_templates_world_key",
        ),
    )
    op.create_index(
        "ix_visual_workflow_templates_world_status",
        "visual_workflow_templates",
        ["world_id", "status"],
    )
    op.create_index(
        "ix_visual_workflow_templates_provider",
        "visual_workflow_templates",
        ["provider_id"],
    )
    op.create_index(
        "ix_visual_workflow_templates_intent",
        "visual_workflow_templates",
        ["world_id", "intent", "status"],
    )

    op.create_table(
        "visual_workflow_template_versions",
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("parameter_schema", JSONB, nullable=False),
        sa.Column("required_capabilities", JSONB, nullable=False),
        sa.Column("allowed_asset_roles", JSONB, nullable=False),
        sa.Column("safety_constraints", JSONB, nullable=False),
        sa.Column("template_payload", JSONB, nullable=False),
        sa.Column(
            "validation_status",
            sa.String(length=24),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column("validation_error", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "validation_status IN ('draft', 'valid', 'invalid', 'disabled')",
            name=op.f("ck_visual_workflow_template_versions_validation_status"),
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["visual_workflow_templates.id"],
            name=op.f("fk_visual_workflow_template_versions_template_id_visual_workflow_templates"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_visual_workflow_template_versions")),
        sa.UniqueConstraint(
            "template_id",
            "version",
            name="uq_visual_workflow_template_versions_version",
        ),
    )
    op.create_index(
        "ix_visual_workflow_template_versions_template",
        "visual_workflow_template_versions",
        ["template_id"],
    )
    op.create_index(
        "ix_visual_workflow_template_versions_status",
        "visual_workflow_template_versions",
        ["template_id", "validation_status"],
    )

    op.create_table(
        "visual_model_assets",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=True),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_kind", sa.String(length=40), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("provider_model_name", sa.String(length=240), nullable=False),
        sa.Column("file_name", sa.String(length=240), nullable=True),
        sa.Column("trigger_words", JSONB, nullable=False),
        sa.Column("compatible_base_models", JSONB, nullable=False),
        sa.Column("recommended_weight", sa.Float(), nullable=True),
        sa.Column("style_tags", JSONB, nullable=False),
        sa.Column("character_tags", JSONB, nullable=False),
        sa.Column(
            "visibility",
            sa.String(length=32),
            server_default=sa.text("'world_admin'"),
            nullable=False,
        ),
        sa.Column("source_note", sa.String(length=500), nullable=True),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "inventory_kind IN ("
            "'checkpoint', 'lora', 'vae', 'embedding', 'controlnet', 'ip_adapter', "
            "'workflow_template', 'prompt_preset', 'other'"
            ")",
            name=op.f("ck_visual_model_assets_inventory_kind"),
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'world_admin', 'world_member', 'developer_only', 'hidden')",
            name=op.f("ck_visual_model_assets_visibility"),
        ),
        sa.CheckConstraint(
            "recommended_weight IS NULL OR "
            "(recommended_weight >= -10 AND recommended_weight <= 10)",
            name=op.f("ck_visual_model_assets_recommended_weight_range"),
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["provider_integrations.id"],
            name=op.f("fk_visual_model_assets_provider_id_provider_integrations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_visual_model_assets_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_visual_model_assets_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_visual_model_assets")),
    )
    op.create_index(
        "ix_visual_model_assets_world_kind", "visual_model_assets", ["world_id", "inventory_kind"]
    )
    op.create_index(
        "ix_visual_model_assets_worldline_kind",
        "visual_model_assets",
        ["world_id", "worldline_id", "inventory_kind"],
    )
    op.create_index(
        "ix_visual_model_assets_provider_kind",
        "visual_model_assets",
        ["provider_id", "inventory_kind"],
    )
    op.create_index(
        "ix_visual_model_assets_visibility", "visual_model_assets", ["world_id", "visibility"]
    )

    op.create_table(
        "character_visual_generation_profiles",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("preferred_checkpoint_id", sa.Uuid(), nullable=True),
        sa.Column("allowed_lora_ids", JSONB, nullable=False),
        sa.Column("default_lora_ids", JSONB, nullable=False),
        sa.Column("banned_lora_ids", JSONB, nullable=False),
        sa.Column("prompt_fragments", JSONB, nullable=False),
        sa.Column("negative_prompt_fragments", JSONB, nullable=False),
        sa.Column("reference_asset_ids", JSONB, nullable=False),
        sa.Column("default_workflow_template_id", sa.Uuid(), nullable=True),
        sa.Column("expression_workflow_template_id", sa.Uuid(), nullable=True),
        sa.Column("cg_workflow_template_id", sa.Uuid(), nullable=True),
        sa.Column("outfit_policy", JSONB, nullable=False),
        sa.Column("pose_policy", JSONB, nullable=False),
        sa.Column(
            "review_status",
            sa.String(length=32),
            server_default=sa.text("'proposed'"),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            sa.String(length=32),
            server_default=sa.text("'world_admin'"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "review_status IN ("
            "'proposed', 'under_review', 'approved', 'applied', 'rejected', 'disabled', 'deleted'"
            ")",
            name=op.f("ck_character_visual_generation_profiles_review_status"),
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'world_admin', 'world_member', 'developer_only', 'hidden')",
            name=op.f("ck_character_visual_generation_profiles_visibility"),
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name=op.f("fk_character_visual_generation_profiles_agent_id_agents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["cg_workflow_template_id"],
            ["visual_workflow_templates.id"],
            name=op.f(
                "fk_character_visual_generation_profiles_cg_workflow_template_id_visual_workflow_templates"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["default_workflow_template_id"],
            ["visual_workflow_templates.id"],
            name=op.f(
                "fk_character_visual_generation_profiles_default_workflow_template_id_visual_workflow_templates"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["expression_workflow_template_id"],
            ["visual_workflow_templates.id"],
            name=op.f(
                "fk_character_visual_generation_profiles_expression_workflow_template_id_visual_workflow_templates"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["preferred_checkpoint_id"],
            ["visual_model_assets.id"],
            name=op.f(
                "fk_character_visual_generation_profiles_preferred_checkpoint_id_visual_model_assets"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_character_visual_generation_profiles_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_character_visual_generation_profiles_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_character_visual_generation_profiles")),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "agent_id",
            name="uq_character_visual_generation_profiles_agent",
        ),
    )
    op.create_index(
        "ix_character_visual_generation_profiles_worldline_agent",
        "character_visual_generation_profiles",
        ["world_id", "worldline_id", "agent_id"],
    )
    op.create_index(
        "ix_character_visual_generation_profiles_review",
        "character_visual_generation_profiles",
        ["world_id", "worldline_id", "review_status"],
    )

    op.create_table(
        "visual_generation_plans",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("intent", sa.String(length=40), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_template_id", sa.Uuid(), nullable=True),
        sa.Column("workflow_template_version_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status", sa.String(length=32), server_default=sa.text("'draft'"), nullable=False
        ),
        sa.Column("character_ids", JSONB, nullable=False),
        sa.Column("scene_id", sa.Uuid(), nullable=True),
        sa.Column("prompt_plan", JSONB, nullable=False),
        sa.Column("model_plan", JSONB, nullable=False),
        sa.Column("output_plan", JSONB, nullable=False),
        sa.Column("validation_results", JSONB, nullable=False),
        sa.Column("source_context", JSONB, nullable=False),
        sa.Column("model_invocation_id", sa.Uuid(), nullable=True),
        sa.Column("media_job_id", sa.Uuid(), nullable=True),
        sa.Column("output_media_asset_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "intent IN ("
            "'character_sprite', 'expression_variant', 'scene_background', 'event_cg', "
            "'multi_character_cg', 'inpaint', 'pose_variant', 'style_reference', "
            "'image_edit', 'image_composition', 'other'"
            ")",
            name=op.f("ck_visual_generation_plans_intent"),
        ),
        sa.CheckConstraint(
            "status IN ("
            "'draft', 'validated', 'validation_failed', 'dry_run_succeeded', 'dry_run_failed', "
            "'queued', 'executed', 'failed', 'canceled', 'deleted'"
            ")",
            name=op.f("ck_visual_generation_plans_status"),
        ),
        sa.ForeignKeyConstraint(
            ["media_job_id"],
            ["media_jobs.id"],
            name=op.f("fk_visual_generation_plans_media_job_id_media_jobs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["model_invocation_id"],
            ["model_invocations.id"],
            name=op.f("fk_visual_generation_plans_model_invocation_id_model_invocations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["output_media_asset_id"],
            ["media_assets.id"],
            name=op.f("fk_visual_generation_plans_output_media_asset_id_media_assets"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["provider_integrations.id"],
            name=op.f("fk_visual_generation_plans_provider_id_provider_integrations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["scene_id"],
            ["scenes.id"],
            name=op.f("fk_visual_generation_plans_scene_id_scenes"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_template_id"],
            ["visual_workflow_templates.id"],
            name=op.f("fk_visual_generation_plans_workflow_template_id_visual_workflow_templates"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_template_version_id"],
            ["visual_workflow_template_versions.id"],
            name=op.f(
                "fk_visual_generation_plans_workflow_template_version_id_visual_workflow_template_versions"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_visual_generation_plans_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_visual_generation_plans_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_visual_generation_plans")),
    )
    op.create_index(
        "ix_visual_generation_plans_worldline_status",
        "visual_generation_plans",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_visual_generation_plans_provider", "visual_generation_plans", ["provider_id"]
    )
    op.create_index(
        "ix_visual_generation_plans_template",
        "visual_generation_plans",
        ["workflow_template_id"],
    )
    op.create_index(
        "ix_visual_generation_plans_invocation",
        "visual_generation_plans",
        ["model_invocation_id"],
    )
    op.create_index(
        "ix_visual_generation_plans_media_job", "visual_generation_plans", ["media_job_id"]
    )
    op.create_index(
        "ix_visual_generation_plans_output_asset",
        "visual_generation_plans",
        ["output_media_asset_id"],
    )

    op.create_table(
        "visual_generation_plan_references",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("reference_kind", sa.String(length=40), nullable=False),
        sa.Column("reference_id", sa.Uuid(), nullable=False),
        sa.Column("reference_role", sa.String(length=40), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "reference_kind IN ("
            "'media_asset', 'workflow_template', 'model_asset', 'character_profile', "
            "'source_fragment', 'source_asset', 'scene', 'agent', 'other'"
            ")",
            name=op.f("ck_visual_generation_plan_references_reference_kind"),
        ),
        sa.CheckConstraint(
            "reference_role IN ("
            "'character_reference', 'style_reference', 'pose_reference', 'mask', "
            "'control_image', 'input_image', 'source', 'evidence', 'output', 'other'"
            ")",
            name=op.f("ck_visual_generation_plan_references_reference_role"),
        ),
        sa.CheckConstraint(
            "display_order >= 0",
            name=op.f("ck_visual_generation_plan_references_display_order_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["visual_generation_plans.id"],
            name=op.f("fk_visual_generation_plan_references_plan_id_visual_generation_plans"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_visual_generation_plan_references_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_visual_generation_plan_references_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_visual_generation_plan_references")),
    )
    op.create_index(
        "ix_visual_generation_plan_references_plan",
        "visual_generation_plan_references",
        ["plan_id", "display_order"],
    )
    op.create_index(
        "ix_visual_generation_plan_references_worldline",
        "visual_generation_plan_references",
        ["world_id", "worldline_id", "reference_kind"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_visual_generation_plan_references_worldline",
        table_name="visual_generation_plan_references",
    )
    op.drop_index(
        "ix_visual_generation_plan_references_plan",
        table_name="visual_generation_plan_references",
    )
    op.drop_table("visual_generation_plan_references")
    op.drop_index("ix_visual_generation_plans_output_asset", table_name="visual_generation_plans")
    op.drop_index("ix_visual_generation_plans_media_job", table_name="visual_generation_plans")
    op.drop_index("ix_visual_generation_plans_invocation", table_name="visual_generation_plans")
    op.drop_index("ix_visual_generation_plans_template", table_name="visual_generation_plans")
    op.drop_index("ix_visual_generation_plans_provider", table_name="visual_generation_plans")
    op.drop_index(
        "ix_visual_generation_plans_worldline_status", table_name="visual_generation_plans"
    )
    op.drop_table("visual_generation_plans")
    op.drop_index(
        "ix_character_visual_generation_profiles_review",
        table_name="character_visual_generation_profiles",
    )
    op.drop_index(
        "ix_character_visual_generation_profiles_worldline_agent",
        table_name="character_visual_generation_profiles",
    )
    op.drop_table("character_visual_generation_profiles")
    op.drop_index("ix_visual_model_assets_visibility", table_name="visual_model_assets")
    op.drop_index("ix_visual_model_assets_provider_kind", table_name="visual_model_assets")
    op.drop_index("ix_visual_model_assets_worldline_kind", table_name="visual_model_assets")
    op.drop_index("ix_visual_model_assets_world_kind", table_name="visual_model_assets")
    op.drop_table("visual_model_assets")
    op.drop_index(
        "ix_visual_workflow_template_versions_status",
        table_name="visual_workflow_template_versions",
    )
    op.drop_index(
        "ix_visual_workflow_template_versions_template",
        table_name="visual_workflow_template_versions",
    )
    op.drop_table("visual_workflow_template_versions")
    op.drop_index("ix_visual_workflow_templates_intent", table_name="visual_workflow_templates")
    op.drop_index("ix_visual_workflow_templates_provider", table_name="visual_workflow_templates")
    op.drop_index(
        "ix_visual_workflow_templates_world_status", table_name="visual_workflow_templates"
    )
    op.drop_table("visual_workflow_templates")
