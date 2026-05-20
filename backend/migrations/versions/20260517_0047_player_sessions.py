"""Add player session resume records.

Revision ID: 20260517_0047
Revises: 20260517_0046
Create Date: 2026-05-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260517_0047"
down_revision: str | None = "20260517_0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "player_sessions",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("player_actor_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_session_id", sa.Uuid(), nullable=True),
        sa.Column("scene_id", sa.Uuid(), nullable=True),
        sa.Column("last_turn_id", sa.Uuid(), nullable=True),
        sa.Column("last_presentation_id", sa.Uuid(), nullable=True),
        sa.Column("route_state", JSONB, nullable=False),
        sa.Column("resume_state", JSONB, nullable=False),
        sa.Column("recovery_status", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'closed')",
            name=op.f("ck_player_sessions_status"),
        ),
        sa.CheckConstraint(
            "recovery_status IN ("
            "'ready', 'stale_conversation', 'missing_media', 'provider_failure', "
            "'media_failure', 'presentation_unavailable'"
            ")",
            name=op.f("ck_player_sessions_recovery_status"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_player_sessions_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_player_sessions_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_player_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["player_actor_id"],
            ["player_actor_profiles.id"],
            name=op.f("fk_player_sessions_player_actor_id_player_actor_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_session_id"],
            ["conversation_sessions.id"],
            name=op.f("fk_player_sessions_conversation_session_id_conversation_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["scene_id"],
            ["scenes.id"],
            name=op.f("fk_player_sessions_scene_id_scenes"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["last_turn_id"],
            ["conversation_turns.id"],
            name=op.f("fk_player_sessions_last_turn_id_conversation_turns"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["last_presentation_id"],
            ["conversation_turn_presentations.id"],
            name=op.f("fk_player_sessions_last_presentation_id_conversation_turn_presentations"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_player_sessions")),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "user_id",
            "player_actor_id",
            name="uq_player_sessions_scope_user_actor",
        ),
    )
    op.create_index(
        "ix_player_sessions_worldline_user",
        "player_sessions",
        ["world_id", "worldline_id", "user_id"],
    )
    op.create_index(
        "ix_player_sessions_conversation",
        "player_sessions",
        ["conversation_session_id"],
    )
    op.create_index(
        "ix_player_sessions_last_seen",
        "player_sessions",
        ["world_id", "last_seen_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_player_sessions_last_seen", table_name="player_sessions")
    op.drop_index("ix_player_sessions_conversation", table_name="player_sessions")
    op.drop_index("ix_player_sessions_worldline_user", table_name="player_sessions")
    op.drop_table("player_sessions")
