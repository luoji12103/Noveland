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


class Worldline(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "worldlines"
    __table_args__ = (
        UniqueConstraint("world_id", "worldline_key", name="uq_worldlines_world_key"),
        CheckConstraint("status IN ('active', 'archived')", name="status"),
        CheckConstraint(
            "fork_event_sequence IS NULL OR fork_event_sequence >= 0",
            name="fork_event_sequence_nonnegative",
        ),
        Index("ix_worldlines_world_status", "world_id", "status"),
        Index("ix_worldlines_parent_worldline_id", "parent_worldline_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_worldline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("worldlines.id", ondelete="SET NULL"),
        nullable=True,
    )
    forked_from_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    fork_event_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    created_by_actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)
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
            "worldline_id",
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
        Index(
            "ix_faction_progress_tracks_worldline_organization",
            "world_id",
            "worldline_id",
            "organization_id",
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
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "agent_id",
            name="uq_agent_presence_states_world_agent",
        ),
        CheckConstraint(
            "visibility_status IN ('visible', 'offscreen', 'hidden', 'unavailable')",
            name="visibility_status",
        ),
        Index("ix_agent_presence_states_world_scene", "world_id", "current_scene_id"),
        Index("ix_agent_presence_states_world_agent", "world_id", "agent_id"),
        Index(
            "ix_agent_presence_states_worldline_agent",
            "world_id",
            "worldline_id",
            "agent_id",
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
        Index(
            "ix_daily_life_event_candidates_worldline_status",
            "world_id",
            "worldline_id",
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
        Index(
            "ix_offscreen_event_queue_worldline_status_due",
            "world_id",
            "worldline_id",
            "status",
            "due_at",
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


class GMAgenda(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gm_agendas"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'paused', 'completed', 'archived')", name="status"),
        CheckConstraint("priority >= 0 AND priority <= 100", name="priority_range"),
        Index("ix_gm_agendas_worldline_status", "world_id", "worldline_id", "status"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    focus_agents: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    focus_organizations: Mapped[list[str]] = mapped_column(
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


class GMEventProposal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gm_event_proposals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed', 'accepted', 'rejected', 'resolved')", name="status"
        ),
        CheckConstraint(
            "importance IN ('daily', 'relationship', 'organization', 'route', 'main_plot')",
            name="importance",
        ),
        CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="risk_score_range"),
        Index("ix_gm_event_proposals_worldline_status", "world_id", "worldline_id", "status"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    agenda_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("gm_agendas.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    event_name: Mapped[str] = mapped_column(String(120), nullable=False)
    proposed_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    importance: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    affected_agents: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    affected_organizations: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    source_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="proposed")
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )


class EventResolutionRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "event_resolution_rules"
    __table_args__ = (
        UniqueConstraint("world_id", "rule_key", name="uq_event_resolution_rules_world_key"),
        CheckConstraint("status IN ('active', 'inactive')", name="status"),
        CheckConstraint("priority >= 0 AND priority <= 100", name="priority_range"),
        Index("ix_event_resolution_rules_world_status", "world_id", "status"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    conditions_json: Mapped[dict[str, Any]] = mapped_column(
        "conditions",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    effects_json: Mapped[dict[str, Any]] = mapped_column(
        "effects",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class PlayerActorProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_actor_profiles"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "user_id",
            name="uq_player_actor_profiles_scope_user",
        ),
        Index("ix_player_actor_profiles_worldline", "world_id", "worldline_id"),
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
    actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    current_scene_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
    )
    profile_json: Mapped[dict[str, Any]] = mapped_column(
        "profile",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PlayerChoiceRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_choice_records"
    __table_args__ = (
        CheckConstraint(
            "choice_kind IN ('dialogue', 'travel', 'contact', 'intervention', 'route')",
            name="choice_kind",
        ),
        Index("ix_player_choice_records_worldline_user", "world_id", "worldline_id", "user_id"),
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
    choice_key: Mapped[str] = mapped_column(String(120), nullable=False)
    choice_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    selected_option: Mapped[str] = mapped_column(Text, nullable=False)
    context_json: Mapped[dict[str, Any]] = mapped_column(
        "context",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    consequence_preview: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    applied_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
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
