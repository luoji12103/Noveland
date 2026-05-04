from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NarrativeArtifactKind(StrEnum):
    AGENT_NOTE = "agent_note"
    WORLD_SUMMARY = "world_summary"
    CONVERSATION_SUMMARY = "conversation_summary"
    CHAPTER_DRAFT = "chapter_draft"


class NarrativePublicationStatus(StrEnum):
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"


class NarrativeGenerationMode(StrEnum):
    MANUAL = "manual"
    AUTO_ON_COMPLETE = "auto_on_complete"


class ConversationNarrativeArtifactSet(StrEnum):
    SUMMARY_AND_CHAPTER = "summary_and_chapter"
    SUMMARY_ONLY = "summary_only"
    CHAPTER_ONLY = "chapter_only"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class NarrativeArtifactCreate(_FrozenContract):
    world_id: uuid.UUID
    agent_id: uuid.UUID | None = None
    source_run_id: uuid.UUID | None = None
    source_conversation_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1)
    artifact_kind: NarrativeArtifactKind = NarrativeArtifactKind.AGENT_NOTE
    metadata: dict[str, Any] = Field(default_factory=dict)


class NarrativeArtifactRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    agent_id: uuid.UUID | None = None
    source_run_id: uuid.UUID | None = None
    source_conversation_id: uuid.UUID | None = None
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


class NarrativePublicationRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    artifact_id: uuid.UUID
    source_draft_id: uuid.UUID | None = None
    status: NarrativePublicationStatus
    reader_visible: bool
    metadata: dict[str, Any]
    published_at: datetime | None = None
    unpublished_at: datetime | None = None
    published_by_user_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("published_at", "unpublished_at", "created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetimes(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("publication datetimes must be timezone-aware")
        return value.astimezone(UTC)


class NarrativeArtifactWithPublication(_FrozenContract):
    artifact: NarrativeArtifactRecord
    publication: NarrativePublicationRecord | None = None


class ConversationNarrativeGenerate(_FrozenContract):
    world_id: uuid.UUID
    conversation_id: uuid.UUID
    artifact_set: ConversationNarrativeArtifactSet = (
        ConversationNarrativeArtifactSet.SUMMARY_AND_CHAPTER
    )
    provider_profile_id: uuid.UUID | None = None
    generation_mode: NarrativeGenerationMode = NarrativeGenerationMode.MANUAL


class ConversationNarrativePromptPreview(_FrozenContract):
    world_id: uuid.UUID
    conversation_id: uuid.UUID
    artifact_set: ConversationNarrativeArtifactSet
    provider_profile_id: uuid.UUID
    provider_profile_key: str
    writer_plugin_identifier: str
    prompt_text: str
    source_turn_count: int
    existing_artifact_count: int
    warnings: list[str]
