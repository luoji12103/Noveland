"""Add media kernel foundation.

Revision ID: 20260510_0030
Revises: 20260507_0029
Create Date: 2026-05-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260510_0030"
down_revision: str | None = "20260507_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "media_jobs",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("turn_id", sa.Uuid(), nullable=True),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("job_kind", sa.String(length=40), nullable=False),
        sa.Column("provider_kind", sa.String(length=64), nullable=True),
        sa.Column(
            "status", sa.String(length=16), server_default=sa.text("'queued'"), nullable=False
        ),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("cancel_policy", sa.String(length=40), nullable=True),
        sa.Column("deadline_hint", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.String(length=160), nullable=True),
        sa.Column("invalidation_key", sa.String(length=160), nullable=True),
        sa.Column("request_json", JSONB, nullable=False),
        sa.Column("result_json", JSONB, nullable=False),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("created_by_actor_ref", sa.String(length=120), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "job_kind IN ("
            "'image_generation', 'image_edit', 'speech_generation', "
            "'speech_transcription', 'background_removal', 'composition', "
            "'upload_import', 'vision_analysis'"
            ")",
            name=op.f("ck_media_jobs_job_kind"),
        ),
        sa.CheckConstraint("priority >= 0", name=op.f("ck_media_jobs_priority_nonnegative")),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name=op.f("ck_media_jobs_status"),
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name=op.f("fk_media_jobs_agent_id_agents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversation_sessions.id"],
            name=op.f("fk_media_jobs_conversation_id_conversation_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["turn_id"],
            ["conversation_turns.id"],
            name=op.f("fk_media_jobs_turn_id_conversation_turns"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_media_jobs_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_media_jobs_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_jobs")),
    )
    op.create_index("ix_media_jobs_agent_id", "media_jobs", ["agent_id"])
    op.create_index(
        "ix_media_jobs_context",
        "media_jobs",
        ["world_id", "worldline_id", "conversation_id", "turn_id"],
    )
    op.create_index(
        "ix_media_jobs_worldline_created",
        "media_jobs",
        ["world_id", "worldline_id", "created_at"],
    )
    op.create_index(
        "ix_media_jobs_worldline_status",
        "media_jobs",
        ["world_id", "worldline_id", "status"],
    )

    op.create_table(
        "media_assets",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("asset_kind", sa.String(length=16), nullable=False),
        sa.Column("asset_role", sa.String(length=40), nullable=False),
        sa.Column("source_kind", sa.String(length=40), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'registered'"),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            sa.String(length=32),
            server_default=sa.text("'private'"),
            nullable=False,
        ),
        sa.Column("storage_uri", sa.String(length=500), nullable=True),
        sa.Column("preview_uri", sa.String(length=500), nullable=True),
        sa.Column("thumbnail_uri", sa.String(length=500), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("file_ext", sa.String(length=20), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("sample_rate_hz", sa.Integer(), nullable=True),
        sa.Column("audio_channels", sa.Integer(), nullable=True),
        sa.Column("has_alpha", sa.Boolean(), nullable=True),
        sa.Column("color_mode", sa.String(length=40), nullable=True),
        sa.Column("provider_kind", sa.String(length=64), nullable=True),
        sa.Column("source_job_id", sa.Uuid(), nullable=True),
        sa.Column("source_event_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by_actor_ref", sa.String(length=120), nullable=False),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "asset_kind IN ('image', 'audio')", name=op.f("ck_media_assets_asset_kind")
        ),
        sa.CheckConstraint(
            "asset_role IN ("
            "'original_image', 'reference_image', 'mask_image', 'transparent_png', "
            "'composite_image', 'scene_background', 'character_sprite', "
            "'character_expression', 'character_pose', 'event_cg', 'speech_audio', "
            "'voice_file', 'voice_sample', 'transcript_audio'"
            ")",
            name=op.f("ck_media_assets_asset_role"),
        ),
        sa.CheckConstraint(
            "source_kind IN ("
            "'provider_generated', 'manual_upload', 'imported_original', "
            "'composed', 'background_removed'"
            ")",
            name=op.f("ck_media_assets_source_kind"),
        ),
        sa.CheckConstraint(
            "status IN ('registered', 'available', 'failed', 'deleted')",
            name=op.f("ck_media_assets_status"),
        ),
        sa.CheckConstraint(
            "visibility IN ("
            "'private', 'world_admin', 'world_member', 'player_visible', "
            "'reader_visible', 'developer_only', 'hidden'"
            ")",
            name=op.f("ck_media_assets_visibility"),
        ),
        sa.CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0",
            name=op.f("ck_media_assets_size_bytes_nonnegative"),
        ),
        sa.CheckConstraint(
            "width IS NULL OR width >= 0",
            name=op.f("ck_media_assets_width_nonnegative"),
        ),
        sa.CheckConstraint(
            "height IS NULL OR height >= 0",
            name=op.f("ck_media_assets_height_nonnegative"),
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name=op.f("ck_media_assets_duration_ms_nonnegative"),
        ),
        sa.CheckConstraint(
            "sample_rate_hz IS NULL OR sample_rate_hz >= 0",
            name=op.f("ck_media_assets_sample_rate_hz_nonnegative"),
        ),
        sa.CheckConstraint(
            "audio_channels IS NULL OR audio_channels >= 0",
            name=op.f("ck_media_assets_audio_channels_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["source_event_id"],
            ["world_events.id"],
            name=op.f("fk_media_assets_source_event_id_world_events"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_job_id"],
            ["media_jobs.id"],
            name=op.f("fk_media_assets_source_job_id_media_jobs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_media_assets_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_media_assets_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_assets")),
    )
    op.create_index("ix_media_assets_source_event_id", "media_assets", ["source_event_id"])
    op.create_index("ix_media_assets_source_job_id", "media_assets", ["source_job_id"])
    op.create_index(
        "ix_media_assets_worldline_created",
        "media_assets",
        ["world_id", "worldline_id", "created_at"],
    )
    op.create_index(
        "ix_media_assets_worldline_kind_role",
        "media_assets",
        ["world_id", "worldline_id", "asset_kind", "asset_role"],
    )
    op.create_index(
        "ix_media_assets_worldline_status",
        "media_assets",
        ["world_id", "worldline_id", "status"],
    )

    op.create_table(
        "media_asset_contexts",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("turn_id", sa.Uuid(), nullable=True),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("world_event_id", sa.Uuid(), nullable=True),
        sa.Column("narrative_artifact_id", sa.Uuid(), nullable=True),
        sa.Column("context_role", sa.String(length=32), nullable=False),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "context_role IN ('source', 'attachment', 'preview', 'output', "
            "'evidence', 'reference')",
            name=op.f("ck_media_asset_contexts_context_role"),
        ),
        sa.CheckConstraint(
            "conversation_id IS NOT NULL OR turn_id IS NOT NULL OR agent_id IS NOT NULL OR "
            "world_event_id IS NOT NULL OR narrative_artifact_id IS NOT NULL",
            name=op.f("ck_media_asset_contexts_context_ref_present"),
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name=op.f("fk_media_asset_contexts_agent_id_agents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["media_assets.id"],
            name=op.f("fk_media_asset_contexts_asset_id_media_assets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversation_sessions.id"],
            name=op.f("fk_media_asset_contexts_conversation_id_conversation_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["narrative_artifact_id"],
            ["narrative_artifacts.id"],
            name=op.f("fk_media_asset_contexts_narrative_artifact_id_narrative_artifacts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["turn_id"],
            ["conversation_turns.id"],
            name=op.f("fk_media_asset_contexts_turn_id_conversation_turns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["world_event_id"],
            ["world_events.id"],
            name=op.f("fk_media_asset_contexts_world_event_id_world_events"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_media_asset_contexts_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_media_asset_contexts_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_asset_contexts")),
    )
    op.create_index("ix_media_asset_contexts_agent_id", "media_asset_contexts", ["agent_id"])
    op.create_index("ix_media_asset_contexts_asset_id", "media_asset_contexts", ["asset_id"])
    op.create_index(
        "ix_media_asset_contexts_conversation_id",
        "media_asset_contexts",
        ["conversation_id"],
    )
    op.create_index(
        "ix_media_asset_contexts_narrative_artifact_id",
        "media_asset_contexts",
        ["narrative_artifact_id"],
    )
    op.create_index("ix_media_asset_contexts_turn_id", "media_asset_contexts", ["turn_id"])
    op.create_index(
        "ix_media_asset_contexts_world_event_id",
        "media_asset_contexts",
        ["world_event_id"],
    )
    op.create_index(
        "ix_media_asset_contexts_worldline_created",
        "media_asset_contexts",
        ["world_id", "worldline_id", "created_at"],
    )

    op.create_table(
        "media_asset_inputs",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("output_asset_id", sa.Uuid(), nullable=False),
        sa.Column("input_asset_id", sa.Uuid(), nullable=False),
        sa.Column("source_job_id", sa.Uuid(), nullable=True),
        sa.Column("input_role", sa.String(length=32), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "input_role IN ('source', 'reference', 'mask', 'background', 'layer', 'audio_source')",
            name=op.f("ck_media_asset_inputs_input_role"),
        ),
        sa.CheckConstraint(
            "display_order >= 0",
            name=op.f("ck_media_asset_inputs_display_order_nonnegative"),
        ),
        sa.CheckConstraint(
            "output_asset_id <> input_asset_id",
            name=op.f("ck_media_asset_inputs_distinct_assets"),
        ),
        sa.ForeignKeyConstraint(
            ["input_asset_id"],
            ["media_assets.id"],
            name=op.f("fk_media_asset_inputs_input_asset_id_media_assets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["output_asset_id"],
            ["media_assets.id"],
            name=op.f("fk_media_asset_inputs_output_asset_id_media_assets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_job_id"],
            ["media_jobs.id"],
            name=op.f("fk_media_asset_inputs_source_job_id_media_jobs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_media_asset_inputs_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_media_asset_inputs_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_asset_inputs")),
        sa.UniqueConstraint(
            "output_asset_id",
            "input_asset_id",
            "input_role",
            "display_order",
            name=op.f("uq_media_asset_inputs_output_input_role_order"),
        ),
    )
    op.create_index(
        "ix_media_asset_inputs_input_asset_id", "media_asset_inputs", ["input_asset_id"]
    )
    op.create_index(
        "ix_media_asset_inputs_output_asset_id",
        "media_asset_inputs",
        ["output_asset_id"],
    )
    op.create_index("ix_media_asset_inputs_source_job_id", "media_asset_inputs", ["source_job_id"])
    op.create_index(
        "ix_media_asset_inputs_worldline_created",
        "media_asset_inputs",
        ["world_id", "worldline_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_media_asset_inputs_worldline_created", table_name="media_asset_inputs")
    op.drop_index("ix_media_asset_inputs_source_job_id", table_name="media_asset_inputs")
    op.drop_index("ix_media_asset_inputs_output_asset_id", table_name="media_asset_inputs")
    op.drop_index("ix_media_asset_inputs_input_asset_id", table_name="media_asset_inputs")
    op.drop_table("media_asset_inputs")

    op.drop_index("ix_media_asset_contexts_worldline_created", table_name="media_asset_contexts")
    op.drop_index("ix_media_asset_contexts_world_event_id", table_name="media_asset_contexts")
    op.drop_index("ix_media_asset_contexts_turn_id", table_name="media_asset_contexts")
    op.drop_index(
        "ix_media_asset_contexts_narrative_artifact_id",
        table_name="media_asset_contexts",
    )
    op.drop_index("ix_media_asset_contexts_conversation_id", table_name="media_asset_contexts")
    op.drop_index("ix_media_asset_contexts_asset_id", table_name="media_asset_contexts")
    op.drop_index("ix_media_asset_contexts_agent_id", table_name="media_asset_contexts")
    op.drop_table("media_asset_contexts")

    op.drop_index("ix_media_assets_worldline_status", table_name="media_assets")
    op.drop_index("ix_media_assets_worldline_kind_role", table_name="media_assets")
    op.drop_index("ix_media_assets_worldline_created", table_name="media_assets")
    op.drop_index("ix_media_assets_source_job_id", table_name="media_assets")
    op.drop_index("ix_media_assets_source_event_id", table_name="media_assets")
    op.drop_table("media_assets")

    op.drop_index("ix_media_jobs_worldline_status", table_name="media_jobs")
    op.drop_index("ix_media_jobs_worldline_created", table_name="media_jobs")
    op.drop_index("ix_media_jobs_context", table_name="media_jobs")
    op.drop_index("ix_media_jobs_agent_id", table_name="media_jobs")
    op.drop_table("media_jobs")
