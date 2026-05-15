from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class NarrativeQualityContextKind(StrEnum):
    AGENT = "agent"
    CONVERSATION = "conversation"
    GM = "gm"
    NARRATIVE = "narrative"
    EVAL = "eval"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class NarrativeQualityEvidenceRef(_FrozenContract):
    kind: str = Field(min_length=1, max_length=120)
    id: str = Field(min_length=1, max_length=200)


class NarrativeQualityContextPreviewRequest(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    context_kind: NarrativeQualityContextKind
    agent_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    limit: int = Field(default=5, ge=1, le=20)

    @model_validator(mode="after")
    def validate_subject(self) -> NarrativeQualityContextPreviewRequest:
        if self.context_kind == NarrativeQualityContextKind.AGENT and self.agent_id is None:
            raise ValueError("agent context requires agent_id")
        if (
            self.context_kind == NarrativeQualityContextKind.CONVERSATION
            and self.conversation_id is None
        ):
            raise ValueError("conversation context requires conversation_id")
        return self


class NarrativeQualityContextPreview(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    context_kind: NarrativeQualityContextKind
    subject_ref: str
    prompt_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[NarrativeQualityEvidenceRef] = Field(default_factory=list)
    generated_at: datetime

    @field_validator("generated_at", mode="after")
    @classmethod
    def normalize_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
