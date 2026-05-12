"""Add visual sprite and scene asset system.

Revision ID: 20260512_0037
Revises: 20260512_0036
Create Date: 2026-05-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260512_0037"
down_revision: str | None = "20260512_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "character_sprite_sets",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("style_key", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("default_variant_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            sa.String(length=32),
            server_default=sa.text("'world_admin'"),
            nullable=False,
        ),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled', 'deleted')",
            name=op.f("ck_character_sprite_sets_status"),
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'world_admin', 'world_member', 'developer_only', 'hidden')",
            name=op.f("ck_character_sprite_sets_visibility"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_character_sprite_sets_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_character_sprite_sets_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name=op.f("fk_character_sprite_sets_agent_id_agents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_character_sprite_sets")),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "agent_id",
            "style_key",
            name="uq_character_sprite_sets_agent_style",
        ),
    )
    op.create_index(
        "ix_character_sprite_sets_worldline_agent",
        "character_sprite_sets",
        ["world_id", "worldline_id", "agent_id"],
    )
    op.create_index(
        "ix_character_sprite_sets_worldline_status",
        "character_sprite_sets",
        ["world_id", "worldline_id", "status"],
    )

    op.create_table(
        "character_sprite_variants",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("sprite_set_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("expression_key", sa.String(length=80), nullable=False),
        sa.Column("pose_key", sa.String(length=80), nullable=True),
        sa.Column("outfit_key", sa.String(length=80), nullable=True),
        sa.Column("mood_tags", JSONB, nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            sa.String(length=32),
            server_default=sa.text("'world_admin'"),
            nullable=False,
        ),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled', 'deleted')",
            name=op.f("ck_character_sprite_variants_status"),
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'world_admin', 'world_member', 'developer_only', 'hidden')",
            name=op.f("ck_character_sprite_variants_visibility"),
        ),
        sa.CheckConstraint(
            "priority >= 0",
            name=op.f("ck_character_sprite_variants_priority_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_character_sprite_variants_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_character_sprite_variants_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sprite_set_id"],
            ["character_sprite_sets.id"],
            name=op.f("fk_character_sprite_variants_sprite_set_id_character_sprite_sets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["media_assets.id"],
            name=op.f("fk_character_sprite_variants_asset_id_media_assets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_character_sprite_variants")),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "sprite_set_id",
            "asset_id",
            "expression_key",
            "pose_key",
            "outfit_key",
            name="uq_character_sprite_variants_asset_keys",
        ),
    )
    op.create_index(
        "ix_character_sprite_variants_set",
        "character_sprite_variants",
        ["sprite_set_id"],
    )
    op.create_index(
        "ix_character_sprite_variants_worldline_expr",
        "character_sprite_variants",
        ["world_id", "worldline_id", "expression_key"],
    )
    op.create_index(
        "ix_character_sprite_variants_asset",
        "character_sprite_variants",
        ["asset_id"],
    )

    op.create_table(
        "scene_background_profiles",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("scene_id", sa.Uuid(), nullable=True),
        sa.Column("location_key", sa.String(length=120), nullable=False),
        sa.Column("time_of_day", sa.String(length=40), nullable=True),
        sa.Column("weather_key", sa.String(length=80), nullable=True),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            sa.String(length=32),
            server_default=sa.text("'world_admin'"),
            nullable=False,
        ),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled', 'deleted')",
            name=op.f("ck_scene_background_profiles_status"),
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'world_admin', 'world_member', 'developer_only', 'hidden')",
            name=op.f("ck_scene_background_profiles_visibility"),
        ),
        sa.CheckConstraint(
            "priority >= 0",
            name=op.f("ck_scene_background_profiles_priority_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_scene_background_profiles_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_scene_background_profiles_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scene_id"],
            ["scenes.id"],
            name=op.f("fk_scene_background_profiles_scene_id_scenes"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["media_assets.id"],
            name=op.f("fk_scene_background_profiles_asset_id_media_assets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scene_background_profiles")),
    )
    op.create_index(
        "ix_scene_background_profiles_worldline_scene",
        "scene_background_profiles",
        ["world_id", "worldline_id", "scene_id"],
    )
    op.create_index(
        "ix_scene_background_profiles_worldline_location",
        "scene_background_profiles",
        ["world_id", "worldline_id", "location_key"],
    )
    op.create_index(
        "ix_scene_background_profiles_asset",
        "scene_background_profiles",
        ["asset_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_scene_background_profiles_asset", table_name="scene_background_profiles")
    op.drop_index(
        "ix_scene_background_profiles_worldline_location",
        table_name="scene_background_profiles",
    )
    op.drop_index(
        "ix_scene_background_profiles_worldline_scene",
        table_name="scene_background_profiles",
    )
    op.drop_table("scene_background_profiles")

    op.drop_index("ix_character_sprite_variants_asset", table_name="character_sprite_variants")
    op.drop_index(
        "ix_character_sprite_variants_worldline_expr",
        table_name="character_sprite_variants",
    )
    op.drop_index("ix_character_sprite_variants_set", table_name="character_sprite_variants")
    op.drop_table("character_sprite_variants")

    op.drop_index(
        "ix_character_sprite_sets_worldline_status",
        table_name="character_sprite_sets",
    )
    op.drop_index(
        "ix_character_sprite_sets_worldline_agent",
        table_name="character_sprite_sets",
    )
    op.drop_table("character_sprite_sets")
