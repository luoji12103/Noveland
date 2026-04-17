from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NarrativeArtifactKind(StrEnum):
    AGENT_NOTE = "agent_note"
    WORLD_SUMMARY = "world_summary"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class NarrativeArtifactCreate(_FrozenContract):
    world_id: uuid.UUID
    agent_id: uuid.UUID | None = None
    source_run_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1)
    artifact_kind: NarrativeArtifactKind = NarrativeArtifactKind.AGENT_NOTE
    metadata: dict[str, Any] = Field(default_factory=dict)


class NarrativeArtifactRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    agent_id: uuid.UUID | None = None
    source_run_id: uuid.UUID | None = None
    title: str
    content: str
    artifact_kind: NarrativeArtifactKind
    metadata: dict[str, Any]
    created_at: datetime

    @field_validator("created_at", mode="after")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(UTC)
