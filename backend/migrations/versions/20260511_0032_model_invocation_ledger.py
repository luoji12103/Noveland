"""Add model invocation ledger.

Revision ID: 20260511_0032
Revises: 20260510_0031
Create Date: 2026-05-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260511_0032"
down_revision: str | None = "20260510_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JSONB = postgresql.JSONB(astext_type=sa.Text())

INVOCATION_KIND = (
    "'agent_runtime', 'conversation_turn', 'narrative_generation', 'gm_generation', "
    "'eval', 'image_generation', 'image_edit', 'image_analysis', 'speech_to_text', "
    "'text_to_speech', 'voice_clone', 'tool_planning', 'repair', 'critique', 'other'"
)
ACTOR_KIND = "'system', 'platform_admin', 'world_admin', 'agent', 'player', 'runtime', 'service'"
PROVIDER_KIND = (
    "'openai_compatible', 'anthropic_compatible', 'openai_image', 'openai_audio', "
    "'custom_http', 'comfyui', 'mimo_tts', 'mimo_asr', 'omnivoice', 'gpt_sovits', "
    "'local_stub', 'other'"
)
INVOCATION_STATUS = "'pending', 'running', 'succeeded', 'failed', 'cancelled', 'redacted'"
VISIBILITY = "'private', 'world_admin', 'developer_only', 'hidden'"
REDACTION_STATUS = "'raw', 'redacted', 'hidden', 'checksum_only'"
RETENTION_POLICY = "'local_debug', 'short_term', 'long_term', 'eval_only', 'purge_after_days'"
TEMPLATE_SCOPE = "'global', 'world'"
TEMPLATE_STATUS = "'draft', 'active', 'deprecated', 'archived'"
INVOCATION_ROLE = (
    "'primary', 'retry', 'fallback', 'repair', 'critique', 'tool_planning', "
    "'vision_analysis', 'image_generation', 'speech_generation', 'other'"
)


def upgrade() -> None:
    op.create_table(
        "model_invocations",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("trace_id", sa.Uuid(), nullable=False),
        sa.Column("parent_invocation_id", sa.Uuid(), nullable=True),
        sa.Column("invocation_kind", sa.String(length=40), nullable=False),
        sa.Column("actor_kind", sa.String(length=32), nullable=False),
        sa.Column("actor_ref", sa.String(length=160), nullable=True),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("turn_id", sa.Uuid(), nullable=True),
        sa.Column("world_event_id", sa.Uuid(), nullable=True),
        sa.Column("media_job_id", sa.Uuid(), nullable=True),
        sa.Column("media_asset_id", sa.Uuid(), nullable=True),
        sa.Column("memory_write_job_id", sa.Uuid(), nullable=True),
        sa.Column("provider_kind", sa.String(length=40), nullable=False),
        sa.Column("provider_profile_id", sa.Uuid(), nullable=True),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("model_version", sa.String(length=80), nullable=True),
        sa.Column("prompt_template_key", sa.String(length=120), nullable=True),
        sa.Column("prompt_template_version", sa.Integer(), nullable=True),
        sa.Column("input_text", sa.Text(), nullable=True),
        sa.Column("output_text", sa.Text(), nullable=True),
        sa.Column("input_json", JSONB, nullable=True),
        sa.Column("output_json", JSONB, nullable=True),
        sa.Column("request_params_json", JSONB, nullable=True),
        sa.Column("response_metadata_json", JSONB, nullable=True),
        sa.Column("usage_json", JSONB, nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(18, 8), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("redaction_status", sa.String(length=24), nullable=False),
        sa.Column("retention_policy", sa.String(length=32), nullable=False),
        sa.Column(
            "contains_sensitive_context",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            f"invocation_kind IN ({INVOCATION_KIND})",
            name=op.f("ck_model_invocations_invocation_kind"),
        ),
        sa.CheckConstraint(
            f"actor_kind IN ({ACTOR_KIND})",
            name=op.f("ck_model_invocations_actor_kind"),
        ),
        sa.CheckConstraint(
            f"provider_kind IN ({PROVIDER_KIND})",
            name=op.f("ck_model_invocations_provider_kind"),
        ),
        sa.CheckConstraint(
            f"status IN ({INVOCATION_STATUS})",
            name=op.f("ck_model_invocations_status"),
        ),
        sa.CheckConstraint(
            f"visibility IN ({VISIBILITY})",
            name=op.f("ck_model_invocations_visibility"),
        ),
        sa.CheckConstraint(
            f"redaction_status IN ({REDACTION_STATUS})",
            name=op.f("ck_model_invocations_redaction_status"),
        ),
        sa.CheckConstraint(
            f"retention_policy IN ({RETENTION_POLICY})",
            name=op.f("ck_model_invocations_retention_policy"),
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name=op.f("ck_model_invocations_latency_nonnegative"),
        ),
        sa.CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name=op.f("ck_model_invocations_estimated_cost_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name=op.f("fk_model_invocations_agent_id_agents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversation_sessions.id"],
            name=op.f("fk_model_invocations_conversation_id_conversation_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["media_asset_id"],
            ["media_assets.id"],
            name=op.f("fk_model_invocations_media_asset_id_media_assets"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["media_job_id"],
            ["media_jobs.id"],
            name=op.f("fk_model_invocations_media_job_id_media_jobs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["memory_write_job_id"],
            ["memory_write_jobs.id"],
            name=op.f("fk_model_invocations_memory_write_job_id_memory_write_jobs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["parent_invocation_id"],
            ["model_invocations.id"],
            name=op.f("fk_model_invocations_parent_invocation_id_model_invocations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["provider_profile_id"],
            ["provider_profiles.id"],
            name=op.f("fk_model_invocations_provider_profile_id_provider_profiles"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["turn_id"],
            ["conversation_turns.id"],
            name=op.f("fk_model_invocations_turn_id_conversation_turns"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["world_event_id"],
            ["world_events.id"],
            name=op.f("fk_model_invocations_world_event_id_world_events"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_model_invocations_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_model_invocations_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_invocations")),
    )
    op.create_index(
        "ix_model_invocations_agent",
        "model_invocations",
        ["world_id", "worldline_id", "agent_id"],
    )
    op.create_index(
        "ix_model_invocations_conversation_turn",
        "model_invocations",
        ["world_id", "worldline_id", "conversation_id", "turn_id"],
    )
    op.create_index(
        "ix_model_invocations_media",
        "model_invocations",
        ["world_id", "worldline_id", "media_job_id", "media_asset_id"],
    )
    op.create_index(
        "ix_model_invocations_memory_job",
        "model_invocations",
        ["world_id", "worldline_id", "memory_write_job_id"],
    )
    op.create_index("ix_model_invocations_parent", "model_invocations", ["parent_invocation_id"])
    op.create_index(
        "ix_model_invocations_provider_model",
        "model_invocations",
        ["world_id", "worldline_id", "provider_kind", "model_name"],
    )
    op.create_index("ix_model_invocations_trace", "model_invocations", ["trace_id"])
    op.create_index(
        "ix_model_invocations_worldline_created",
        "model_invocations",
        ["world_id", "worldline_id", "created_at"],
    )
    op.create_index(
        "ix_model_invocations_worldline_kind",
        "model_invocations",
        ["world_id", "worldline_id", "invocation_kind"],
    )
    op.create_index(
        "ix_model_invocations_worldline_status",
        "model_invocations",
        ["world_id", "worldline_id", "status"],
    )

    op.create_table(
        "prompt_templates",
        sa.Column("scope_kind", sa.String(length=16), nullable=False),
        sa.Column("world_id", sa.Uuid(), nullable=True),
        sa.Column("scope_key", sa.String(length=120), nullable=False),
        sa.Column("template_key", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("invocation_kind", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("input_schema_json", JSONB, nullable=True),
        sa.Column("output_schema_json", JSONB, nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            f"scope_kind IN ({TEMPLATE_SCOPE})",
            name=op.f("ck_prompt_templates_scope_kind"),
        ),
        sa.CheckConstraint(
            f"invocation_kind IN ({INVOCATION_KIND})",
            name=op.f("ck_prompt_templates_invocation_kind"),
        ),
        sa.CheckConstraint(
            f"status IN ({TEMPLATE_STATUS})",
            name=op.f("ck_prompt_templates_status"),
        ),
        sa.CheckConstraint("version > 0", name=op.f("ck_prompt_templates_version_positive")),
        sa.CheckConstraint(
            "(scope_kind = 'global' AND world_id IS NULL AND scope_key = 'global') OR "
            "(scope_kind = 'world' AND world_id IS NOT NULL)",
            name=op.f("ck_prompt_templates_scope_consistency"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_prompt_templates_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_templates")),
        sa.UniqueConstraint(
            "scope_key",
            "template_key",
            "version",
            name=op.f("uq_prompt_templates_key"),
        ),
    )
    op.create_index(
        "ix_prompt_templates_key_status",
        "prompt_templates",
        ["template_key", "invocation_kind", "status"],
    )
    op.create_index(
        "ix_prompt_templates_scope_status",
        "prompt_templates",
        ["scope_kind", "world_id", "status"],
    )

    op.create_table(
        "prompt_snapshots",
        sa.Column("invocation_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("template_key", sa.String(length=120), nullable=True),
        sa.Column("template_version", sa.Integer(), nullable=True),
        sa.Column("raw_prompt_text", sa.Text(), nullable=True),
        sa.Column("raw_messages_json", JSONB, nullable=True),
        sa.Column("raw_request_json", JSONB, nullable=True),
        sa.Column("raw_response_json", JSONB, nullable=True),
        sa.Column("raw_output_text", sa.Text(), nullable=True),
        sa.Column("normalized_output_json", JSONB, nullable=True),
        sa.Column("prompt_context_snapshot_json", JSONB, nullable=True),
        sa.Column("tool_definitions_json", JSONB, nullable=True),
        sa.Column("context_pack_refs_json", JSONB, nullable=True),
        sa.Column("input_asset_refs_json", JSONB, nullable=True),
        sa.Column("prompt_checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("request_checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("response_checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("output_checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("redaction_status", sa.String(length=24), nullable=False),
        sa.Column(
            "contains_sensitive_context",
            sa.Boolean(),
            server_default=sa.text("false"),
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
            f"visibility IN ({VISIBILITY})",
            name=op.f("ck_prompt_snapshots_visibility"),
        ),
        sa.CheckConstraint(
            f"redaction_status IN ({REDACTION_STATUS})",
            name=op.f("ck_prompt_snapshots_redaction_status"),
        ),
        sa.ForeignKeyConstraint(
            ["invocation_id"],
            ["model_invocations.id"],
            name=op.f("fk_prompt_snapshots_invocation_id_model_invocations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["prompt_templates.id"],
            name=op.f("fk_prompt_snapshots_template_id_prompt_templates"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_snapshots")),
        sa.UniqueConstraint("invocation_id", name=op.f("uq_prompt_snapshots_invocation_id")),
    )
    op.create_index("ix_prompt_snapshots_template_id", "prompt_snapshots", ["template_id"])

    op.create_table(
        "agent_runtime_run_model_invocations",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("agent_runtime_run_id", sa.Uuid(), nullable=False),
        sa.Column("model_invocation_id", sa.Uuid(), nullable=False),
        sa.Column("invocation_role", sa.String(length=32), nullable=False),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            f"invocation_role IN ({INVOCATION_ROLE})",
            name=op.f("ck_agent_runtime_run_model_invocations_invocation_role"),
        ),
        sa.CheckConstraint(
            "sequence_index >= 0",
            name=op.f("ck_agent_runtime_run_model_invocations_sequence_index_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["agent_runtime_run_id"],
            ["agent_runtime_runs.id"],
            name=op.f(
                "fk_agent_runtime_run_model_invocations_agent_runtime_run_id_agent_runtime_runs"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["model_invocation_id"],
            ["model_invocations.id"],
            name=op.f("fk_agent_runtime_run_model_invocations_model_invocation_id_model_invocations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_agent_runtime_run_model_invocations_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_agent_runtime_run_model_invocations_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_runtime_run_model_invocations")),
        sa.UniqueConstraint(
            "agent_runtime_run_id",
            "model_invocation_id",
            name=op.f("uq_agent_run_invocations_run_invocation"),
        ),
        sa.UniqueConstraint(
            "agent_runtime_run_id",
            "sequence_index",
            name=op.f("uq_agent_run_invocations_run_sequence"),
        ),
    )
    op.create_index(
        "ix_agent_run_invocations_invocation",
        "agent_runtime_run_model_invocations",
        ["model_invocation_id"],
    )
    op.create_index(
        "ix_agent_run_invocations_run",
        "agent_runtime_run_model_invocations",
        ["agent_runtime_run_id", "sequence_index"],
    )
    op.create_index(
        "ix_agent_run_invocations_worldline",
        "agent_runtime_run_model_invocations",
        ["world_id", "worldline_id"],
    )

    op.create_table(
        "model_invocation_tags",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("invocation_id", sa.Uuid(), nullable=False),
        sa.Column("tag_type", sa.String(length=40), nullable=False),
        sa.Column("tag_key", sa.String(length=80), nullable=False),
        sa.Column("tag_value", sa.String(length=220), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["invocation_id"],
            ["model_invocations.id"],
            name=op.f("fk_model_invocation_tags_invocation_id_model_invocations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_model_invocation_tags_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_model_invocation_tags_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_invocation_tags")),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "invocation_id",
            "tag_type",
            "tag_key",
            "tag_value",
            name=op.f("uq_model_invocation_tags_identity"),
        ),
    )
    op.create_index(
        "ix_model_invocation_tags_invocation",
        "model_invocation_tags",
        ["invocation_id"],
    )
    op.create_index(
        "ix_model_invocation_tags_lookup",
        "model_invocation_tags",
        ["world_id", "worldline_id", "tag_type", "tag_key", "tag_value"],
    )


def downgrade() -> None:
    op.drop_index("ix_model_invocation_tags_lookup", table_name="model_invocation_tags")
    op.drop_index("ix_model_invocation_tags_invocation", table_name="model_invocation_tags")
    op.drop_table("model_invocation_tags")

    op.drop_index(
        "ix_agent_run_invocations_worldline",
        table_name="agent_runtime_run_model_invocations",
    )
    op.drop_index(
        "ix_agent_run_invocations_run",
        table_name="agent_runtime_run_model_invocations",
    )
    op.drop_index(
        "ix_agent_run_invocations_invocation",
        table_name="agent_runtime_run_model_invocations",
    )
    op.drop_table("agent_runtime_run_model_invocations")

    op.drop_index("ix_prompt_snapshots_template_id", table_name="prompt_snapshots")
    op.drop_table("prompt_snapshots")

    op.drop_index("ix_prompt_templates_scope_status", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_key_status", table_name="prompt_templates")
    op.drop_table("prompt_templates")

    op.drop_index("ix_model_invocations_worldline_status", table_name="model_invocations")
    op.drop_index("ix_model_invocations_worldline_kind", table_name="model_invocations")
    op.drop_index("ix_model_invocations_worldline_created", table_name="model_invocations")
    op.drop_index("ix_model_invocations_trace", table_name="model_invocations")
    op.drop_index("ix_model_invocations_provider_model", table_name="model_invocations")
    op.drop_index("ix_model_invocations_parent", table_name="model_invocations")
    op.drop_index("ix_model_invocations_memory_job", table_name="model_invocations")
    op.drop_index("ix_model_invocations_media", table_name="model_invocations")
    op.drop_index("ix_model_invocations_conversation_turn", table_name="model_invocations")
    op.drop_index("ix_model_invocations_agent", table_name="model_invocations")
    op.drop_table("model_invocations")
