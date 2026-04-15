"""Add world clock state and transition audit tables.

Revision ID: 20260415_0002
Revises: 20260415_0001
Create Date: 2026-04-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260415_0002"
down_revision: str | None = "20260415_0001"
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
    op.create_table(
        "world_clock_states",
        *common_columns(),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("current_world_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("wall_time_anchor", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "speed_multiplier",
            sa.Numeric(12, 6),
            server_default=sa.text("1.000000"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint(
            "status IN ('running', 'paused')",
            name="ck_world_clock_states_status",
        ),
        sa.CheckConstraint(
            "speed_multiplier > 0",
            name="ck_world_clock_states_speed_multiplier_positive",
        ),
        sa.CheckConstraint(
            "revision >= 0",
            name="ck_world_clock_states_revision_nonnegative",
        ),
        sa.CheckConstraint(
            "(status = 'paused' AND wall_time_anchor IS NULL) OR "
            "(status = 'running' AND wall_time_anchor IS NOT NULL)",
            name="ck_world_clock_states_wall_time_anchor_matches_status",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name="fk_world_clock_states_world_id_worlds",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_world_clock_states"),
        sa.UniqueConstraint("world_id", name="uq_world_clock_states_world_id"),
    )
    op.create_index("ix_world_clock_states_world_id", "world_clock_states", ["world_id"])

    op.create_table(
        "world_clock_transitions",
        *common_columns(),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transition_type", sa.String(length=32), nullable=False),
        sa.Column("previous_status", sa.String(length=16), nullable=True),
        sa.Column("new_status", sa.String(length=16), nullable=False),
        sa.Column("previous_world_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("new_world_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("wall_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_revision", sa.Integer(), nullable=True),
        sa.Column("new_revision", sa.Integer(), nullable=False),
        sa.Column("actor_ref", sa.String(length=120), nullable=True),
        sa.Column("correlation_id", sa.String(length=120), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "transition_type IN ('initialize', 'pause', 'resume', 'advance', 'skip')",
            name="ck_world_clock_transitions_transition_type",
        ),
        sa.CheckConstraint(
            "previous_status IS NULL OR previous_status IN ('running', 'paused')",
            name="ck_world_clock_transitions_previous_status",
        ),
        sa.CheckConstraint(
            "new_status IN ('running', 'paused')",
            name="ck_world_clock_transitions_new_status",
        ),
        sa.CheckConstraint(
            "previous_revision IS NULL OR previous_revision >= 0",
            name="ck_world_clock_transitions_previous_revision_nonnegative",
        ),
        sa.CheckConstraint(
            "new_revision >= 0",
            name="ck_world_clock_transitions_new_revision_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name="fk_world_clock_transitions_world_id_worlds",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_world_clock_transitions"),
        sa.UniqueConstraint(
            "world_id",
            "new_revision",
            name="uq_world_clock_transitions_world_revision",
        ),
    )
    op.create_index(
        "ix_world_clock_transitions_world_id",
        "world_clock_transitions",
        ["world_id"],
    )
    op.create_index(
        "ix_world_clock_transitions_world_wall_time",
        "world_clock_transitions",
        ["world_id", "wall_time"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_world_clock_transitions_world_wall_time",
        table_name="world_clock_transitions",
    )
    op.drop_index("ix_world_clock_transitions_world_id", table_name="world_clock_transitions")
    op.drop_table("world_clock_transitions")

    op.drop_index("ix_world_clock_states_world_id", table_name="world_clock_states")
    op.drop_table("world_clock_states")
