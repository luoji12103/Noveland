"""Add multimodal conversation turn presentations.

Revision ID: 20260512_0038
Revises: 20260512_0037
Create Date: 2026-05-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260512_0038"
down_revision: str | None = "20260512_0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "conversation_turn_presentations",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("turn_id", sa.Uuid(), nullable=False),
        sa.Column("speaker_agent_id", sa.Uuid(), nullable=True),
        sa.Column("emotion_key", sa.String(length=80), nullable=True),
        sa.Column("emotion_intensity", sa.Float(), nullable=True),
        sa.Column("sprite_set_id", sa.Uuid(), nullable=True),
        sa.Column("sprite_variant_id", sa.Uuid(), nullable=True),
        sa.Column("voice_profile_id", sa.Uuid(), nullable=True),
        sa.Column("tts_media_asset_id", sa.Uuid(), nullable=True),
        sa.Column("background_asset_id", sa.Uuid(), nullable=True),
        sa.Column("composite_scene_asset_id", sa.Uuid(), nullable=True),
        sa.Column("transcript_id", sa.Uuid(), nullable=True),
        sa.Column("presentation", JSONB, nullable=False),
        sa.Column(
            "render_state",
            sa.String(length=32),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "emotion_intensity IS NULL OR emotion_intensity >= 0",
            name=op.f("ck_conversation_turn_presentations_emotion_intensity_nonnegative"),
        ),
        sa.CheckConstraint(
            "emotion_intensity IS NULL OR emotion_intensity <= 2",
            name=op.f("ck_conversation_turn_presentations_emotion_intensity_max"),
        ),
        sa.CheckConstraint(
            "render_state IN ('draft', 'visual_rendered', 'speech_rendered', "
            "'transcribed', 'failed')",
            name=op.f("ck_conversation_turn_presentations_render_state"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_conversation_turn_presentations_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_conversation_turn_presentations_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversation_sessions.id"],
            name=op.f("fk_conversation_turn_presentations_conversation_id_conversation_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["turn_id"],
            ["conversation_turns.id"],
            name=op.f("fk_conversation_turn_presentations_turn_id_conversation_turns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["speaker_agent_id"],
            ["agents.id"],
            name=op.f("fk_conversation_turn_presentations_speaker_agent_id_agents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["sprite_set_id"],
            ["character_sprite_sets.id"],
            name=op.f("fk_conversation_turn_presentations_sprite_set_id_character_sprite_sets"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["sprite_variant_id"],
            ["character_sprite_variants.id"],
            name=op.f(
                "fk_conversation_turn_presentations_sprite_variant_id_character_sprite_variants"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["voice_profile_id"],
            ["voice_profiles.id"],
            name=op.f("fk_conversation_turn_presentations_voice_profile_id_voice_profiles"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tts_media_asset_id"],
            ["media_assets.id"],
            name=op.f("fk_conversation_turn_presentations_tts_media_asset_id_media_assets"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["background_asset_id"],
            ["media_assets.id"],
            name=op.f("fk_conversation_turn_presentations_background_asset_id_media_assets"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["composite_scene_asset_id"],
            ["media_assets.id"],
            name=op.f(
                "fk_conversation_turn_presentations_composite_scene_asset_id_media_assets"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["transcript_id"],
            ["speech_transcripts.id"],
            name=op.f("fk_conversation_turn_presentations_transcript_id_speech_transcripts"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversation_turn_presentations")),
        sa.UniqueConstraint("turn_id", name="uq_conversation_turn_presentations_turn"),
    )
    op.create_index(
        "ix_conversation_turn_presentations_worldline_turn",
        "conversation_turn_presentations",
        ["world_id", "worldline_id", "turn_id"],
    )
    op.create_index(
        "ix_conversation_turn_presentations_conversation",
        "conversation_turn_presentations",
        ["conversation_id"],
    )
    op.create_index(
        "ix_conversation_turn_presentations_speaker",
        "conversation_turn_presentations",
        ["speaker_agent_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversation_turn_presentations_speaker",
        table_name="conversation_turn_presentations",
    )
    op.drop_index(
        "ix_conversation_turn_presentations_conversation",
        table_name="conversation_turn_presentations",
    )
    op.drop_index(
        "ix_conversation_turn_presentations_worldline_turn",
        table_name="conversation_turn_presentations",
    )
    op.drop_table("conversation_turn_presentations")
