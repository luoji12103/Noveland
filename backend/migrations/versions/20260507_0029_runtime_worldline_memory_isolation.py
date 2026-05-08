"""Harden runtime worldline memory isolation.

Revision ID: 20260507_0029
Revises: 20260507_0028
Create Date: 2026-05-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260507_0029"
down_revision: str | None = "20260507_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _add_worldline_column("agent_runtime_runs")
    _add_worldline_column("conversation_sessions")
    _add_worldline_column("agent_profile_snapshots")

    _backfill_worldline("agent_runtime_runs")
    _backfill_worldline("conversation_sessions")
    _backfill_worldline("agent_profile_snapshots")

    op.create_index(
        "ix_agent_runtime_runs_worldline_agent_started_at",
        "agent_runtime_runs",
        ["world_id", "worldline_id", "agent_id", "started_at"],
    )
    op.create_index(
        "ix_conversation_sessions_worldline_mode_status",
        "conversation_sessions",
        ["world_id", "worldline_id", "mode", "status"],
    )

    with op.batch_alter_table("agent_profile_snapshots") as batch_op:
        batch_op.drop_constraint("uq_agent_profile_snapshots_world_agent", type_="unique")
        batch_op.drop_index("ix_agent_profile_snapshots_world_agent")
        batch_op.create_unique_constraint(
            "uq_agent_profile_snapshots_worldline_agent",
            ["world_id", "worldline_id", "agent_id"],
        )
        batch_op.create_index(
            "ix_agent_profile_snapshots_worldline_agent",
            ["world_id", "worldline_id", "agent_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_profile_snapshots") as batch_op:
        batch_op.drop_index("ix_agent_profile_snapshots_worldline_agent")
        batch_op.drop_constraint("uq_agent_profile_snapshots_worldline_agent", type_="unique")
        batch_op.create_unique_constraint(
            "uq_agent_profile_snapshots_world_agent",
            ["world_id", "agent_id"],
        )
        batch_op.create_index("ix_agent_profile_snapshots_world_agent", ["world_id", "agent_id"])

    op.drop_index(
        "ix_conversation_sessions_worldline_mode_status",
        table_name="conversation_sessions",
    )
    op.drop_index(
        "ix_agent_runtime_runs_worldline_agent_started_at",
        table_name="agent_runtime_runs",
    )

    for table_name in ("agent_profile_snapshots", "conversation_sessions", "agent_runtime_runs"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("worldline_id")


def _add_worldline_column(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.add_column(sa.Column("worldline_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            f"fk_{table_name}_worldline_id_worldlines",
            "worldlines",
            ["worldline_id"],
            ["id"],
            ondelete="CASCADE",
        )


def _backfill_worldline(table_name: str) -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE {table_name}
            SET worldline_id = worldlines.id
            FROM worldlines
            WHERE {table_name}.world_id = worldlines.world_id
              AND worldlines.parent_worldline_id IS NULL
              AND {table_name}.worldline_id IS NULL
            """
        )
    )
