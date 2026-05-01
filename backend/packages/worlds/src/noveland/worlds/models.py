from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from noveland.plugins.constants import (
    BUILTIN_DEFAULT_WORLD_RULES,
    BUILTIN_LOCAL_PGVECTOR_MEMORY,
)
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class World(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "worlds"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_worlds_slug"),
        Index("ix_worlds_owner_user_id", "owner_user_id"),
    )

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rules_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    memory_backend_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("memory_backend_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    memory_plugin_identifier: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default=BUILTIN_LOCAL_PGVECTOR_MEMORY,
    )
    memory_plugin_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    world_rules_plugin_identifier: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default=BUILTIN_DEFAULT_WORLD_RULES,
    )
    world_rules_plugin_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        default=True,
    )


class WorldMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "world_memberships"
    __table_args__ = (
        UniqueConstraint("world_id", "user_id", name="uq_world_memberships_world_user"),
        CheckConstraint(
            "role IN ('world_admin', 'human_user')",
            name="role",
        ),
        Index("ix_world_memberships_world_id", "world_id"),
        Index("ix_world_memberships_user_id", "user_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)


class Scene(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scenes"
    __table_args__ = (
        UniqueConstraint("world_id", "scene_key", name="uq_scenes_world_scene_key"),
        Index("ix_scenes_world_id", "world_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    scene_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        default=True,
    )


class WorldClockStateModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "world_clock_states"
    __table_args__ = (
        UniqueConstraint("world_id", name="uq_world_clock_states_world_id"),
        CheckConstraint("status IN ('running', 'paused')", name="status"),
        CheckConstraint("speed_multiplier > 0", name="speed_multiplier_positive"),
        CheckConstraint("revision >= 0", name="revision_nonnegative"),
        CheckConstraint(
            "(status = 'paused' AND wall_time_anchor IS NULL) OR "
            "(status = 'running' AND wall_time_anchor IS NOT NULL)",
            name="wall_time_anchor_matches_status",
        ),
        Index("ix_world_clock_states_world_id", "world_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    current_world_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    wall_time_anchor: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    speed_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(12, 6),
        nullable=False,
        server_default=text("1.000000"),
    )
    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        default=0,
    )


class WorldClockTransitionModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "world_clock_transitions"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "new_revision",
            name="uq_world_clock_transitions_world_revision",
        ),
        CheckConstraint(
            "transition_type IN ('initialize', 'pause', 'resume', 'advance', 'skip')",
            name="transition_type",
        ),
        CheckConstraint(
            "previous_status IS NULL OR previous_status IN ('running', 'paused')",
            name="previous_status",
        ),
        CheckConstraint("new_status IN ('running', 'paused')", name="new_status"),
        CheckConstraint(
            "previous_revision IS NULL OR previous_revision >= 0",
            name="previous_revision_nonnegative",
        ),
        CheckConstraint("new_revision >= 0", name="new_revision_nonnegative"),
        Index("ix_world_clock_transitions_world_id", "world_id"),
        Index("ix_world_clock_transitions_world_wall_time", "world_id", "wall_time"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    transition_type: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    new_status: Mapped[str] = mapped_column(String(16), nullable=False)
    previous_world_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    new_world_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    wall_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
