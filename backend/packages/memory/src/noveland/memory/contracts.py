from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MemoryBackendKind(StrEnum):
    MEM0_OSS = "mem0_oss"
    LOCAL_PGVECTOR = "local_pgvector"


class MemoryWriteSourceKind(StrEnum):
    AGENT_RUN = "agent_run"
    CONVERSATION_TURN = "conversation_turn"
    WORLD_EVENT = "world_event"


class MemoryWriteJobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class MemoryBackendHealthStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class MemoryMessage(_FrozenContract):
    role: str = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1, max_length=16_000)


class MemoryTurn(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    agent_id: uuid.UUID
    conversation_id: uuid.UUID | None = None
    turn_id: uuid.UUID | None = None
    run_id: uuid.UUID | None = None
    source_event_id: uuid.UUID | None = None
    trigger_source: str | None = Field(default=None, max_length=120)
    messages: list[MemoryMessage] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    dedupe_key: str = Field(min_length=1, max_length=240)


class MemoryEvent(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    agent_id: uuid.UUID
    event_id: uuid.UUID
    run_id: uuid.UUID | None = None
    content: str = Field(min_length=1, max_length=16_000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    dedupe_key: str = Field(min_length=1, max_length=240)


class MemoryItemRecord(_FrozenContract):
    id: str
    world_id: uuid.UUID
    agent_id: uuid.UUID
    content: str
    metadata: dict[str, Any]
    backend: str
    created_at: datetime | None = None
    score: float | None = None

    @field_validator("created_at", mode="after")
    @classmethod
    def normalize_created_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(UTC)


class MemorySearchRequest(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    agent_id: uuid.UUID
    query_text: str = Field(min_length=1, max_length=8_000)
    limit: int = Field(default=10, ge=1, le=50)


class MemorySearchResult(_FrozenContract):
    backend: str
    items: list[MemoryItemRecord]
    latency_ms: int | None = Field(default=None, ge=0)


class MemoryContextItem(_FrozenContract):
    id: str
    content: str
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentProfileSnapshot(_FrozenContract):
    aliases: list[str] = Field(default_factory=list)
    identity_notes: list[str] = Field(default_factory=list)
    durable_preferences: list[str] = Field(default_factory=list)
    long_lived_goals: list[str] = Field(default_factory=list)
    language_style_preferences: list[str] = Field(default_factory=list)


class MemoryContext(_FrozenContract):
    worldline_id: uuid.UUID
    backend: str
    items: list[MemoryContextItem]
    profile_snapshot: AgentProfileSnapshot | None = None
    query_text: str


class MemoryDeleteScope(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    agent_id: uuid.UUID
    run_id: uuid.UUID | None = None


class MemoryDeleteResult(_FrozenContract):
    backend: str
    deleted_count: int | None = Field(default=None, ge=0)


class MemoryBackendHealth(_FrozenContract):
    backend: str
    status: MemoryBackendHealthStatus
    details: dict[str, Any] = Field(default_factory=dict)


class MemoryWriteResult(_FrozenContract):
    backend: str
    source_dedupe_key: str
    recorded_count: int = Field(ge=0)
    backend_ids: list[str] = Field(default_factory=list)
    latency_ms: int | None = Field(default=None, ge=0)


class MemoryBackendProfileCreate(_FrozenContract):
    profile_key: str = Field(
        min_length=2,
        max_length=80,
        pattern=r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$",
    )
    name: str = Field(min_length=1, max_length=160)
    backend_kind: MemoryBackendKind
    vector_store_config: dict[str, Any] = Field(default_factory=dict)
    llm_config: dict[str, Any] = Field(default_factory=dict)
    embedder_config: dict[str, Any] = Field(default_factory=dict)
    reranker_config: dict[str, Any] = Field(default_factory=dict)
    secret_refs: dict[str, str] = Field(default_factory=dict)
    is_enabled: bool = True


class MemoryBackendProfileUpdate(_FrozenContract):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    vector_store_config: dict[str, Any] | None = None
    llm_config: dict[str, Any] | None = None
    embedder_config: dict[str, Any] | None = None
    reranker_config: dict[str, Any] | None = None
    secret_refs: dict[str, str] | None = None
    is_enabled: bool | None = None


class MemoryBackendProfileRecord(_FrozenContract):
    id: uuid.UUID
    profile_key: str
    name: str
    backend_kind: MemoryBackendKind
    vector_store_config: dict[str, Any]
    llm_config: dict[str, Any]
    embedder_config: dict[str, Any]
    reranker_config: dict[str, Any]
    secret_refs: dict[str, str]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetimes(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(UTC)


class MemoryProfileSnapshotRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None
    agent_id: uuid.UUID
    aliases: list[str] = Field(default_factory=list)
    identity_notes: list[str] = Field(default_factory=list)
    durable_preferences: list[str] = Field(default_factory=list)
    long_lived_goals: list[str] = Field(default_factory=list)
    language_style_preferences: list[str] = Field(default_factory=list)
    refreshed_at: datetime
    created_at: datetime
    updated_at: datetime

    @field_validator("refreshed_at", "created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetimes(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(UTC)


class MemoryWriteLogRecord(_FrozenContract):
    id: uuid.UUID
    job_id: uuid.UUID
    backend: str
    success: bool
    latency_ms: int | None = Field(default=None, ge=0)
    request_summary: dict[str, Any] = Field(default_factory=dict)
    response_summary: dict[str, Any] = Field(default_factory=dict)
    correlation_ids: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime

    @field_validator("occurred_at", mode="after")
    @classmethod
    def normalize_occurred_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(UTC)


class MemoryWriteJobRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None
    agent_id: uuid.UUID
    backend_profile_id: uuid.UUID
    backend_profile_key: str
    backend_profile_name: str
    backend_kind: MemoryBackendKind
    source_kind: MemoryWriteSourceKind
    source_id: uuid.UUID
    dedupe_key: str
    status: MemoryWriteJobStatus
    attempt_count: int = Field(ge=0)
    next_attempt_at: datetime
    last_error: str | None = None
    processed_at: datetime | None = None
    is_retryable: bool
    terminal_reason: str | None = None
    last_log_success: bool | None = None
    age_seconds: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime

    @field_validator("next_attempt_at", "processed_at", "created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetimes(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(UTC)


class MemoryWriteJobStatusSummary(_FrozenContract):
    pending_count: int = Field(ge=0)
    processing_count: int = Field(ge=0)
    succeeded_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    due_count: int = Field(ge=0)
    retryable_failed_count: int = Field(ge=0)
    terminal_failed_count: int = Field(ge=0)
    stalled_processing_count: int = Field(ge=0)


class MemoryBackfillSourceSummary(_FrozenContract):
    source_kind: MemoryWriteSourceKind
    candidate_count: int = Field(ge=0)
    skipped_existing_count: int = Field(ge=0)
    skipped_no_profile_count: int = Field(ge=0)
    skipped_disabled_profile_count: int = Field(ge=0)


class MemoryBackfillWorldSummary(_FrozenContract):
    world_id: uuid.UUID
    backend_profile_id: uuid.UUID | None = None
    backend_profile_key: str | None = None
    candidate_count: int = Field(ge=0)
    skipped_existing_count: int = Field(ge=0)
    skipped_no_profile_count: int = Field(ge=0)
    skipped_disabled_profile_count: int = Field(ge=0)


class MemoryBackfillDryRunResult(_FrozenContract):
    candidate_count: int = Field(ge=0)
    skipped_existing_count: int = Field(ge=0)
    skipped_no_profile_count: int = Field(ge=0)
    skipped_disabled_profile_count: int = Field(ge=0)
    source_summaries: list[MemoryBackfillSourceSummary] = Field(default_factory=list)
    world_summaries: list[MemoryBackfillWorldSummary] = Field(default_factory=list)


class MemoryBackfillExecutionResult(_FrozenContract):
    enqueued_count: int = Field(ge=0)
    skipped_existing_count: int = Field(ge=0)
    skipped_no_profile_count: int = Field(ge=0)
    skipped_disabled_profile_count: int = Field(ge=0)
    batch_limit: int = Field(ge=1)
    dry_run_before: MemoryBackfillDryRunResult


class MemoryRetrievalLogRecord(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None
    agent_id: uuid.UUID
    backend_profile_id: uuid.UUID | None = None
    backend: str
    query_text: str
    hit_count: int = Field(ge=0)
    selected_item_ids: list[str] = Field(default_factory=list)
    latency_ms: int | None = Field(default=None, ge=0)
    context_item_count: int = Field(ge=0)
    occurred_at: datetime

    @field_validator("occurred_at", mode="after")
    @classmethod
    def normalize_occurred_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(UTC)


class MemoryEvalCase(_FrozenContract):
    label: str = Field(min_length=1, max_length=160)
    world_id: uuid.UUID
    agent_id: uuid.UUID
    query_text: str = Field(min_length=1, max_length=8_000)
    limit: int = Field(default=5, ge=1, le=50)


class MemoryEvalCaseResult(_FrozenContract):
    label: str
    query_text: str
    backend: str
    hit_count: int = Field(ge=0)
    context_item_count: int = Field(ge=0)
    latency_ms: int | None = Field(default=None, ge=0)


class MemoryEvalResult(_FrozenContract):
    backend: str
    case_count: int = Field(ge=0)
    hit_case_count: int = Field(ge=0)
    average_latency_ms: int | None = Field(default=None, ge=0)
    average_context_items: float = Field(ge=0)
    recommendations: list[str] = Field(default_factory=list)
    cases: list[MemoryEvalCaseResult] = Field(default_factory=list)


class MemoryQueueReadinessReport(_FrozenContract):
    status: str
    pending_count: int = Field(ge=0)
    processing_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    retryable_failed_count: int = Field(ge=0)
    terminal_failed_count: int = Field(ge=0)
    stalled_processing_count: int = Field(ge=0)
    due_count: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    stalled_after_seconds: int = Field(ge=1)
    external_queue_ready: bool
    issues: list[str] = Field(default_factory=list)


class MemoryBackend(Protocol):
    def record_turn(self, turn: MemoryTurn) -> MemoryWriteResult:
        """Persist one turn-shaped memory payload."""

    def record_events(self, events: Sequence[MemoryEvent]) -> MemoryWriteResult:
        """Persist one or more event-shaped memory payloads."""

    def list_memories(
        self,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
        worldline_id: uuid.UUID | None = None,
    ) -> Sequence[MemoryItemRecord]:
        """List memories for one agent scope."""

    def search(self, request: MemorySearchRequest) -> MemorySearchResult:
        """Search memories for one agent scope."""

    def delete_scope(self, scope: MemoryDeleteScope) -> MemoryDeleteResult:
        """Delete one agent scope, optionally narrowed to one run."""

    def healthcheck(self) -> MemoryBackendHealth:
        """Perform a shallow backend health check."""
