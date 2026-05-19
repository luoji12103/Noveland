"""Add private beta invite records.

Revision ID: 20260517_0046
Revises: 20260517_0045
Create Date: 2026-05-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260517_0046"
down_revision: str | None = "20260517_0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "private_beta_invites",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=True),
        sa.Column("invited_email", sa.String(length=320), nullable=True),
        sa.Column("invited_user_id", sa.Uuid(), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("intended_world_role", sa.String(length=32), nullable=False),
        sa.Column("beta_role", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redeemed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_actor_ref", sa.String(length=160), nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=True),
        sa.Column("created_by_actor_ref", sa.String(length=160), nullable=False),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'waitlisted', 'redeemed', 'expired', 'revoked')",
            name=op.f("ck_private_beta_invites_status"),
        ),
        sa.CheckConstraint(
            "intended_world_role IN ('human_user')",
            name=op.f("ck_private_beta_invites_intended_world_role"),
        ),
        sa.CheckConstraint(
            "beta_role IN ('tester', 'player_tester')",
            name=op.f("ck_private_beta_invites_beta_role"),
        ),
        sa.CheckConstraint(
            "length(token_hash) = 64",
            name=op.f("ck_private_beta_invites_token_hash_length"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_private_beta_invites_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_private_beta_invites_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_user_id"],
            ["users.id"],
            name=op.f("fk_private_beta_invites_invited_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["redeemed_by_user_id"],
            ["users.id"],
            name=op.f("fk_private_beta_invites_redeemed_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_private_beta_invites")),
        sa.UniqueConstraint("token_hash", name="uq_private_beta_invites_token_hash"),
    )
    op.create_index(
        "ix_private_beta_invites_world_status",
        "private_beta_invites",
        ["world_id", "status"],
    )
    op.create_index(
        "ix_private_beta_invites_worldline",
        "private_beta_invites",
        ["world_id", "worldline_id"],
    )
    op.create_index(
        "ix_private_beta_invites_invited_user",
        "private_beta_invites",
        ["invited_user_id"],
    )
    op.create_index(
        "ix_private_beta_invites_invited_email",
        "private_beta_invites",
        ["invited_email"],
    )
    op.create_index(
        "ix_private_beta_invites_redeemed_user",
        "private_beta_invites",
        ["redeemed_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_private_beta_invites_redeemed_user", table_name="private_beta_invites")
    op.drop_index("ix_private_beta_invites_invited_email", table_name="private_beta_invites")
    op.drop_index("ix_private_beta_invites_invited_user", table_name="private_beta_invites")
    op.drop_index("ix_private_beta_invites_worldline", table_name="private_beta_invites")
    op.drop_index("ix_private_beta_invites_world_status", table_name="private_beta_invites")
    op.drop_table("private_beta_invites")
