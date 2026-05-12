from __future__ import annotations

import uuid

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class ConversationSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "conversation_sessions"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "session_key",
            name="uq_conversation_sessions_world_session_key",
        ),
        CheckConstraint("scope_type IN ('scene', 'world')", name="scope_type"),
        CheckConstraint("mode IN ('manual_chain', 'auto_dialogue')", name="mode"),
        CheckConstraint(
            "status IN ('draft', 'running', 'paused', 'completed', 'stopped', 'failed')",
            name="status",
        ),
        CheckConstraint("max_turns > 0", name="max_turns_positive"),
        CheckConstraint("next_turn_index >= 0", name="next_turn_index_non_negative"),
        CheckConstraint(
            "terminal_reason IN ("
            "'max_turns_reached', "
            "'loop_guard_repeated_output', "
            "'no_enabled_participants', "
            "'consecutive_failures_exceeded', "
            "'operator_stopped', "
            "'speaker_error'"
            ") OR terminal_reason IS NULL",
            name="terminal_reason",
        ),
        CheckConstraint(
            "(scope_type = 'scene' AND scene_id IS NOT NULL) OR "
            "(scope_type = 'world' AND scene_id IS NULL)",
            name="scene_scope_consistency",
        ),
        Index("ix_conversation_sessions_world_id", "world_id"),
        Index("ix_conversation_sessions_scene_id", "scene_id"),
        Index(
            "ix_conversation_sessions_world_mode_status",
            "world_id",
            "mode",
            "status",
        ),
        Index(
            "ix_conversation_sessions_worldline_mode_status",
            "world_id",
            "worldline_id",
            "mode",
            "status",
        ),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=True,
    )
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=True,
    )
    session_key: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(16), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False, default="")
    opening_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    max_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    next_turn_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    policy_config: Mapped[dict[str, object]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    writer_config: Mapped[dict[str, object]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    memory_config: Mapped[dict[str, object]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    terminal_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ConversationParticipant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "agent_id",
            name="uq_conversation_participants_session_agent",
        ),
        UniqueConstraint(
            "session_id",
            "turn_order",
            name="uq_conversation_participants_session_turn_order",
        ),
        CheckConstraint("turn_order >= 0", name="turn_order_non_negative"),
        Index("ix_conversation_participants_session_id", "session_id"),
        Index("ix_conversation_participants_agent_id", "agent_id"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )


class ConversationTurn(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "conversation_turns"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "turn_index",
            name="uq_conversation_turns_session_turn_index",
        ),
        CheckConstraint("speaker_kind IN ('operator', 'agent')", name="speaker_kind"),
        CheckConstraint("status IN ('succeeded', 'skipped', 'failed')", name="status"),
        Index("ix_conversation_turns_session_id", "session_id"),
        Index("ix_conversation_turns_speaker_agent_id", "speaker_agent_id"),
        Index("ix_conversation_turns_run_id", "run_id"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    speaker_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runtime_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)


class ConversationTurnPresentation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "conversation_turn_presentations"
    __table_args__ = (
        UniqueConstraint("turn_id", name="uq_conversation_turn_presentations_turn"),
        CheckConstraint(
            "emotion_intensity IS NULL OR emotion_intensity >= 0",
            name="emotion_intensity_nonnegative",
        ),
        CheckConstraint(
            "emotion_intensity IS NULL OR emotion_intensity <= 2",
            name="emotion_intensity_max",
        ),
        CheckConstraint(
            "render_state IN ("
            "'draft', 'visual_rendered', 'speech_rendered', 'transcribed', 'failed'"
            ")",
            name="render_state",
        ),
        Index(
            "ix_conversation_turn_presentations_worldline_turn",
            "world_id",
            "worldline_id",
            "turn_id",
        ),
        Index(
            "ix_conversation_turn_presentations_conversation",
            "conversation_id",
        ),
        Index(
            "ix_conversation_turn_presentations_speaker",
            "speaker_agent_id",
        ),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversation_turns.id", ondelete="CASCADE"),
        nullable=False,
    )
    speaker_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    emotion_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    emotion_intensity: Mapped[float | None] = mapped_column(Float, nullable=True)
    sprite_set_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("character_sprite_sets.id", ondelete="SET NULL"),
        nullable=True,
    )
    sprite_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("character_sprite_variants.id", ondelete="SET NULL"),
        nullable=True,
    )
    voice_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("voice_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    tts_media_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    background_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    composite_scene_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    transcript_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("speech_transcripts.id", ondelete="SET NULL"),
        nullable=True,
    )
    presentation_json: Mapped[dict[str, object]] = mapped_column(
        "presentation",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    render_state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'draft'"),
        default="draft",
    )
