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
    Uuid,
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
        Uuid(as_uuid=True),
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


class StoryHook(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "story_hooks"
    __table_args__ = (
        UniqueConstraint("world_id", "worldline_id", "hook_key", name="uq_story_hooks_scope_key"),
        CheckConstraint(
            "hook_type IN ('promise', 'foreshadowing', 'mystery', 'agreement', 'flag')",
            name="hook_type",
        ),
        CheckConstraint("status IN ('open', 'resolved', 'cancelled')", name="status"),
        CheckConstraint("priority >= 0 AND priority <= 100", name="priority_range"),
        Index("ix_story_hooks_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_story_hooks_worldline_type", "world_id", "worldline_id", "hook_type"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    hook_key: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    hook_type: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    owner_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class PlotThread(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "plot_threads"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "thread_key",
            name="uq_plot_threads_scope_key",
        ),
        CheckConstraint(
            "thread_type IN ('personal', 'organization', 'daily', 'main', 'hidden')",
            name="thread_type",
        ),
        CheckConstraint(
            "status IN ('active', 'dormant', 'completed', 'archived')",
            name="status",
        ),
        CheckConstraint("priority >= 0 AND priority <= 100", name="priority_range"),
        Index("ix_plot_threads_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_plot_threads_worldline_type", "world_id", "worldline_id", "thread_type"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    thread_key: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    thread_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    stakes: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_beats: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    participant_agent_ids: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    organization_ids: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    related_event_ids: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class RouteAffinity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "route_affinities"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "agent_id",
            "route_key",
            name="uq_route_affinities_scope_agent_key",
        ),
        CheckConstraint(
            "status IN ('locked', 'available', 'active', 'completed', 'blocked')",
            name="status",
        ),
        CheckConstraint("affinity >= -100 AND affinity <= 100", name="affinity_range"),
        CheckConstraint("stage >= 0", name="stage_nonnegative"),
        Index("ix_route_affinities_worldline_agent", "world_id", "worldline_id", "agent_id"),
        Index("ix_route_affinities_worldline_status", "world_id", "worldline_id", "status"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    route_key: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="available")
    affinity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    flags: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    last_choice_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("player_choice_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class EventTriggerCondition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "event_trigger_conditions"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "condition_key",
            name="uq_event_trigger_conditions_world_key",
        ),
        CheckConstraint("status IN ('active', 'inactive')", name="status"),
        CheckConstraint("priority >= 0 AND priority <= 100", name="priority_range"),
        Index("ix_event_trigger_conditions_world_status", "world_id", "status"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    condition_key: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    conditions_json: Mapped[dict[str, Any]] = mapped_column(
        "conditions",
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


class SceneBeatDraft(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scene_beat_drafts"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'approved', 'published', 'archived')", name="status"),
        CheckConstraint(
            "source_kind IN ('event', 'proposal', 'daily_episode', 'manual')",
            name="source_kind",
        ),
        Index("ix_scene_beat_drafts_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_scene_beat_drafts_source", "world_id", "source_kind", "source_ref"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    setup: Mapped[str] = mapped_column(Text, nullable=False)
    dialogue_beats: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    choice_points: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    aftermath: Mapped[str] = mapped_column(Text, nullable=False)
    participant_agent_ids: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class DailyEpisodeDraft(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_episode_drafts"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'queued', 'published', 'archived')", name="status"),
        Index("ix_daily_episode_drafts_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_daily_episode_drafts_source_candidate", "source_candidate_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("daily_life_event_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    scene_beat_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scene_beat_drafts.id", ondelete="SET NULL"),
        nullable=True,
    )
    participant_agent_ids: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class GroupInteractionContext(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "group_interaction_contexts"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "context_key",
            name="uq_group_interaction_contexts_scope_key",
        ),
        CheckConstraint(
            "status IN ('planned', 'active', 'completed', 'archived')",
            name="status",
        ),
        CheckConstraint(
            "interaction_type IN ('club', 'class', 'organization_meeting', 'conflict', 'casual')",
            name="interaction_type",
        ),
        Index(
            "ix_group_interaction_contexts_worldline_status",
            "world_id",
            "worldline_id",
            "status",
        ),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    context_key: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    interaction_type: Mapped[str] = mapped_column(String(40), nullable=False)
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    participant_agent_ids: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    participant_roles: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    constraints: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="planned")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class RelationshipEventSuggestion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "relationship_event_suggestions"
    __table_args__ = (
        CheckConstraint("status IN ('suggested', 'accepted', 'dismissed')", name="status"),
        Index(
            "ix_relationship_event_suggestions_worldline_status",
            "world_id",
            "worldline_id",
            "status",
        ),
        Index("ix_relationship_event_suggestions_relationship", "relationship_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_relationship_edges.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_event_name: Mapped[str] = mapped_column(String(120), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="suggested")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class OrganizationConflictEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organization_conflict_events"
    __table_args__ = (
        CheckConstraint("status IN ('proposed', 'resolved', 'dismissed')", name="status"),
        CheckConstraint("pressure_delta >= -100 AND pressure_delta <= 100", name="pressure_delta"),
        CheckConstraint("progress_delta >= -100 AND progress_delta <= 100", name="progress_delta"),
        Index(
            "ix_organization_conflict_events_worldline_status",
            "world_id",
            "worldline_id",
            "status",
        ),
        Index("ix_organization_conflict_events_track", "faction_track_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("world_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    faction_track_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("faction_progress_tracks.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    pressure_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="proposed")
    resolved_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class RumorRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rumor_records"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "rumor_key",
            name="uq_rumor_records_scope_key",
        ),
        CheckConstraint("status IN ('active', 'resolved', 'false', 'archived')", name="status"),
        CheckConstraint(
            "visibility IN ('private', 'group', 'public')",
            name="visibility",
        ),
        Index("ix_rumor_records_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_rumor_records_worldline_visibility", "world_id", "worldline_id", "visibility"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    rumor_key: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    visibility: Mapped[str] = mapped_column(String(24), nullable=False, default="private")
    known_agent_ids: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class RumorPropagation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rumor_propagations"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'delivered', 'blocked')", name="status"),
        Index("ix_rumor_propagations_rumor_status", "rumor_id", "status"),
        Index(
            "ix_rumor_propagations_worldline_target",
            "world_id",
            "worldline_id",
            "target_agent_id",
        ),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    rumor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rumor_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    propagation_reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    delivered_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class CharacterKnowledgeFact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "character_knowledge_facts"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "agent_id",
            "fact_key",
            name="uq_character_knowledge_facts_scope_agent_key",
        ),
        CheckConstraint(
            "knowledge_kind IN ('fact', 'secret', 'guess', 'misbelief')",
            name="knowledge_kind",
        ),
        CheckConstraint(
            "visibility IN ('private', 'shared', 'public')",
            name="visibility",
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 100", name="confidence_range"),
        Index(
            "ix_character_knowledge_facts_worldline_agent",
            "world_id",
            "worldline_id",
            "agent_id",
        ),
        Index(
            "ix_character_knowledge_facts_worldline_kind",
            "world_id",
            "worldline_id",
            "knowledge_kind",
        ),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    knowledge_kind: Mapped[str] = mapped_column(String(24), nullable=False, default="fact")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    visibility: Mapped[str] = mapped_column(String(24), nullable=False, default="private")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class SecretRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "secret_records"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "secret_key",
            name="uq_secret_records_scope_key",
        ),
        CheckConstraint(
            "status IN ('hidden', 'revealed', 'archived')",
            name="status",
        ),
        CheckConstraint(
            "visibility IN ('private', 'holders', 'public')",
            name="visibility",
        ),
        Index("ix_secret_records_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_secret_records_worldline_visibility", "world_id", "worldline_id", "visibility"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    secret_key: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    holder_agent_ids: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    reveal_conditions: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    consequence_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    visibility: Mapped[str] = mapped_column(String(24), nullable=False, default="holders")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="hidden")
    revealed_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class CharacterEmotionalState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "character_emotional_states"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "agent_id",
            name="uq_character_emotional_states_scope_agent",
        ),
        CheckConstraint(
            "stress >= 0 AND stress <= 100",
            name="stress_range",
        ),
        CheckConstraint(
            "fatigue >= 0 AND fatigue <= 100",
            name="fatigue_range",
        ),
        CheckConstraint(
            "anticipation >= 0 AND anticipation <= 100",
            name="anticipation_range",
        ),
        CheckConstraint(
            "jealousy >= 0 AND jealousy <= 100",
            name="jealousy_range",
        ),
        CheckConstraint(
            "anger >= 0 AND anger <= 100",
            name="anger_range",
        ),
        Index(
            "ix_character_emotional_states_worldline_agent",
            "world_id",
            "worldline_id",
            "agent_id",
        ),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    mood: Mapped[str] = mapped_column(String(80), nullable=False, default="neutral")
    stress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fatigue: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    anticipation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    jealousy: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    anger: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class RelationshipRepairRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "relationship_repair_records"
    __table_args__ = (
        CheckConstraint(
            "repair_kind IN "
            "('decay', 'repair', 'conflict', 'apology', 'kept_promise', 'shared_event')",
            name="repair_kind",
        ),
        CheckConstraint(
            "status IN ('proposed', 'applied', 'dismissed')",
            name="status",
        ),
        Index(
            "ix_relationship_repair_records_worldline_status",
            "world_id",
            "worldline_id",
            "status",
        ),
        Index("ix_relationship_repair_records_relationship", "relationship_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_relationship_edges.id", ondelete="CASCADE"),
        nullable=False,
    )
    repair_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    score_delta: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="proposed")
    applied_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class PlayerJournalEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_journal_entries"
    __table_args__ = (
        CheckConstraint(
            "entry_kind IN ('choice', 'relationship', 'event', 'narrative', 'private_note')",
            name="entry_kind",
        ),
        CheckConstraint(
            "visibility IN ('player_private', 'world_admin')",
            name="visibility",
        ),
        Index("ix_player_journal_entries_worldline_user", "world_id", "worldline_id", "user_id"),
        Index("ix_player_journal_entries_source_event", "source_event_id"),
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
    player_actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("player_actor_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    entry_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    visibility: Mapped[str] = mapped_column(String(24), nullable=False, default="player_private")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class InWorldNotification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "in_world_notifications"
    __table_args__ = (
        CheckConstraint(
            "notification_kind IN "
            "('message', 'invitation', 'rumor', 'promise', 'incident', 'intervention')",
            name="notification_kind",
        ),
        CheckConstraint(
            "status IN ('unread', 'read', 'archived')",
            name="status",
        ),
        Index("ix_in_world_notifications_worldline_user", "world_id", "worldline_id", "user_id"),
        Index("ix_in_world_notifications_source_event", "source_event_id"),
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
    notification_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="unread")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class PlayerInterventionRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_intervention_records"
    __table_args__ = (
        CheckConstraint(
            "intervention_kind IN ('observe', 'reply', 'travel', 'contact', 'push_event')",
            name="intervention_kind",
        ),
        CheckConstraint(
            "status IN ('recorded', 'resolved', 'cancelled')",
            name="status",
        ),
        Index(
            "ix_player_intervention_records_worldline_user",
            "world_id",
            "worldline_id",
            "user_id",
        ),
        Index("ix_player_intervention_records_choice", "choice_id"),
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
    intervention_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    target_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_scene_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    choice_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("player_choice_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="recorded")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class GMStyleReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gm_style_reviews"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pass', 'warning', 'fail')",
            name="status",
        ),
        Index("ix_gm_style_reviews_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_gm_style_reviews_source", "world_id", "source_kind", "source_ref"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reviewed_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    diagnostics: Mapped[list[dict[str, Any]]] = mapped_column(
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


class NarrativeContinuityReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "narrative_continuity_reviews"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pass', 'warning', 'fail')",
            name="status",
        ),
        Index(
            "ix_narrative_continuity_reviews_worldline_status",
            "world_id",
            "worldline_id",
            "status",
        ),
        Index("ix_narrative_continuity_reviews_artifact", "artifact_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("narrative_artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reviewed_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(
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


class RouteMilestone(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "route_milestones"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "milestone_key",
            name="uq_route_milestones_scope_key",
        ),
        CheckConstraint(
            "status IN ('planned', 'active', 'completed', 'blocked')",
            name="status",
        ),
        CheckConstraint("stage >= 0", name="stage_nonnegative"),
        Index("ix_route_milestones_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_route_milestones_route_affinity", "route_affinity_id"),
        Index("ix_route_milestones_plot_thread", "plot_thread_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    route_affinity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("route_affinities.id", ondelete="SET NULL"),
        nullable=True,
    )
    plot_thread_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("plot_threads.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    milestone_key: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    stage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="planned")
    conditions: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    evidence_metadata: Mapped[dict[str, Any]] = mapped_column(
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


class EndingCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ending_candidates"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "ending_key",
            name="uq_ending_candidates_scope_key",
        ),
        CheckConstraint(
            "ending_type IN ('normal', 'bad', 'hidden', 'epilogue')",
            name="ending_type",
        ),
        CheckConstraint(
            "status IN ('planned', 'available', 'locked', 'achieved', 'retired')",
            name="status",
        ),
        Index("ix_ending_candidates_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_ending_candidates_worldline_type", "world_id", "worldline_id", "ending_type"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    route_affinity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("route_affinities.id", ondelete="SET NULL"),
        nullable=True,
    )
    plot_thread_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("plot_threads.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    ending_key: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    ending_type: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="planned")
    requirements: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    outcome_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_metadata: Mapped[dict[str, Any]] = mapped_column(
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


class LongRunEvalRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "long_run_eval_runs"
    __table_args__ = (
        CheckConstraint("status IN ('completed', 'warning', 'failed')", name="status"),
        CheckConstraint("horizon_days >= 1 AND horizon_days <= 90", name="horizon_days_range"),
        Index("ix_long_run_eval_runs_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_long_run_eval_runs_worldline_created", "world_id", "worldline_id", "created_at"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    eval_key: Mapped[str] = mapped_column(String(120), nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    recommendations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    blockers: Mapped[list[dict[str, Any]]] = mapped_column(
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


class AuthoringTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "authoring_templates"
    __table_args__ = (
        UniqueConstraint("world_id", "template_key", name="uq_authoring_templates_world_key"),
        CheckConstraint(
            "template_kind IN ('source_notes', 'character', 'event', 'route', 'world_bundle')",
            name="template_kind",
        ),
        Index("ix_authoring_templates_world_kind", "world_id", "template_kind"),
        Index("ix_authoring_templates_world_active", "world_id", "is_active"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_key: Mapped[str] = mapped_column(String(120), nullable=False)
    template_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    validation_issues: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class AuthoringImportJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "authoring_import_jobs"
    __table_args__ = (
        CheckConstraint("status IN ('preview', 'applied', 'failed')", name="status"),
        Index("ix_authoring_import_jobs_world_status", "world_id", "status"),
        Index("ix_authoring_import_jobs_template", "template_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("authoring_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    preview_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    applied_refs: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    validation_issues: Mapped[list[dict[str, Any]]] = mapped_column(
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


class LivingWorldReleaseProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "living_world_release_profiles"
    __table_args__ = (
        UniqueConstraint("world_id", name="uq_living_world_release_profiles_world_id"),
        CheckConstraint("status IN ('draft', 'ready', 'blocked', 'released')", name="status"),
        Index("ix_living_world_release_profiles_status", "status"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile_key: Mapped[str] = mapped_column(String(120), nullable=False, default="default")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    branch_policy: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    backup_policy: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    content_review_policy: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    player_permission_policy: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    worldline_policy: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    checklist: Mapped[dict[str, Any]] = mapped_column(
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


class BetaChecklistRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "beta_checklist_runs"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'passed', 'warning', 'blocked')", name="status"),
        CheckConstraint("blocker_count >= 0", name="blocker_count_nonnegative"),
        Index("ix_beta_checklist_runs_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_beta_checklist_runs_worldline_created", "world_id", "worldline_id", "created_at"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_key: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    blocker_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by_actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class BetaChecklistItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "beta_checklist_items"
    __table_args__ = (
        UniqueConstraint("run_id", "item_key", name="uq_beta_checklist_items_run_key"),
        CheckConstraint("status IN ('pending', 'passed', 'warning', 'blocked')", name="status"),
        Index("ix_beta_checklist_items_run_status", "run_id", "status"),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("beta_checklist_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_key: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)


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
