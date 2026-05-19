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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


def _json_column() -> JSONB | JSON:
    return JSONB().with_variant(JSON(), "sqlite")


PRIVATE_BETA_INVITE_STATUS_CHECK = (
    "'pending', 'accepted', 'waitlisted', 'redeemed', 'expired', 'revoked'"
)
PRIVATE_BETA_WORLD_ROLE_CHECK = "'human_user'"
PRIVATE_BETA_ROLE_CHECK = "'tester', 'player_tester'"


class PrivateBetaInvite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "private_beta_invites"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_private_beta_invites_token_hash"),
        CheckConstraint(
            f"status IN ({PRIVATE_BETA_INVITE_STATUS_CHECK})",
            name="status",
        ),
        CheckConstraint(
            f"intended_world_role IN ({PRIVATE_BETA_WORLD_ROLE_CHECK})",
            name="intended_world_role",
        ),
        CheckConstraint(
            f"beta_role IN ({PRIVATE_BETA_ROLE_CHECK})",
            name="beta_role",
        ),
        CheckConstraint("length(token_hash) = 64", name="token_hash_length"),
        Index("ix_private_beta_invites_world_status", "world_id", "status"),
        Index("ix_private_beta_invites_worldline", "world_id", "worldline_id"),
        Index("ix_private_beta_invites_invited_user", "invited_user_id"),
        Index("ix_private_beta_invites_invited_email", "invited_email"),
        Index("ix_private_beta_invites_redeemed_user", "redeemed_by_user_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=True,
    )
    invited_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    invited_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    intended_world_role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="human_user",
    )
    beta_role: Mapped[str] = mapped_column(String(32), nullable=False, default="tester")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    redeemed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_actor_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_actor_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        _json_column(),
        nullable=False,
        default=dict,
    )
