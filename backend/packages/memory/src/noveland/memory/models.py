from __future__ import annotations

import uuid
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from noveland.memory.vector_type import EmbeddingVector
from sqlalchemy import JSON, Boolean, CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class AgentMemoryItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_memory_items"
    __table_args__ = (
        CheckConstraint("visibility = 'private'", name="visibility"),
        Index("ix_agent_memory_items_world_agent", "world_id", "agent_id"),
        Index("ix_agent_memory_items_world_agent_active", "world_id", "agent_id", "is_active"),
        Index("ix_agent_memory_items_source_event_id", "source_event_id"),
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
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
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
