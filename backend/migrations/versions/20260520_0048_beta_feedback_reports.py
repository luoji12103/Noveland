"""Add private beta feedback reports.

Revision ID: 20260520_0048
Revises: 20260517_0047
Create Date: 2026-05-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260520_0048"
down_revision: str | None = "20260517_0047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "beta_feedback_reports",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=False),
        sa.Column("player_actor_id", sa.Uuid(), nullable=True),
        sa.Column("issue_type", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reporter_note", sa.Text(), nullable=True),
        sa.Column("evidence_refs", JSONB, nullable=False),
        sa.Column("repair_proposal_refs", JSONB, nullable=False),
        sa.Column("triage_note", sa.Text(), nullable=True),
        sa.Column("triaged_by_actor_ref", sa.String(length=160), nullable=True),
        sa.Column("triaged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("moderation_report_id", sa.Uuid(), nullable=True),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
            "issue_type IN ("
            "'dialogue', 'persona', 'memory', 'sprite', 'background', 'voice', 'playback', "
            "'provider', 'quota', 'session_recovery', 'ux', 'worldline', 'other'"
            ")",
            name=op.f("ck_beta_feedback_reports_issue_type"),
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name=op.f("ck_beta_feedback_reports_severity"),
        ),
        sa.CheckConstraint(
            "status IN ("
            "'submitted', 'triaged', 'investigating', 'linked_to_repair', "
            "'resolved', 'dismissed'"
            ")",
            name=op.f("ck_beta_feedback_reports_status"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_beta_feedback_reports_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_beta_feedback_reports_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reporter_user_id"],
            ["users.id"],
            name=op.f("fk_beta_feedback_reports_reporter_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["player_actor_id"],
            ["player_actor_profiles.id"],
            name=op.f("fk_beta_feedback_reports_player_actor_id_player_actor_profiles"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_beta_feedback_reports")),
    )
    op.create_index(
        "ix_beta_feedback_reports_world_status",
        "beta_feedback_reports",
        ["world_id", "status"],
    )
    op.create_index(
        "ix_beta_feedback_reports_worldline_status",
        "beta_feedback_reports",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_beta_feedback_reports_reporter",
        "beta_feedback_reports",
        ["world_id", "reporter_user_id"],
    )
    op.create_index(
        "ix_beta_feedback_reports_issue_type",
        "beta_feedback_reports",
        ["world_id", "issue_type"],
    )
    op.create_index(
        "ix_beta_feedback_reports_created",
        "beta_feedback_reports",
        ["world_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_beta_feedback_reports_created", table_name="beta_feedback_reports")
    op.drop_index("ix_beta_feedback_reports_issue_type", table_name="beta_feedback_reports")
    op.drop_index("ix_beta_feedback_reports_reporter", table_name="beta_feedback_reports")
    op.drop_index("ix_beta_feedback_reports_worldline_status", table_name="beta_feedback_reports")
    op.drop_index("ix_beta_feedback_reports_world_status", table_name="beta_feedback_reports")
    op.drop_table("beta_feedback_reports")
