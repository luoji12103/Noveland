"""Create core persistent schema.

Revision ID: 20260415_0001
Revises:
Create Date: 2026-04-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260415_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def common_columns() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "platform_settings",
        *common_columns(),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column(
            "value",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_platform_settings"),
        sa.UniqueConstraint("key", name="uq_platform_settings_key"),
    )

    op.create_table(
        "users",
        *common_columns(),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "worlds",
        *common_columns(),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "rules_config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_worlds_owner_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_worlds"),
        sa.UniqueConstraint("slug", name="uq_worlds_slug"),
    )
    op.create_index("ix_worlds_owner_user_id", "worlds", ["owner_user_id"])

    op.create_table(
        "world_memberships",
        *common_columns(),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "role IN ('world_admin', 'human_user')",
            name="ck_world_memberships_role",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_world_memberships_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name="fk_world_memberships_world_id_worlds",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_world_memberships"),
        sa.UniqueConstraint("world_id", "user_id", name="uq_world_memberships_world_user"),
    )
    op.create_index("ix_world_memberships_user_id", "world_memberships", ["user_id"])
    op.create_index("ix_world_memberships_world_id", "world_memberships", ["world_id"])

    op.create_table(
        "scenes",
        *common_columns(),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scene_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name="fk_scenes_world_id_worlds",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scenes"),
        sa.UniqueConstraint("world_id", "scene_key", name="uq_scenes_world_scene_key"),
    )
    op.create_index("ix_scenes_world_id", "scenes", ["world_id"])

    op.create_table(
        "agents",
        *common_columns(),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("home_scene_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_key", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint("kind IN ('role_agent', 'narrative_agent')", name="ck_agents_kind"),
        sa.ForeignKeyConstraint(
            ["home_scene_id"],
            ["scenes.id"],
            name="fk_agents_home_scene_id_scenes",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name="fk_agents_world_id_worlds",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agents"),
        sa.UniqueConstraint("world_id", "agent_key", name="uq_agents_world_agent_key"),
    )
    op.create_index("ix_agents_home_scene_id", "agents", ["home_scene_id"])
    op.create_index("ix_agents_world_id", "agents", ["world_id"])


def downgrade() -> None:
    op.drop_index("ix_agents_world_id", table_name="agents")
    op.drop_index("ix_agents_home_scene_id", table_name="agents")
    op.drop_table("agents")

    op.drop_index("ix_scenes_world_id", table_name="scenes")
    op.drop_table("scenes")

    op.drop_index("ix_world_memberships_world_id", table_name="world_memberships")
    op.drop_index("ix_world_memberships_user_id", table_name="world_memberships")
    op.drop_table("world_memberships")

    op.drop_index("ix_worlds_owner_user_id", table_name="worlds")
    op.drop_table("worlds")

    op.drop_table("users")
    op.drop_table("platform_settings")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
