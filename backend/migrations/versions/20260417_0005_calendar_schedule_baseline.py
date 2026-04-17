"""Add agent calendar entries and world schedule rules.

Revision ID: 20260417_0005
Revises: 20260416_0004
Create Date: 2026-04-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260417_0005"
down_revision: str | None = "20260416_0004"
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
        "agent_calendar_entries",
        *common_columns(),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recurrence_rule", sa.String(length=240), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'cancelled')",
            name="ck_agent_calendar_entries_status",
        ),
        sa.CheckConstraint(
            "ends_at IS NULL OR ends_at >= starts_at",
            name="ck_agent_calendar_entries_ends_after_starts",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name="fk_agent_calendar_entries_agent_id_agents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name="fk_agent_calendar_entries_world_id_worlds",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agent_calendar_entries"),
    )
    op.create_index(
        "ix_agent_calendar_entries_world_agent_starts",
        "agent_calendar_entries",
        ["world_id", "agent_id", "starts_at"],
    )
    op.create_index(
        "ix_agent_calendar_entries_world_agent_status",
        "agent_calendar_entries",
        ["world_id", "agent_id", "status"],
    )

    op.create_table(
        "world_schedule_rules",
        *common_columns(),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint(
            "kind IN ('weekday', 'weekend', 'timetable')",
            name="ck_world_schedule_rules_kind",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name="fk_world_schedule_rules_world_id_worlds",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_world_schedule_rules"),
        sa.UniqueConstraint("world_id", "rule_key", name="uq_world_schedule_rules_world_rule_key"),
    )
    op.create_index("ix_world_schedule_rules_world_id", "world_schedule_rules", ["world_id"])
    op.create_index(
        "ix_world_schedule_rules_world_enabled",
        "world_schedule_rules",
        ["world_id", "is_enabled"],
    )


def downgrade() -> None:
    op.drop_index("ix_world_schedule_rules_world_enabled", table_name="world_schedule_rules")
    op.drop_index("ix_world_schedule_rules_world_id", table_name="world_schedule_rules")
    op.drop_table("world_schedule_rules")
    op.drop_index(
        "ix_agent_calendar_entries_world_agent_status",
        table_name="agent_calendar_entries",
    )
    op.drop_index(
        "ix_agent_calendar_entries_world_agent_starts",
        table_name="agent_calendar_entries",
    )
    op.drop_table("agent_calendar_entries")
