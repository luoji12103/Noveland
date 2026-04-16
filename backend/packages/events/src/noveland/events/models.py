from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class WorldEventModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "world_events"
    __table_args__ = (
        UniqueConstraint("world_id", "sequence", name="uq_world_events_world_sequence"),
        CheckConstraint("sequence > 0", name="sequence_positive"),
        CheckConstraint(
            "event_name ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$'",
            name="event_name_format",
        ),
        Index("ix_world_events_world_sequence", "world_id", "sequence"),
        Index("ix_world_events_world_event_name", "world_id", "event_name"),
        Index("ix_world_events_world_wall_time", "world_id", "wall_time"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_name: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    wall_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    world_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    causation_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="RESTRICT"),
        nullable=True,
    )
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)


class WorldSnapshotModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "world_snapshots"
    __table_args__ = (
        CheckConstraint("covers_event_sequence >= 0", name="covers_event_sequence_nonnegative"),
        CheckConstraint("status IN ('valid', 'invalid')", name="status"),
        CheckConstraint("payload IS NOT NULL OR payload_uri IS NOT NULL", name="payload_or_uri"),
        Index("ix_world_snapshots_world_sequence", "world_id", "covers_event_sequence"),
        Index(
            "ix_world_snapshots_world_latest_valid",
            "world_id",
            "status",
            "covers_event_sequence",
        ),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    covers_event_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'valid'"),
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    payload_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    snapshot_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_by_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("world_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
