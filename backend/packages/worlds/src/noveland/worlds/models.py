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


class WorldBible(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "world_bibles"
    __table_args__ = (
        UniqueConstraint("world_id", name="uq_world_bibles_world_id"),
        Index("ix_world_bibles_world_id", "world_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_material: Mapped[str] = mapped_column(Text, nullable=False, default="")
    canon_timeline: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    setting_rules: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    forbidden_changes: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    sequel_boundaries: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    continuity_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
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
        Index("ix_scenes_world_region", "world_id", "region_key"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    scene_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    region_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    location_tags: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    opening_rules: Mapped[dict[str, Any]] = mapped_column(
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


class WorldOrganization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "world_organizations"
    __table_args__ = (
        UniqueConstraint("world_id", "organization_key", name="uq_world_organizations_world_key"),
        CheckConstraint(
            "organization_type IN ('school', 'club', 'family', 'company', "
            "'faction', 'secret_group', 'other')",
            name="organization_type",
        ),
        Index("ix_world_organizations_world_id", "world_id"),
        Index("ix_world_organizations_world_type", "world_id", "organization_type"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    organization_type: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    hidden_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
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


class OrganizationMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "agent_id",
            name="uq_organization_memberships_organization_agent",
        ),
        CheckConstraint(
            "visibility IN ('public', 'hidden')",
            name="visibility",
        ),
        CheckConstraint("loyalty >= 0 AND loyalty <= 100", name="loyalty_range"),
        CheckConstraint("influence >= 0 AND influence <= 100", name="influence_range"),
        Index("ix_organization_memberships_world_agent", "world_id", "agent_id"),
        Index(
            "ix_organization_memberships_world_organization",
            "world_id",
            "organization_id",
        ),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("world_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, default="public")
    loyalty: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    influence: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    responsibilities: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class FactionProgressTrack(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "faction_progress_tracks"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "track_key",
            name="uq_faction_progress_tracks_organization_key",
        ),
        CheckConstraint(
            "track_type IN ('goal', 'conflict', 'resource', 'reputation', 'risk')",
            name="track_type",
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="progress_range"),
        CheckConstraint("pressure >= 0 AND pressure <= 100", name="pressure_range"),
        Index("ix_faction_progress_tracks_world_organization", "world_id", "organization_id"),
        Index("ix_faction_progress_tracks_world_type", "world_id", "track_type"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("world_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    track_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    track_type: Mapped[str] = mapped_column(String(40), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pressure: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class SceneLocationEdge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scene_location_edges"
    __table_args__ = (
        UniqueConstraint("source_scene_id", "target_scene_id", name="uq_scene_location_edges_pair"),
        CheckConstraint("source_scene_id <> target_scene_id", name="distinct_scenes"),
        Index("ix_scene_location_edges_world_source", "world_id", "source_scene_id"),
        Index("ix_scene_location_edges_world_target", "world_id", "target_scene_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_scene_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_scene_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=False,
    )
    travel_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    traversal_rules: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class AgentPresenceState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_presence_states"
    __table_args__ = (
        UniqueConstraint("world_id", "agent_id", name="uq_agent_presence_states_world_agent"),
        CheckConstraint(
            "visibility_status IN ('visible', 'offscreen', 'hidden', 'unavailable')",
            name="visibility_status",
        ),
        Index("ix_agent_presence_states_world_scene", "world_id", "current_scene_id"),
        Index("ix_agent_presence_states_world_agent", "world_id", "agent_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_scene_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
    )
    visibility_status: Mapped[str] = mapped_column(String(24), nullable=False, default="visible")
    encounter_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    scheduled_movement: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    last_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )


class DailyLifeEventCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_life_event_candidates"
    __table_args__ = (
        CheckConstraint("status IN ('candidate', 'queued', 'dismissed')", name="status"),
        CheckConstraint(
            "importance IN ('daily', 'relationship', 'organization')", name="importance"
        ),
        Index("ix_daily_life_event_candidates_world_status", "world_id", "status"),
        Index("ix_daily_life_event_candidates_world_time", "world_id", "starts_at"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[str] = mapped_column(String(32), nullable=False, default="daily")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(80), nullable=False, default="daily_preview")
    source_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="candidate")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class OffscreenEventQueueItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "offscreen_event_queue"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'resolved', 'cancelled', 'failed')", name="status"),
        CheckConstraint(
            "importance IN ('daily', 'relationship', 'organization', 'route', 'main_plot')",
            name="importance",
        ),
        Index("ix_offscreen_event_queue_world_status_due", "world_id", "status", "due_at"),
        Index("ix_offscreen_event_queue_world_importance", "world_id", "importance"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("daily_life_event_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_name: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(
        "payload",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    importance: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    resolved_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


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
