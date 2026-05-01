"""Add agent profile snapshots for long-term memory overlays.

Revision ID: 20260423_0018
Revises: 20260423_0017
Create Date: 2026-04-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260423_0018"
down_revision: str | None = "20260423_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type() -> postgresql.JSONB | sa.JSON:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "agent_profile_snapshots",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("aliases", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("identity_notes", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "durable_preferences",
            _json_type(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "long_lived_goals",
            _json_type(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "language_style_preferences",
            _json_type(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "refreshed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("world_id", "agent_id", name="uq_agent_profile_snapshots_world_agent"),
    )
    with op.batch_alter_table("agent_profile_snapshots") as batch_op:
        batch_op.alter_column("aliases", server_default=None)
        batch_op.alter_column("identity_notes", server_default=None)
        batch_op.alter_column("durable_preferences", server_default=None)
        batch_op.alter_column("long_lived_goals", server_default=None)
        batch_op.alter_column("language_style_preferences", server_default=None)
    op.create_index(
        "ix_agent_profile_snapshots_world_agent",
        "agent_profile_snapshots",
        ["world_id", "agent_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_profile_snapshots_world_agent", table_name="agent_profile_snapshots")
    op.drop_table("agent_profile_snapshots")
