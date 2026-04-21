"""Add local pgvector-backed agent memory items.

Revision ID: 20260417_0006
Revises: 20260417_0005
Create Date: 2026-04-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260417_0006"
down_revision: str | None = "20260417_0005"
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
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "agent_memory_items",
        *common_columns(),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=False),
        sa.Column(
            "visibility",
            sa.String(length=16),
            server_default=sa.text("'private'"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint("visibility = 'private'", name="ck_agent_memory_items_visibility"),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name="fk_agent_memory_items_agent_id_agents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_event_id"],
            ["world_events.id"],
            name="fk_agent_memory_items_source_event_id_world_events",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name="fk_agent_memory_items_world_id_worlds",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agent_memory_items"),
    )
    op.execute(
        "ALTER TABLE agent_memory_items "
        "ALTER COLUMN embedding TYPE vector(1536) "
        "USING embedding::vector(1536)"
    )
    op.create_index(
        "ix_agent_memory_items_world_agent",
        "agent_memory_items",
        ["world_id", "agent_id"],
    )
    op.create_index(
        "ix_agent_memory_items_world_agent_active",
        "agent_memory_items",
        ["world_id", "agent_id", "is_active"],
    )
    op.create_index(
        "ix_agent_memory_items_source_event_id",
        "agent_memory_items",
        ["source_event_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_memory_items_source_event_id", table_name="agent_memory_items")
    op.drop_index("ix_agent_memory_items_world_agent_active", table_name="agent_memory_items")
    op.drop_index("ix_agent_memory_items_world_agent", table_name="agent_memory_items")
    op.drop_table("agent_memory_items")
