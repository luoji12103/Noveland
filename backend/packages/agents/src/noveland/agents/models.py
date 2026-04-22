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


class Agent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("world_id", "agent_key", name="uq_agents_world_agent_key"),
        CheckConstraint(
            "kind IN ('role_agent', 'narrative_agent')",
            name="kind",
        ),
        Index("ix_agents_world_id", "world_id"),
        Index("ix_agents_home_scene_id", "home_scene_id"),
        Index("ix_agents_source_preset_id", "source_preset_id"),
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
    agent_key: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
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
        Index("ix_agent_runtime_runs_provider_profile_id", "provider_profile_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
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
        Index("ix_agent_observations_world_agent_observed", "world_id", "agent_id", "observed_at"),
        Index("ix_agent_observations_source_event_id", "source_event_id"),
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
