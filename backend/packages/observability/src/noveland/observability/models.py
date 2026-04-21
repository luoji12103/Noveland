from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class RuntimeDiagnosticEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "runtime_diagnostic_events"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('info', 'warning', 'error')",
            name="severity",
        ),
        CheckConstraint(
            "component IN ("
            "'runtime', "
            "'provider', "
            "'agent', "
            "'conversation', "
            "'event_publisher', "
            "'api'"
            ")",
            name="component",
        ),
        Index("ix_runtime_diagnostic_events_occurred_at", "occurred_at"),
        Index("ix_runtime_diagnostic_events_severity_component", "severity", "component"),
        Index("ix_runtime_diagnostic_events_world_occurred_at", "world_id", "occurred_at"),
        Index("ix_runtime_diagnostic_events_agent_occurred_at", "agent_id", "occurred_at"),
        Index("ix_runtime_diagnostic_events_run_id", "run_id"),
        Index("ix_runtime_diagnostic_events_provider_profile_id", "provider_profile_id"),
    )

    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    component: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    world_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=True,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runtime_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("provider_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
