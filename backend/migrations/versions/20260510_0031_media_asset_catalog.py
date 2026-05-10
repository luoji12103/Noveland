"""Add media asset catalog.

Revision ID: 20260510_0031
Revises: 20260510_0030
Create Date: 2026-05-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260510_0031"
down_revision: str | None = "20260510_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "media_asset_tags",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("tag_type", sa.String(length=40), nullable=False),
        sa.Column("tag_key", sa.String(length=80), nullable=False),
        sa.Column("tag_value", sa.String(length=220), nullable=False),
        sa.Column("confidence", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.Column(
            "source_kind",
            sa.String(length=24),
            server_default=sa.text("'manual'"),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            sa.String(length=32),
            server_default=sa.text("'world_admin'"),
            nullable=False,
        ),
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
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_media_asset_tags_confidence_range"),
        ),
        sa.CheckConstraint(
            "source_kind IN ('manual', 'imported', 'system', 'provider', 'derived')",
            name=op.f("ck_media_asset_tags_source_kind"),
        ),
        sa.CheckConstraint(
            "visibility IN ("
            "'private', 'world_admin', 'world_member', 'player_visible', "
            "'reader_visible', 'developer_only', 'hidden'"
            ")",
            name=op.f("ck_media_asset_tags_visibility"),
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["media_assets.id"],
            name=op.f("fk_media_asset_tags_asset_id_media_assets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_media_asset_tags_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_media_asset_tags_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_asset_tags")),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "asset_id",
            "tag_type",
            "tag_key",
            "tag_value",
            name=op.f("uq_media_asset_tags_identity"),
        ),
    )
    op.create_index("ix_media_asset_tags_asset_id", "media_asset_tags", ["asset_id"])
    op.create_index(
        "ix_media_asset_tags_worldline_tag",
        "media_asset_tags",
        ["world_id", "worldline_id", "tag_type", "tag_key", "tag_value"],
    )
    op.create_index(
        "ix_media_asset_tags_worldline_visibility",
        "media_asset_tags",
        ["world_id", "worldline_id", "visibility"],
    )

    op.create_table(
        "media_asset_collections",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("collection_kind", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_agent_id", sa.Uuid(), nullable=True),
        sa.Column(
            "visibility",
            sa.String(length=32),
            server_default=sa.text("'world_admin'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
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
            "status IN ('active', 'deleted')",
            name=op.f("ck_media_asset_collections_status"),
        ),
        sa.CheckConstraint(
            "visibility IN ("
            "'private', 'world_admin', 'world_member', 'player_visible', "
            "'reader_visible', 'developer_only', 'hidden'"
            ")",
            name=op.f("ck_media_asset_collections_visibility"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_agent_id"],
            ["agents.id"],
            name=op.f("fk_media_asset_collections_owner_agent_id_agents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_media_asset_collections_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_media_asset_collections_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_asset_collections")),
    )
    op.create_index(
        "ix_media_asset_collections_owner_agent_id",
        "media_asset_collections",
        ["owner_agent_id"],
    )
    op.create_index(
        "ix_media_asset_collections_worldline_kind",
        "media_asset_collections",
        ["world_id", "worldline_id", "collection_kind"],
    )
    op.create_index(
        "ix_media_asset_collections_worldline_status_created",
        "media_asset_collections",
        ["world_id", "worldline_id", "status", "created_at"],
    )
    op.create_index(
        "ix_media_asset_collections_worldline_visibility",
        "media_asset_collections",
        ["world_id", "worldline_id", "visibility"],
    )

    op.create_table(
        "media_asset_collection_items",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
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
            "display_order >= 0",
            name=op.f("ck_media_asset_collection_items_display_order_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["media_assets.id"],
            name=op.f("fk_media_asset_collection_items_asset_id_media_assets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["media_asset_collections.id"],
            name=op.f("fk_media_asset_collection_items_collection_id_media_asset_collections"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_media_asset_collection_items_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_media_asset_collection_items_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_asset_collection_items")),
        sa.UniqueConstraint(
            "collection_id",
            "asset_id",
            "role",
            name=op.f("uq_media_asset_collection_items_collection_asset_role"),
        ),
    )
    op.create_index(
        "ix_media_asset_collection_items_asset_id",
        "media_asset_collection_items",
        ["asset_id"],
    )
    op.create_index(
        "ix_media_asset_collection_items_collection_order",
        "media_asset_collection_items",
        ["collection_id", "display_order"],
    )
    op.create_index(
        "ix_media_asset_collection_items_worldline_asset",
        "media_asset_collection_items",
        ["world_id", "worldline_id", "asset_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_media_asset_collection_items_worldline_asset",
        table_name="media_asset_collection_items",
    )
    op.drop_index(
        "ix_media_asset_collection_items_collection_order",
        table_name="media_asset_collection_items",
    )
    op.drop_index(
        "ix_media_asset_collection_items_asset_id",
        table_name="media_asset_collection_items",
    )
    op.drop_table("media_asset_collection_items")

    op.drop_index(
        "ix_media_asset_collections_worldline_visibility",
        table_name="media_asset_collections",
    )
    op.drop_index(
        "ix_media_asset_collections_worldline_status_created",
        table_name="media_asset_collections",
    )
    op.drop_index(
        "ix_media_asset_collections_worldline_kind",
        table_name="media_asset_collections",
    )
    op.drop_index("ix_media_asset_collections_owner_agent_id", table_name="media_asset_collections")
    op.drop_table("media_asset_collections")

    op.drop_index("ix_media_asset_tags_worldline_visibility", table_name="media_asset_tags")
    op.drop_index("ix_media_asset_tags_worldline_tag", table_name="media_asset_tags")
    op.drop_index("ix_media_asset_tags_asset_id", table_name="media_asset_tags")
    op.drop_table("media_asset_tags")
