from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class AgentCalendarEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_calendar_entries"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'cancelled')", name="status"),
        CheckConstraint("ends_at IS NULL OR ends_at >= starts_at", name="ends_after_starts"),
        Index("ix_agent_calendar_entries_world_agent_starts", "world_id", "agent_id", "starts_at"),
        Index("ix_agent_calendar_entries_world_agent_status", "world_id", "agent_id", "status"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recurrence_rule: Mapped[str | None] = mapped_column(String(240), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'active'"),
        default="active",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class WorldScheduleRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "world_schedule_rules"
    __table_args__ = (
        UniqueConstraint("world_id", "rule_key", name="uq_world_schedule_rules_world_rule_key"),
        CheckConstraint("kind IN ('weekday', 'weekend', 'timetable')", name="kind"),
        Index("ix_world_schedule_rules_world_id", "world_id"),
        Index("ix_world_schedule_rules_world_enabled", "world_id", "is_enabled"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        default=True,
    )
