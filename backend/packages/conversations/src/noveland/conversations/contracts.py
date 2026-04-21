from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

SESSION_KEY_PATTERN = r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$"


class ConversationScopeType(StrEnum):
    SCENE = "scene"
    WORLD = "world"


class ConversationMode(StrEnum):
    MANUAL_CHAIN = "manual_chain"
    AUTO_DIALOGUE = "auto_dialogue"


class ConversationSessionStatus(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversationSpeakerKind(StrEnum):
    OPERATOR = "operator"
    AGENT = "agent"


class ConversationTurnStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class ConversationSessionCreate(_FrozenContract):
    world_id: uuid.UUID
    scene_id: uuid.UUID | None = None
    session_key: str = Field(pattern=SESSION_KEY_PATTERN, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    scope_type: ConversationScopeType
    mode: ConversationMode
    objective: str = Field(default="", max_length=8_000)
    opening_prompt: str = Field(default="", max_length=12_000)
    max_turns: int = Field(default=12, ge=1, le=200)

    @model_validator(mode="after")
    def validate_scope(self) -> ConversationSessionCreate:
        if self.scope_type == ConversationScopeType.SCENE and self.scene_id is None:
            raise ValueError("scene_id is required for scene-scoped conversations")
        if self.scope_type == ConversationScopeType.WORLD and self.scene_id is not None:
            raise ValueError("scene_id is not allowed for world-scoped conversations")
        return self


class ConversationSessionUpdate(_FrozenContract):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    objective: str | None = Field(default=None, max_length=8_000)
    opening_prompt: str | None = Field(default=None, max_length=12_000)
    max_turns: int | None = Field(default=None, ge=1, le=200)


class ConversationParticipantDefinition(_FrozenContract):
    agent_id: uuid.UUID
    turn_order: int = Field(ge=0, le=10_000)
    is_enabled: bool = True


class ConversationSeed(_FrozenContract):
    input_text: str = Field(min_length=1, max_length=12_000)


class ConversationSessionRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    scene_id: uuid.UUID | None
    session_key: str
    title: str
    scope_type: ConversationScopeType
    mode: ConversationMode
    status: ConversationSessionStatus
    objective: str
    opening_prompt: str
    max_turns: int
    next_turn_index: int
    created_at: datetime
    updated_at: datetime


class ConversationParticipantRecord(_FrozenContract):
    id: uuid.UUID
    session_id: uuid.UUID
    agent_id: uuid.UUID
    turn_order: int
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class ConversationTurnRecord(_FrozenContract):
    id: uuid.UUID
    session_id: uuid.UUID
    turn_index: int
    speaker_kind: ConversationSpeakerKind
    speaker_agent_id: uuid.UUID | None
    input_text: str
    output_text: str | None
    status: ConversationTurnStatus
    run_id: uuid.UUID | None
    error_text: str | None
    created_at: datetime
    updated_at: datetime


class PreparedConversationTurn(_FrozenContract):
    session: ConversationSessionRecord
    speaker_agent_id: uuid.UUID
    turn_index: int
    participant_index: int
    available_participant_count: int
    prompt_text: str
    emit_started_event: bool = False


class ConversationAdvanceResult(_FrozenContract):
    session: ConversationSessionRecord
    turn: ConversationTurnRecord


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC)
