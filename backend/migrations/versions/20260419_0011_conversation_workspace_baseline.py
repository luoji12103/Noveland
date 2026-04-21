"""Add conversation workspace baseline.

Revision ID: 20260419_0011
Revises: 20260417_0010
Create Date: 2026-04-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260419_0011"
down_revision: str | None = "20260417_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversation_sessions",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("scene_id", sa.Uuid(), nullable=True),
        sa.Column("session_key", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("scope_type", sa.String(length=16), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("opening_prompt", sa.Text(), nullable=False),
        sa.Column("max_turns", sa.Integer(), nullable=False),
        sa.Column("next_turn_index", sa.Integer(), server_default=sa.text("0"), nullable=False),
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
            "scope_type IN ('scene', 'world')",
            name="ck_conversation_sessions_scope_type",
        ),
        sa.CheckConstraint(
            "mode IN ('manual_chain', 'auto_dialogue')",
            name="ck_conversation_sessions_mode",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'running', 'paused', 'completed', 'failed')",
            name="ck_conversation_sessions_status",
        ),
        sa.CheckConstraint("max_turns > 0", name="ck_conversation_sessions_max_turns_positive"),
        sa.CheckConstraint(
            "next_turn_index >= 0",
            name="ck_conversation_sessions_next_turn_index_non_negative",
        ),
        sa.CheckConstraint(
            "(scope_type = 'scene' AND scene_id IS NOT NULL) OR "
            "(scope_type = 'world' AND scene_id IS NULL)",
            name="ck_conversation_sessions_scene_scope_consistency",
        ),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "world_id",
            "session_key",
            name="uq_conversation_sessions_world_session_key",
        ),
    )
    op.create_index(
        "ix_conversation_sessions_world_id",
        "conversation_sessions",
        ["world_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_sessions_scene_id",
        "conversation_sessions",
        ["scene_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_sessions_world_mode_status",
        "conversation_sessions",
        ["world_id", "mode", "status"],
        unique=False,
    )

    op.create_table(
        "conversation_participants",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("turn_order", sa.Integer(), nullable=False),
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
        sa.CheckConstraint(
            "turn_order >= 0",
            name="ck_conversation_participants_turn_order_non_negative",
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["conversation_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "agent_id",
            name="uq_conversation_participants_session_agent",
        ),
        sa.UniqueConstraint(
            "session_id",
            "turn_order",
            name="uq_conversation_participants_session_turn_order",
        ),
    )
    op.create_index(
        "ix_conversation_participants_session_id",
        "conversation_participants",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_participants_agent_id",
        "conversation_participants",
        ["agent_id"],
        unique=False,
    )

    op.create_table(
        "conversation_turns",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("speaker_kind", sa.String(length=16), nullable=False),
        sa.Column("speaker_agent_id", sa.Uuid(), nullable=True),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("output_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
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
            "speaker_kind IN ('operator', 'agent')",
            name="ck_conversation_turns_speaker_kind",
        ),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed')",
            name="ck_conversation_turns_status",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runtime_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["conversation_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["speaker_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "turn_index",
            name="uq_conversation_turns_session_turn_index",
        ),
    )
    op.create_index(
        "ix_conversation_turns_session_id",
        "conversation_turns",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_turns_speaker_agent_id",
        "conversation_turns",
        ["speaker_agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_turns_run_id",
        "conversation_turns",
        ["run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_turns_run_id", table_name="conversation_turns")
    op.drop_index("ix_conversation_turns_speaker_agent_id", table_name="conversation_turns")
    op.drop_index("ix_conversation_turns_session_id", table_name="conversation_turns")
    op.drop_table("conversation_turns")
    op.drop_index("ix_conversation_participants_agent_id", table_name="conversation_participants")
    op.drop_index("ix_conversation_participants_session_id", table_name="conversation_participants")
    op.drop_table("conversation_participants")
    op.drop_index("ix_conversation_sessions_world_mode_status", table_name="conversation_sessions")
    op.drop_index("ix_conversation_sessions_scene_id", table_name="conversation_sessions")
    op.drop_index("ix_conversation_sessions_world_id", table_name="conversation_sessions")
    op.drop_table("conversation_sessions")
