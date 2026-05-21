from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from noveland.observability.contracts import IncidentEvidenceRef
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModerationCategory(StrEnum):
    SAFETY = "safety"
    PRIVACY = "privacy"
    COPYRIGHT = "copyright"
    ABUSE = "abuse"
    QUALITY = "quality"
    SECURITY = "security"
    OTHER = "other"


class ModerationSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ModerationReportStatus(StrEnum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    ESCALATED = "escalated"


class ModerationActionStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    CANCELED = "canceled"


class ModerationIncidentStatus(StrEnum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    MITIGATED = "mitigated"
    CLOSED = "closed"


class ModerationTargetKind(StrEnum):
    WORLD = "world"
    WORLDLINE = "worldline"
    SCENE = "scene"
    NARRATIVE_PUBLICATION = "narrative_publication"
    CONVERSATION_SESSION = "conversation_session"
    CONVERSATION_TURN = "conversation_turn"
    MEDIA_ASSET = "media_asset"
    PROVIDER_INTEGRATION = "provider_integration"
    PLUGIN_PACKAGE = "plugin_package"
    PLAYER_PROFILE = "player_profile"
    OTHER = "other"


class ModerationActionKind(StrEnum):
    DISABLE_MEDIA = "disable_media"
    DISABLE_WORLD = "disable_world"
    DISABLE_PROVIDER = "disable_provider"
    ROLLBACK_REVIEW = "rollback_review"
    TAKEDOWN_CONTENT = "takedown_content"
    NOTE_ONLY = "note_only"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class ModerationReportCreate(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    target_ref_kind: ModerationTargetKind
    target_ref_id: uuid.UUID | None = None
    category: ModerationCategory = ModerationCategory.OTHER
    severity: ModerationSeverity = ModerationSeverity.LOW
    reason: str = Field(min_length=1, max_length=500)
    reporter_note: str | None = Field(default=None, max_length=1000)
    evidence_refs: tuple[IncidentEvidenceRef, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModerationReportReview(_FrozenContract):
    status: ModerationReportStatus
    review_note: str | None = Field(default=None, max_length=1000)


class ModerationReportRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None
    reporter_user_id: uuid.UUID
    target_ref_kind: ModerationTargetKind
    target_ref_id: uuid.UUID | None
    category: ModerationCategory
    severity: ModerationSeverity
    status: ModerationReportStatus
    reason: str
    reporter_note: str | None
    evidence_refs: tuple[IncidentEvidenceRef, ...]
    created_by_actor_ref: str
    reviewed_by_actor_ref: str | None
    reviewed_at: datetime | None
    review_note: str | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", "reviewed_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        return _normalize_datetime(value)


class ModerationActionCreate(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    report_id: uuid.UUID | None = None
    incident_id: uuid.UUID | None = None
    action_kind: ModerationActionKind
    status: ModerationActionStatus = ModerationActionStatus.PROPOSED
    target_ref_kind: ModerationTargetKind
    target_ref_id: uuid.UUID | None = None
    reason: str = Field(min_length=1, max_length=500)
    review_note: str | None = Field(default=None, max_length=1000)
    evidence_refs: tuple[IncidentEvidenceRef, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModerationActionRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None
    report_id: uuid.UUID | None
    incident_id: uuid.UUID | None
    action_kind: ModerationActionKind
    status: ModerationActionStatus
    target_ref_kind: ModerationTargetKind
    target_ref_id: uuid.UUID | None
    reason: str
    audit_summary: dict[str, Any]
    evidence_refs: tuple[IncidentEvidenceRef, ...]
    created_by_actor_ref: str
    reviewed_by_actor_ref: str | None
    reviewed_at: datetime | None
    review_note: str | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", "reviewed_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        return _normalize_datetime(value)


class ModerationIncidentCreate(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    status: ModerationIncidentStatus = ModerationIncidentStatus.OPEN
    severity: ModerationSeverity = ModerationSeverity.MEDIUM
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=1000)
    report_ids: tuple[uuid.UUID, ...] = ()
    action_ids: tuple[uuid.UUID, ...] = ()
    evidence_refs: tuple[IncidentEvidenceRef, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModerationIncidentReview(_FrozenContract):
    status: ModerationIncidentStatus
    review_note: str | None = Field(default=None, max_length=1000)
    report_ids: tuple[uuid.UUID, ...] | None = None
    action_ids: tuple[uuid.UUID, ...] | None = None


class ModerationIncidentRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None
    status: ModerationIncidentStatus
    severity: ModerationSeverity
    title: str
    summary: str
    report_ids: tuple[uuid.UUID, ...]
    action_ids: tuple[uuid.UUID, ...]
    evidence_refs: tuple[IncidentEvidenceRef, ...]
    created_by_actor_ref: str
    reviewed_by_actor_ref: str | None
    reviewed_at: datetime | None
    review_note: str | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", "reviewed_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        return _normalize_datetime(value)


class ModerationSafetyReviewCreate(_FrozenContract):
    worldline_id: uuid.UUID
    target_ref_kind: ModerationTargetKind
    target_ref_id: uuid.UUID
    category: ModerationCategory = ModerationCategory.SAFETY
    severity: ModerationSeverity = ModerationSeverity.MEDIUM
    policy_key: str = Field(min_length=1, max_length=120)
    finding: str = Field(min_length=1, max_length=500)
    evidence_refs: tuple[IncidentEvidenceRef, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModerationFeedbackEscalationCreate(_FrozenContract):
    feedback_report_id: uuid.UUID
    category: ModerationCategory = ModerationCategory.SAFETY
    severity: ModerationSeverity | None = None
    reason: str = Field(min_length=1, max_length=500)
    evidence_refs: tuple[IncidentEvidenceRef, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
