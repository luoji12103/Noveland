from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BetaFeedbackIssueType(StrEnum):
    DIALOGUE = "dialogue"
    PERSONA = "persona"
    MEMORY = "memory"
    SPRITE = "sprite"
    BACKGROUND = "background"
    VOICE = "voice"
    PLAYBACK = "playback"
    PROVIDER = "provider"
    QUOTA = "quota"
    SESSION_RECOVERY = "session_recovery"
    UX = "ux"
    WORLDLINE = "worldline"
    OTHER = "other"


class BetaFeedbackSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BetaFeedbackReportStatus(StrEnum):
    SUBMITTED = "submitted"
    TRIAGED = "triaged"
    INVESTIGATING = "investigating"
    LINKED_TO_REPAIR = "linked_to_repair"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class BetaFeedbackEvidenceKind(StrEnum):
    WORLDLINE = "worldline"
    SCENE = "scene"
    CONVERSATION = "conversation"
    TURN = "turn"
    PRESENTATION = "presentation"
    MEDIA_ASSET = "media_asset"
    MEDIA_JOB = "media_job"
    INVOCATION = "invocation"
    PERSONA = "persona"
    MEMORY = "memory"
    VOICE_PROFILE = "voice_profile"
    SPRITE_SET = "sprite_set"
    SPRITE_VARIANT = "sprite_variant"
    BACKGROUND_PROFILE = "background_profile"
    PROVIDER = "provider"
    PLAYER_ACTOR = "player_actor"
    QUOTA = "quota"
    SESSION = "session"
    UX = "ux"
    OTHER = "other"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class BetaFeedbackEvidenceRef(_FrozenContract):
    kind: BetaFeedbackEvidenceKind
    id: uuid.UUID | None = None
    label: str | None = Field(default=None, max_length=160)
    worldline_id: uuid.UUID | None = None
    role: str | None = Field(default=None, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BetaFeedbackRepairProposalRef(_FrozenContract):
    proposal_id: uuid.UUID
    proposal_kind: str = Field(min_length=1, max_length=120)
    status: str = Field(min_length=1, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BetaFeedbackReportCreate(_FrozenContract):
    worldline_id: uuid.UUID
    issue_type: BetaFeedbackIssueType
    severity: BetaFeedbackSeverity = BetaFeedbackSeverity.LOW
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=1200)
    reporter_note: str | None = Field(default=None, max_length=1000)
    player_actor_id: uuid.UUID | None = None
    evidence_refs: tuple[BetaFeedbackEvidenceRef, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class BetaFeedbackReportTriage(_FrozenContract):
    status: BetaFeedbackReportStatus
    severity: BetaFeedbackSeverity | None = None
    triage_note: str | None = Field(default=None, max_length=1200)
    evidence_refs: tuple[BetaFeedbackEvidenceRef, ...] | None = None
    repair_proposal_refs: tuple[BetaFeedbackRepairProposalRef, ...] | None = None
    metadata: dict[str, Any] | None = None


class BetaFeedbackReportRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    reporter_user_id: uuid.UUID
    player_actor_id: uuid.UUID | None
    issue_type: BetaFeedbackIssueType
    severity: BetaFeedbackSeverity
    status: BetaFeedbackReportStatus
    title: str
    description: str
    reporter_note: str | None
    evidence_refs: tuple[BetaFeedbackEvidenceRef, ...]
    repair_proposal_refs: tuple[BetaFeedbackRepairProposalRef, ...]
    triage_note: str | None
    triaged_by_actor_ref: str | None
    triaged_at: datetime | None
    moderation_report_id: uuid.UUID | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("triaged_at", "created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
