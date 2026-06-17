"""Extend media kernel with objects and generic references.

Revision ID: 20260512_0033
Revises: 20260511_0032
Create Date: 2026-05-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260512_0033"
down_revision: str | None = "20260511_0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JSONB = postgresql.JSONB(astext_type=sa.Text())

ASSET_KIND = "'image', 'audio', 'video', 'document', 'other'"
ASSET_ROLE = (
    "'original_image', 'reference_image', 'mask_image', 'transparent_png', "
    "'composite_image', 'scene_background', 'character_sprite', "
    "'character_expression', 'character_pose', 'event_cg', 'speech_audio', "
    "'voice_file', 'voice_sample', 'transcript_audio', 'video_clip', "
    "'document', 'thumbnail', 'other'"
)
SOURCE_KIND = (
    "'provider_generated', 'manual_upload', 'imported_original', 'composed', "
    "'background_removed', 'cropped', 'converted', 'system_generated', "
    "'test_fixture', 'other'"
)
JOB_KIND = (
    "'image_generation', 'image_edit', 'speech_generation', "
    "'speech_transcription', 'background_removal', 'composition', "
    "'upload_import', 'vision_analysis', 'transcode', 'thumbnail', 'import', 'other'"
)
OBJECT_ROLE = (
    "'original', 'primary', 'thumbnail', 'preview', 'mask', 'alpha', "
    "'transparent', 'composed', 'waveform', 'transcript_source', 'derived', 'other'"
)
REF_KIND = (
    "'conversation_turn', 'conversation_session', 'world_event', 'narrative_artifact', "
    "'agent', 'scene', 'world', 'model_invocation', 'media_job', 'memory_write_job', 'other'"
)
REF_ROLE = (
    "'attachment', 'input', 'output', 'evidence', 'preview', 'thumbnail', "
    "'background', 'foreground', 'character_sprite', 'voice_reference', "
    "'source', 'derived_from', 'other'"
)


def upgrade() -> None:
    _replace_check("media_assets", "ck_media_assets_asset_kind", f"asset_kind IN ({ASSET_KIND})")
    _replace_check("media_assets", "ck_media_assets_asset_role", f"asset_role IN ({ASSET_ROLE})")
    _replace_check("media_assets", "ck_media_assets_source_kind", f"source_kind IN ({SOURCE_KIND})")
    _replace_check("media_jobs", "ck_media_jobs_job_kind", f"job_kind IN ({JOB_KIND})")

    op.add_column("media_assets", sa.Column("source_invocation_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_media_assets_source_invocation_id_model_invocations"),
        "media_assets",
        "model_invocations",
        ["source_invocation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_media_assets_source_invocation_id",
        "media_assets",
        ["source_invocation_id"],
    )

    op.add_column("media_jobs", sa.Column("source_event_id", sa.Uuid(), nullable=True))
    op.add_column("media_jobs", sa.Column("source_invocation_id", sa.Uuid(), nullable=True))
    op.add_column(
        "media_jobs",
        sa.Column("provider_config_json", JSONB, nullable=True),
    )
    op.execute("UPDATE media_jobs SET provider_config_json = '{}'::jsonb")
    op.alter_column("media_jobs", "provider_config_json", nullable=False)
    op.create_foreign_key(
        op.f("fk_media_jobs_source_event_id_world_events"),
        "media_jobs",
        "world_events",
        ["source_event_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("fk_media_jobs_source_invocation_id_model_invocations"),
        "media_jobs",
        "model_invocations",
        ["source_invocation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_media_jobs_source_event_id", "media_jobs", ["source_event_id"])
    op.create_index(
        "ix_media_jobs_source_invocation_id",
        "media_jobs",
        ["source_invocation_id"],
    )

    op.create_table(
        "media_objects",
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("object_role", sa.String(length=40), nullable=False),
        sa.Column("storage_uri", sa.String(length=500), nullable=False),
        sa.Column("filename", sa.String(length=220), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("sample_rate_hz", sa.Integer(), nullable=True),
        sa.Column("audio_channels", sa.Integer(), nullable=True),
        sa.Column("frame_rate", sa.Float(), nullable=True),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            f"object_role IN ({OBJECT_ROLE})",
            name=op.f("ck_media_objects_object_role"),
        ),
        sa.CheckConstraint(
            "size_bytes >= 0",
            name=op.f("ck_media_objects_size_bytes_nonnegative"),
        ),
        sa.CheckConstraint(
            "width IS NULL OR width >= 0", name=op.f("ck_media_objects_width_nonnegative")
        ),
        sa.CheckConstraint(
            "height IS NULL OR height >= 0", name=op.f("ck_media_objects_height_nonnegative")
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name=op.f("ck_media_objects_duration_ms_nonnegative"),
        ),
        sa.CheckConstraint(
            "sample_rate_hz IS NULL OR sample_rate_hz >= 0",
            name=op.f("ck_media_objects_sample_rate_hz_nonnegative"),
        ),
        sa.CheckConstraint(
            "audio_channels IS NULL OR audio_channels >= 0",
            name=op.f("ck_media_objects_audio_channels_nonnegative"),
        ),
        sa.CheckConstraint(
            "frame_rate IS NULL OR frame_rate >= 0",
            name=op.f("ck_media_objects_frame_rate_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["media_assets.id"],
            name=op.f("fk_media_objects_asset_id_media_assets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_media_objects_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_media_objects_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_objects")),
        sa.UniqueConstraint("storage_uri", name=op.f("uq_media_objects_storage_uri")),
    )
    op.create_index("ix_media_objects_asset_role", "media_objects", ["asset_id", "object_role"])
    op.create_index("ix_media_objects_checksum", "media_objects", ["checksum_sha256"])
    op.create_index(
        "ix_media_objects_worldline_created",
        "media_objects",
        ["world_id", "worldline_id", "created_at"],
    )

    op.create_table(
        "media_references",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("ref_kind", sa.String(length=40), nullable=False),
        sa.Column("ref_id", sa.Uuid(), nullable=False),
        sa.Column("ref_role", sa.String(length=40), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(f"ref_kind IN ({REF_KIND})", name=op.f("ck_media_references_ref_kind")),
        sa.CheckConstraint(f"ref_role IN ({REF_ROLE})", name=op.f("ck_media_references_ref_role")),
        sa.CheckConstraint(
            "display_order >= 0",
            name=op.f("ck_media_references_display_order_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["media_assets.id"],
            name=op.f("fk_media_references_asset_id_media_assets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_media_references_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_media_references_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_references")),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "asset_id",
            "ref_kind",
            "ref_id",
            "ref_role",
            name=op.f("uq_media_references_identity"),
        ),
    )
    op.create_index("ix_media_references_asset_id", "media_references", ["asset_id"])
    op.create_index(
        "ix_media_references_target",
        "media_references",
        ["world_id", "worldline_id", "ref_kind", "ref_id"],
    )
    op.create_index(
        "ix_media_references_worldline_created",
        "media_references",
        ["world_id", "worldline_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_media_references_worldline_created", table_name="media_references")
    op.drop_index("ix_media_references_target", table_name="media_references")
    op.drop_index("ix_media_references_asset_id", table_name="media_references")
    op.drop_table("media_references")

    op.drop_index("ix_media_objects_worldline_created", table_name="media_objects")
    op.drop_index("ix_media_objects_checksum", table_name="media_objects")
    op.drop_index("ix_media_objects_asset_role", table_name="media_objects")
    op.drop_table("media_objects")

    op.drop_index("ix_media_jobs_source_invocation_id", table_name="media_jobs")
    op.drop_index("ix_media_jobs_source_event_id", table_name="media_jobs")
    op.drop_constraint(
        op.f("fk_media_jobs_source_invocation_id_model_invocations"),
        "media_jobs",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_media_jobs_source_event_id_world_events"),
        "media_jobs",
        type_="foreignkey",
    )
    op.drop_column("media_jobs", "provider_config_json")
    op.drop_column("media_jobs", "source_invocation_id")
    op.drop_column("media_jobs", "source_event_id")

    op.drop_index("ix_media_assets_source_invocation_id", table_name="media_assets")
    op.drop_constraint(
        op.f("fk_media_assets_source_invocation_id_model_invocations"),
        "media_assets",
        type_="foreignkey",
    )
    op.drop_column("media_assets", "source_invocation_id")

    _replace_check(
        "media_jobs",
        "ck_media_jobs_job_kind",
        "job_kind IN ('image_generation', 'image_edit', 'speech_generation', "
        "'speech_transcription', 'background_removal', 'composition', "
        "'upload_import', 'vision_analysis')",
    )
    _replace_check(
        "media_assets",
        "ck_media_assets_source_kind",
        "source_kind IN ('provider_generated', 'manual_upload', 'imported_original', "
        "'composed', 'background_removed')",
    )
    _replace_check(
        "media_assets",
        "ck_media_assets_asset_role",
        "asset_role IN ('original_image', 'reference_image', 'mask_image', "
        "'transparent_png', 'composite_image', 'scene_background', "
        "'character_sprite', 'character_expression', 'character_pose', 'event_cg', "
        "'speech_audio', 'voice_file', 'voice_sample', 'transcript_audio')",
    )
    _replace_check(
        "media_assets",
        "ck_media_assets_asset_kind",
        "asset_kind IN ('image', 'audio')",
    )


def _replace_check(table_name: str, constraint_name: str, condition: str) -> None:
    formatted_name = op.f(constraint_name)
    op.drop_constraint(formatted_name, table_name, type_="check")
    op.create_check_constraint(formatted_name, table_name, condition)
