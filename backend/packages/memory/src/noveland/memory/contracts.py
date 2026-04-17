from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Protocol

from noveland.memory.vector_type import VECTOR_DIMENSIONS
from pydantic import BaseModel, ConfigDict, Field, field_validator


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class MemoryItemCreate(_FrozenContract):
    world_id: uuid.UUID
    agent_id: uuid.UUID
    content: str = Field(min_length=1)
    embedding: list[float]
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_event_id: uuid.UUID | None = None

    @field_validator("embedding", mode="after")
    @classmethod
    def validate_embedding(cls, value: list[float]) -> list[float]:
        if len(value) != VECTOR_DIMENSIONS:
            raise ValueError(f"embedding must have {VECTOR_DIMENSIONS} dimensions")
        return [float(item) for item in value]


class MemorySearchQuery(_FrozenContract):
    world_id: uuid.UUID
    agent_id: uuid.UUID
    embedding: list[float]
    limit: int = Field(default=10, ge=1, le=50)

    @field_validator("embedding", mode="after")
    @classmethod
    def validate_embedding(cls, value: list[float]) -> list[float]:
        if len(value) != VECTOR_DIMENSIONS:
            raise ValueError(f"embedding must have {VECTOR_DIMENSIONS} dimensions")
        return [float(item) for item in value]


class MemoryItemRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    agent_id: uuid.UUID
    content: str
    metadata: dict[str, Any]
    embedding: list[float]
    visibility: str
    is_active: bool
    source_event_id: uuid.UUID | None = None
    score: float | None = None


class MemoryBackend(Protocol):
    def add(self, item: MemoryItemCreate) -> MemoryItemRecord:
        """Store one memory item."""

    def list(self, world_id: uuid.UUID, agent_id: uuid.UUID) -> Sequence[MemoryItemRecord]:
        """List active memory items for one agent."""

    def search(self, query: MemorySearchQuery) -> Sequence[MemoryItemRecord]:
        """Search memory items for one agent."""

    def disable(self, memory_id: uuid.UUID) -> None:
        """Soft-disable one memory item."""
