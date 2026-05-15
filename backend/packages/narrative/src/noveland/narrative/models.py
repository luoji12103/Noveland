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


class NarrativeArtifact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "narrative_artifacts"
    __table_args__ = (
        CheckConstraint(
            "artifact_kind IN ("
            "'agent_note', "
            "'world_summary', "
            "'conversation_summary', "
            "'chapter_draft'"
            ")",
            name="artifact_kind",
        ),
        Index("ix_narrative_artifacts_world_created_at", "world_id", "created_at"),
        Index(
            "ix_narrative_artifacts_worldline_created_at",
            "world_id",
            "worldline_id",
            "created_at",
        ),
        Index("ix_narrative_artifacts_world_agent", "world_id", "agent_id"),
        Index(
            "ix_narrative_artifacts_world_conversation_created_at",
            "world_id",
            "source_conversation_id",
            "created_at",
        ),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("worldlines.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runtime_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversation_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    artifact_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class NarrativePublication(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "narrative_publications"
    __table_args__ = (
        UniqueConstraint("artifact_id", name="uq_narrative_publications_artifact_id"),
        CheckConstraint(
            "status IN ('published', 'unpublished')",
            name="status",
        ),
        Index(
            "ix_narrative_publications_world_status_visible",
            "world_id",
            "status",
            "reader_visible",
        ),
        Index(
            "ix_narrative_publications_worldline_status_visible",
            "world_id",
            "worldline_id",
            "status",
            "reader_visible",
        ),
        Index("ix_narrative_publications_world_published_at", "world_id", "published_at"),
        Index("ix_narrative_publications_source_draft", "source_draft_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("worldlines.id", ondelete="SET NULL"),
        nullable=True,
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("narrative_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("narrative_artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'published'"),
        default="published",
    )
    reader_visible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        default=True,
    )
    published_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unpublished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
