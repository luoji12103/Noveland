"""Add agent persona and observation baseline.

Revision ID: 20260417_0010
Revises: 20260417_0009
Create Date: 2026-04-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260417_0010"
down_revision: str | None = "20260417_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_personas",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("persona_text", sa.Text(), nullable=False),
        sa.Column(
            "behavior_policy",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "id",
            sa.Uuid(),
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
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", name="uq_agent_personas_agent_id"),
    )
    op.create_index(
        "ix_agent_personas_world_agent",
        "agent_personas",
        ["world_id", "agent_id"],
        unique=False,
    )

    op.create_table(
        "agent_observations",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("source_event_id", sa.Uuid(), nullable=True),
        sa.Column("observation_type", sa.String(length=80), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "id",
            sa.Uuid(),
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
        sa.CheckConstraint(
            "observation_type <> ''",
            name="ck_agent_observations_observation_type_present",
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_event_id"], ["world_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_observations_world_agent_observed",
        "agent_observations",
        ["world_id", "agent_id", "observed_at"],
        unique=False,
    )
    op.create_index(
        "ix_agent_observations_source_event_id",
        "agent_observations",
        ["source_event_id"],
        unique=False,
    )
    op.create_index(
        "uq_agent_observations_agent_source_event",
        "agent_observations",
        ["agent_id", "source_event_id"],
        unique=True,
        postgresql_where=sa.text("source_event_id IS NOT NULL"),
        sqlite_where=sa.text("source_event_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_agent_observations_agent_source_event", table_name="agent_observations")
    op.drop_index("ix_agent_observations_source_event_id", table_name="agent_observations")
    op.drop_index("ix_agent_observations_world_agent_observed", table_name="agent_observations")
    op.drop_table("agent_observations")
    op.drop_index("ix_agent_personas_world_agent", table_name="agent_personas")
    op.drop_table("agent_personas")
