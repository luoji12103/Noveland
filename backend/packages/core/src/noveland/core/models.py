from __future__ import annotations

from datetime import datetime
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import CheckConstraint, DateTime, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class PlatformSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "platform_settings"
    __table_args__ = (UniqueConstraint("key", name="uq_platform_settings_key"),)

    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class RuntimeControlState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "runtime_control_states"
    __table_args__ = (
        UniqueConstraint("control_key", name="uq_runtime_control_states_control_key"),
        CheckConstraint(
            "desired_state IN ('running', 'stopped')",
            name="desired_state",
        ),
    )

    control_key: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'default'"),
        default="default",
    )
    desired_state: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'stopped'"),
        default="stopped",
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_run_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_run_finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
