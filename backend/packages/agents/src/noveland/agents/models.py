from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from noveland.plugins.constants import BUILTIN_DEFAULT_PERSONA_POLICY
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class Agent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("world_id", "agent_key", name="uq_agents_world_agent_key"),
        CheckConstraint(
            "kind IN ('role_agent', 'narrative_agent')",
            name="kind",
        ),
        CheckConstraint(
            "narrative_role IS NULL OR narrative_role IN ("
            "'protagonist', 'main_character', 'side_character', "
            "'supporting_cast', 'ordinary_member', 'organization_member', "
            "'original_character', 'narrative_agent'"
            ")",
            name="narrative_role",
        ),
        CheckConstraint(
            "importance IS NULL OR importance IN ('lead', 'major', 'minor', 'background')",
            name="importance",
        ),
        CheckConstraint(
            "canon_status IS NULL OR canon_status IN ("
            "'canon', 'post_canon', 'alternate', 'original_expansion'"
            ")",
            name="canon_status",
        ),
        CheckConstraint(
            "character_category IS NULL OR character_category IN ("
            "'player', 'main_character', 'side_character', 'ordinary_member', "
            "'organization_member', 'original_character', 'narrative_agent'"
            ")",
            name="character_category",
        ),
        Index("ix_agents_world_id", "world_id"),
        Index("ix_agents_home_scene_id", "home_scene_id"),
        Index("ix_agents_source_preset_id", "source_preset_id"),
        Index("ix_agents_world_canon_status", "world_id", "canon_status"),
        Index("ix_agents_world_character_category", "world_id", "character_category"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    home_scene_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_preset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_presets.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_preset_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agent_key: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    narrative_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    importance: Mapped[str | None] = mapped_column(String(40), nullable=True)
    canon_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    character_category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    character_profile: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
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


class AgentRelationshipEdge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_relationship_edges"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "source_agent_id",
            "target_agent_id",
            "relationship_type",
            name="uq_agent_relationship_edges_source_target_type",
        ),
        CheckConstraint("source_agent_id <> target_agent_id", name="distinct_agents"),
        CheckConstraint(
            "relationship_type IN ('affection', 'friendship', 'rivalry', 'family', "
            "'alliance', 'hostility', 'obligation', 'debt', 'secret', 'custom')",
            name="relationship_type",
        ),
        CheckConstraint("affection >= -100 AND affection <= 100", name="affection_range"),
        CheckConstraint("trust >= -100 AND trust <= 100", name="trust_range"),
        CheckConstraint("hostility >= 0 AND hostility <= 100", name="hostility_range"),
        CheckConstraint("intimacy >= 0 AND intimacy <= 100", name="intimacy_range"),
        CheckConstraint("obligation >= 0 AND obligation <= 100", name="obligation_range"),
        CheckConstraint("rivalry >= 0 AND rivalry <= 100", name="rivalry_range"),
        CheckConstraint("debt >= 0 AND debt <= 100", name="debt_range"),
        Index("ix_agent_relationship_edges_world_source", "world_id", "source_agent_id"),
        Index("ix_agent_relationship_edges_world_target", "world_id", "target_agent_id"),
        Index(
            "ix_agent_relationship_edges_worldline_source",
            "world_id",
            "worldline_id",
            "source_agent_id",
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
    source_agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(String(40), nullable=False)
    affection: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trust: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hostility: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    intimacy: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    obligation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rivalry: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    debt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class AgentPreset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_presets"
    __table_args__ = (
        UniqueConstraint("preset_key", name="uq_agent_presets_preset_key"),
        CheckConstraint(
            "default_kind IN ('role_agent', 'narrative_agent')",
            name="default_kind",
        ),
        Index("ix_agent_presets_is_active", "is_active"),
    )

    preset_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    default_provider_profile_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    persona_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    behavior_policy: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    calendar_blueprint_json: Mapped[list[dict[str, Any]]] = mapped_column(
        "calendar_blueprint",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    advanced_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
        default=1,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        default=True,
    )


class AgentRuntimeRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_runtime_runs"
    __table_args__ = (
        CheckConstraint("status IN ('running', 'succeeded', 'failed')", name="status"),
        CheckConstraint(
            "trigger_source IN ('manual', 'calendar_entry', 'schedule_rule', 'runtime_tick')",
            name="trigger_source",
        ),
        Index("ix_agent_runtime_runs_world_agent_started_at", "world_id", "agent_id", "started_at"),
        Index(
            "ix_agent_runtime_runs_worldline_agent_started_at",
            "world_id",
            "worldline_id",
            "agent_id",
            "started_at",
        ),
        Index("ix_agent_runtime_runs_provider_profile_id", "provider_profile_id"),
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
    provider_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("provider_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_calendar_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_calendar_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_schedule_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_schedule_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    trigger_source: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnostics: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentPersona(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_personas"
    __table_args__ = (
        UniqueConstraint("agent_id", name="uq_agent_personas_agent_id"),
        Index("ix_agent_personas_world_agent", "world_id", "agent_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    persona_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    behavior_policy: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    policy_plugin_identifier: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default=BUILTIN_DEFAULT_PERSONA_POLICY,
    )
    policy_plugin_config: Mapped[dict[str, Any]] = mapped_column(
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


class AgentObservation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_observations"
    __table_args__ = (
        CheckConstraint("observation_type <> ''", name="observation_type_present"),
        CheckConstraint(
            "review_status IN ('unreviewed', 'approved', 'rejected')",
            name="review_status",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="confidence_score_range",
        ),
        CheckConstraint("runtime_use_count >= 0", name="runtime_use_count_non_negative"),
        Index("ix_agent_observations_world_agent_observed", "world_id", "agent_id", "observed_at"),
        Index("ix_agent_observations_source_event_id", "source_event_id"),
        Index("ix_agent_observations_world_agent_review", "world_id", "agent_id", "review_status"),
        Index("ix_agent_observations_last_used_run_id", "last_used_run_id"),
        Index(
            "uq_agent_observations_agent_source_event",
            "agent_id",
            "source_event_id",
            unique=True,
            postgresql_where=text("source_event_id IS NOT NULL"),
            sqlite_where=text("source_event_id IS NOT NULL"),
        ),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    observation_type: Mapped[str] = mapped_column(String(80), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'unreviewed'"),
        default="unreviewed",
    )
    runtime_use_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        default=0,
    )
    last_used_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runtime_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
