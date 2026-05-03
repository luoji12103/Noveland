"""Add observation traceability fields.

Revision ID: 20260503_0019
Revises: 20260423_0018
Create Date: 2026-05-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260503_0019"
down_revision: str | None = "20260423_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("agent_observations") as batch_op:
        batch_op.add_column(sa.Column("confidence_score", sa.Float(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "review_status",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'unreviewed'"),
            ),
        )
        batch_op.add_column(
            sa.Column(
                "runtime_use_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )
        batch_op.add_column(sa.Column("last_used_run_id", sa.Uuid(), nullable=True))
        batch_op.create_check_constraint(
            "ck_agent_observations_review_status",
            "review_status IN ('unreviewed', 'approved', 'rejected')",
        )
        batch_op.create_check_constraint(
            "ck_agent_observations_confidence_score_range",
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
        )
        batch_op.create_check_constraint(
            "ck_agent_observations_runtime_use_count_non_negative",
            "runtime_use_count >= 0",
        )
        batch_op.create_foreign_key(
            "fk_agent_observations_last_used_run_id_agent_runtime_runs",
            "agent_runtime_runs",
            ["last_used_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_agent_observations_world_agent_review",
            ["world_id", "agent_id", "review_status"],
            unique=False,
        )
        batch_op.create_index(
            "ix_agent_observations_last_used_run_id",
            ["last_used_run_id"],
            unique=False,
        )
        batch_op.alter_column("review_status", server_default=None)
        batch_op.alter_column("runtime_use_count", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("agent_observations") as batch_op:
        batch_op.drop_index("ix_agent_observations_last_used_run_id")
        batch_op.drop_index("ix_agent_observations_world_agent_review")
        batch_op.drop_constraint(
            "fk_agent_observations_last_used_run_id_agent_runtime_runs",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "ck_agent_observations_runtime_use_count_non_negative",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_agent_observations_confidence_score_range",
            type_="check",
        )
        batch_op.drop_constraint("ck_agent_observations_review_status", type_="check")
        batch_op.drop_column("last_used_run_id")
        batch_op.drop_column("runtime_use_count")
        batch_op.drop_column("review_status")
        batch_op.drop_column("confidence_score")
