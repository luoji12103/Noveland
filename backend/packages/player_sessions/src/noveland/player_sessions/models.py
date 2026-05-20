from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


def _json_column() -> JSONB | JSON:
    return JSONB().with_variant(JSON(), "sqlite")


PLAYER_SESSION_STATUS_CHECK = "'active', 'paused', 'closed'"
PLAYER_RECOVERY_STATUS_CHECK = (
    "'ready', 'stale_conversation', 'missing_media', 'provider_failure', "
    "'media_failure', 'presentation_unavailable'"
)


class PlayerSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_sessions"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "user_id",
            "player_actor_id",
            name="uq_player_sessions_scope_user_actor",
        ),
        CheckConstraint(
            f"status IN ({PLAYER_SESSION_STATUS_CHECK})",
            name="status",
        ),
        CheckConstraint(
            f"recovery_status IN ({PLAYER_RECOVERY_STATUS_CHECK})",
            name="recovery_status",
        ),
        Index("ix_player_sessions_worldline_user", "world_id", "worldline_id", "user_id"),
        Index("ix_player_sessions_conversation", "conversation_session_id"),
        Index("ix_player_sessions_last_seen", "world_id", "last_seen_at"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_actor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("player_actor_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversation_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_turn_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversation_turns.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_presentation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversation_turn_presentations.id", ondelete="SET NULL"),
        nullable=True,
    )
    route_state_json: Mapped[dict[str, Any]] = mapped_column(
        "route_state",
        _json_column(),
        nullable=False,
        default=dict,
    )
    resume_state_json: Mapped[dict[str, Any]] = mapped_column(
        "resume_state",
        _json_column(),
        nullable=False,
        default=dict,
    )
    recovery_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="ready",
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="active",
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
