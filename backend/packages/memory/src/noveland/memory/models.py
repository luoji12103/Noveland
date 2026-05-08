from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from noveland.memory.vector_type import EmbeddingVector
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


def _json_column() -> JSONB | JSON:
    return JSONB().with_variant(JSON(), "sqlite")


class MemoryBackendProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "memory_backend_profiles"
    __table_args__ = (
        UniqueConstraint("profile_key", name="uq_memory_backend_profiles_profile_key"),
        CheckConstraint(
            "backend_kind IN ('mem0_oss', 'local_pgvector')",
            name="backend_kind",
        ),
    )

    profile_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    backend_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    vector_store_config: Mapped[dict[str, Any]] = mapped_column(
        _json_column(),
        nullable=False,
        default=dict,
    )
    llm_config: Mapped[dict[str, Any]] = mapped_column(
        _json_column(),
        nullable=False,
        default=dict,
    )
    embedder_config: Mapped[dict[str, Any]] = mapped_column(
        _json_column(),
        nullable=False,
        default=dict,
    )
    reranker_config: Mapped[dict[str, Any]] = mapped_column(
        _json_column(),
        nullable=False,
        default=dict,
    )
    secret_refs: Mapped[dict[str, str]] = mapped_column(
        _json_column(),
        nullable=False,
        default=dict,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        default=True,
    )


class AgentMemoryItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_memory_items"
    __table_args__ = (
        CheckConstraint("visibility = 'private'", name="visibility"),
        Index("ix_agent_memory_items_world_agent", "world_id", "agent_id"),
        Index("ix_agent_memory_items_worldline_agent", "world_id", "worldline_id", "agent_id"),
        Index("ix_agent_memory_items_world_agent_active", "world_id", "agent_id", "is_active"),
        Index(
            "ix_agent_memory_items_worldline_agent_active",
            "world_id",
            "worldline_id",
            "agent_id",
            "is_active",
        ),
        Index("ix_agent_memory_items_source_event_id", "source_event_id"),
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
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        _json_column(),
        nullable=False,
        default=dict,
    )
    embedding: Mapped[list[float]] = mapped_column(EmbeddingVector(), nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'private'"),
        default="private",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        default=True,
    )


class MemoryWriteJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "memory_write_jobs"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_memory_write_jobs_dedupe_key"),
        CheckConstraint(
            "source_kind IN ('agent_run', 'conversation_turn', 'world_event')",
            name="source_kind",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'succeeded', 'failed')",
            name="status",
        ),
        CheckConstraint("attempt_count >= 0", name="attempt_count_non_negative"),
        Index("ix_memory_write_jobs_status_next_attempt_at", "status", "next_attempt_at"),
        Index("ix_memory_write_jobs_world_agent", "world_id", "agent_id"),
        Index("ix_memory_write_jobs_worldline_agent", "world_id", "worldline_id", "agent_id"),
        Index("ix_memory_write_jobs_backend_profile_id", "backend_profile_id"),
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
    backend_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("memory_backend_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(
        _json_column(),
        nullable=False,
        default=dict,
    )
    dedupe_key: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'pending'"),
        default="pending",
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        default=0,
    )
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MemoryWriteLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "memory_write_logs"
    __table_args__ = (
        Index("ix_memory_write_logs_job_id", "job_id"),
        Index("ix_memory_write_logs_occurred_at", "occurred_at"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("memory_write_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    backend: Mapped[str] = mapped_column(String(120), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_summary: Mapped[dict[str, Any]] = mapped_column(
        _json_column(),
        nullable=False,
        default=dict,
    )
    response_summary: Mapped[dict[str, Any]] = mapped_column(
        _json_column(),
        nullable=False,
        default=dict,
    )
    correlation_ids: Mapped[dict[str, Any]] = mapped_column(
        _json_column(),
        nullable=False,
        default=dict,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class MemoryRetrievalLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "memory_retrieval_logs"
    __table_args__ = (
        Index("ix_memory_retrieval_logs_world_agent", "world_id", "agent_id"),
        Index("ix_memory_retrieval_logs_worldline_agent", "world_id", "worldline_id", "agent_id"),
        Index("ix_memory_retrieval_logs_occurred_at", "occurred_at"),
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
    backend_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("memory_backend_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    backend: Mapped[str] = mapped_column(String(120), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    selected_item_ids: Mapped[list[str]] = mapped_column(
        _json_column(),
        nullable=False,
        default=list,
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    context_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class AgentProfileSnapshotModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_profile_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "agent_id",
            name="uq_agent_profile_snapshots_worldline_agent",
        ),
        Index(
            "ix_agent_profile_snapshots_worldline_agent",
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
    aliases: Mapped[list[str]] = mapped_column(_json_column(), nullable=False, default=list)
    identity_notes: Mapped[list[str]] = mapped_column(
        _json_column(),
        nullable=False,
        default=list,
    )
    durable_preferences: Mapped[list[str]] = mapped_column(
        _json_column(),
        nullable=False,
        default=list,
    )
    long_lived_goals: Mapped[list[str]] = mapped_column(
        _json_column(),
        nullable=False,
        default=list,
    )
    language_style_preferences: Mapped[list[str]] = mapped_column(
        _json_column(),
        nullable=False,
        default=list,
    )
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
