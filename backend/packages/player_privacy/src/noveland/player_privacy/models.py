from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class PlayerPrivacyRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_privacy_requests"
    __table_args__ = (
        CheckConstraint(
            "request_kind IN ('export', 'delete')",
            name="request_kind",
        ),
        CheckConstraint(
            "status IN ("
            "'requested', "
            "'under_review', "
            "'approved_for_redaction', "
            "'rejected', "
            "'completed'"
            ")",
            name="status",
        ),
        Index(
            "ix_player_privacy_requests_worldline_user",
            "world_id",
            "worldline_id",
            "user_id",
        ),
        Index("ix_player_privacy_requests_status", "world_id", "status"),
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
    request_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="requested")
    target_ref_kind: Mapped[str | None] = mapped_column(String(80), nullable=True)
    target_ref_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_json: Mapped[dict[str, Any]] = mapped_column(
        "summary",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    redaction_plan_json: Mapped[dict[str, Any]] = mapped_column(
        "redaction_plan",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    created_by_actor_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    reviewed_by_actor_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
