"""Add runtime diagnostic events.

Revision ID: 20260417_0008
Revises: 20260417_0007
Create Date: 2026-04-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260417_0008"
down_revision: str | None = "20260417_0007"
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
        "runtime_diagnostic_events",
        *common_columns(),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("component", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "severity IN ('info', 'warning', 'error')",
            name="ck_runtime_diagnostic_events_severity",
        ),
        sa.CheckConstraint(
            "component IN ('runtime', 'provider', 'agent', 'event_publisher', 'api')",
            name="ck_runtime_diagnostic_events_component",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name="fk_runtime_diagnostic_events_agent_id_agents",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["provider_profile_id"],
            ["provider_profiles.id"],
            name="fk_runtime_diag_events_provider_profile",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["agent_runtime_runs.id"],
            name="fk_runtime_diagnostic_events_run_id_agent_runtime_runs",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name="fk_runtime_diagnostic_events_world_id_worlds",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_runtime_diagnostic_events"),
    )
    op.create_index(
        "ix_runtime_diagnostic_events_occurred_at",
        "runtime_diagnostic_events",
        ["occurred_at"],
    )
    op.create_index(
        "ix_runtime_diagnostic_events_severity_component",
        "runtime_diagnostic_events",
        ["severity", "component"],
    )
    op.create_index(
        "ix_runtime_diagnostic_events_world_occurred_at",
        "runtime_diagnostic_events",
        ["world_id", "occurred_at"],
    )
    op.create_index(
        "ix_runtime_diagnostic_events_agent_occurred_at",
        "runtime_diagnostic_events",
        ["agent_id", "occurred_at"],
    )
    op.create_index(
        "ix_runtime_diagnostic_events_run_id",
        "runtime_diagnostic_events",
        ["run_id"],
    )
    op.create_index(
        "ix_runtime_diagnostic_events_provider_profile_id",
        "runtime_diagnostic_events",
        ["provider_profile_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_runtime_diagnostic_events_provider_profile_id",
        table_name="runtime_diagnostic_events",
    )
    op.drop_index("ix_runtime_diagnostic_events_run_id", table_name="runtime_diagnostic_events")
    op.drop_index(
        "ix_runtime_diagnostic_events_agent_occurred_at",
        table_name="runtime_diagnostic_events",
    )
    op.drop_index(
        "ix_runtime_diagnostic_events_world_occurred_at",
        table_name="runtime_diagnostic_events",
    )
    op.drop_index(
        "ix_runtime_diagnostic_events_severity_component",
        table_name="runtime_diagnostic_events",
    )
    op.drop_index(
        "ix_runtime_diagnostic_events_occurred_at",
        table_name="runtime_diagnostic_events",
    )
    op.drop_table("runtime_diagnostic_events")
