"""Add player privacy requests.

Revision ID: 20260516_0043
Revises: 20260515_0042
Create Date: 2026-05-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260516_0043"
down_revision: str | None = "20260515_0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "player_privacy_requests",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("request_kind", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("target_ref_kind", sa.String(length=80), nullable=True),
        sa.Column("target_ref_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("summary", JSONB, nullable=False),
        sa.Column("redaction_plan", JSONB, nullable=False),
        sa.Column("created_by_actor_ref", sa.String(length=160), nullable=False),
        sa.Column("reviewed_by_actor_ref", sa.String(length=160), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
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
            "request_kind IN ('export', 'delete')",
            name=op.f("ck_player_privacy_requests_request_kind"),
        ),
        sa.CheckConstraint(
            "status IN ("
            "'requested', "
            "'under_review', "
            "'approved_for_redaction', "
            "'rejected', "
            "'completed'"
            ")",
            name=op.f("ck_player_privacy_requests_status"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_player_privacy_requests_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_player_privacy_requests_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_player_privacy_requests_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_player_privacy_requests")),
    )
    op.create_index(
        "ix_player_privacy_requests_worldline_user",
        "player_privacy_requests",
        ["world_id", "worldline_id", "user_id"],
    )
    op.create_index(
        "ix_player_privacy_requests_status",
        "player_privacy_requests",
        ["world_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_player_privacy_requests_status", table_name="player_privacy_requests")
    op.drop_index("ix_player_privacy_requests_worldline_user", table_name="player_privacy_requests")
    op.drop_table("player_privacy_requests")
