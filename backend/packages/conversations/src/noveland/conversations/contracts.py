from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from noveland.plugins.constants import BUILTIN_DEFAULT_NARRATIVE_WRITER
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
    STOPPED = "stopped"
    FAILED = "failed"


class ConversationSpeakerKind(StrEnum):
    OPERATOR = "operator"
    AGENT = "agent"


class ConversationTurnStatus(StrEnum):
    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"
    FAILED = "failed"


class ConversationErrorPolicy(StrEnum):
    FAIL_SESSION = "fail_session"
    SKIP_TURN = "skip_turn"
    RETRY_ONCE_THEN_FAIL = "retry_once_then_fail"
    RETRY_ONCE_THEN_SKIP = "retry_once_then_skip"


class ConversationSpeakerPolicyMode(StrEnum):
    ROUND_ROBIN = "round_robin"
    LEAST_RECENT = "least_recent"
    PRIORITY_ORDER = "priority_order"
    MANUAL_NEXT = "manual_next"


class ConversationTerminalReason(StrEnum):
    MAX_TURNS_REACHED = "max_turns_reached"
    LOOP_GUARD_REPEATED_OUTPUT = "loop_guard_repeated_output"
    NO_ENABLED_PARTICIPANTS = "no_enabled_participants"
    CONSECUTIVE_FAILURES_EXCEEDED = "consecutive_failures_exceeded"
    OPERATOR_STOPPED = "operator_stopped"
    SPEAKER_ERROR = "speaker_error"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class ConversationPolicyConfig(_FrozenContract):
    error_policy: ConversationErrorPolicy
    max_consecutive_failed_turns: int = Field(ge=1, le=20)
    loop_guard_window: int = Field(ge=2, le=20)
    repeat_output_threshold: int = Field(ge=2, le=20)
    speaker_policy: ConversationSpeakerPolicyMode = ConversationSpeakerPolicyMode.ROUND_ROBIN
    manual_next_agent_id: uuid.UUID | None = None
    participant_repeat_cooldown: int = Field(default=0, ge=0, le=20)
    min_enabled_participants: int = Field(default=1, ge=1, le=20)
    max_turn_budget: int | None = Field(default=None, ge=1, le=200)

    @model_validator(mode="after")
    def validate_thresholds(self) -> ConversationPolicyConfig:
        if self.repeat_output_threshold > self.loop_guard_window:
            raise ValueError("repeat_output_threshold cannot exceed loop_guard_window")
        return self


class ConversationWriterConfig(_FrozenContract):
    provider_profile_id: uuid.UUID | None = None
    writer_plugin_identifier: str = Field(
        default=BUILTIN_DEFAULT_NARRATIVE_WRITER,
        min_length=1,
        max_length=120,
    )
    writer_plugin_config: dict[str, object] = Field(default_factory=dict)
    auto_generate_on_complete: bool = False
    generate_summary: bool = True
    generate_chapter: bool = True
    style_guide: str = Field(default="", max_length=4_000)
    target_length: str = Field(default="standard", pattern="^(brief|standard|expanded)$")
    source_constraints: str = Field(default="", max_length=4_000)
    include_prompt_preview: bool = True


class ConversationMemoryConfig(_FrozenContract):
    write_turn_memory: bool = True
    retrieve_memory: bool = True
    max_context_items: int = Field(default=5, ge=1, le=20)
    query_window: int = Field(default=8, ge=1, le=50)
    include_recent_turns: bool = True
    include_agent_observations: bool = True
    memory_query_strategy: str = Field(default="prompt", pattern="^(prompt|objective|transcript)$")


class ConversationSessionCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    scene_id: uuid.UUID | None = None
    session_key: str = Field(pattern=SESSION_KEY_PATTERN, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    scope_type: ConversationScopeType
    mode: ConversationMode
    objective: str = Field(default="", max_length=8_000)
    opening_prompt: str = Field(default="", max_length=12_000)
    max_turns: int = Field(default=12, ge=1, le=200)
    policy: ConversationPolicyConfig
    writer_config: ConversationWriterConfig
    memory_config: ConversationMemoryConfig = Field(default_factory=ConversationMemoryConfig)

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
    policy: ConversationPolicyConfig | None = None
    writer_config: ConversationWriterConfig | None = None
    memory_config: ConversationMemoryConfig | None = None


class ConversationParticipantDefinition(_FrozenContract):
    agent_id: uuid.UUID
    turn_order: int = Field(ge=0, le=10_000)
    is_enabled: bool = True


class ConversationSeed(_FrozenContract):
    input_text: str = Field(min_length=1, max_length=12_000)


class ConversationSessionRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None
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
    policy: ConversationPolicyConfig
    writer_config: ConversationWriterConfig
    memory_config: ConversationMemoryConfig
    terminal_reason: ConversationTerminalReason | None
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


class ConversationSpeakerCandidate(_FrozenContract):
    agent_id: uuid.UUID
    display_name: str
    turn_order: int
    is_enabled: bool
    score: float
    reasons: list[str]
    last_spoke_turn_index: int | None = None


class ConversationSpeakerPreview(_FrozenContract):
    session_id: uuid.UUID
    policy_mode: ConversationSpeakerPolicyMode
    selected_agent_id: uuid.UUID | None
    selected_reason: str
    candidates: list[ConversationSpeakerCandidate]


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
