from __future__ import annotations

import uuid
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, Text
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
