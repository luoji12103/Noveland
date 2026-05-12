from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from noveland.media.contracts import MediaJobRecord
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

LEAKY_KEYS = {
    "storage_uri",
    "preview_uri",
    "thumbnail_uri",
    "base64",
    "bytes",
    "path",
    "file_path",
    "raw_prompt",
    "raw_output",
}


class AssetGenerationPolicyStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


class AssetGenerationRunKind(StrEnum):
    PREVIEW = "preview"
    APPLY = "apply"


class AssetGenerationRunStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AssetGenerationProposalKind(StrEnum):
    VISUAL_SCENE = "visual_scene"
    SPEECH_AUDIO = "speech_audio"
    SCENE_BACKGROUND = "scene_background"
    CHARACTER_SPRITE = "character_sprite"
    COMPOSITE_SCENE = "composite_scene"


class AssetGenerationProposalStatus(StrEnum):
    PROPOSED = "proposed"
    APPLIED = "applied"
    DISMISSED = "dismissed"
    BLOCKED = "blocked"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class AssetGenerationPolicyCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    policy_key: str = Field(min_length=1, max_length=120)
    status: AssetGenerationPolicyStatus = AssetGenerationPolicyStatus.ACTIVE
    budget_json: dict[str, Any] = Field(default_factory=dict)
    lookahead_json: dict[str, Any] = Field(default_factory=dict)
    provider_preferences_json: dict[str, Any] = Field(default_factory=dict)
    rules_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("policy_key", mode="after")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("policy_key must not be empty")
        return normalized

    @field_validator(
        "budget_json",
        "lookahead_json",
        "provider_preferences_json",
        "rules_json",
        mode="after",
    )
    @classmethod
    def validate_safe_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value, "policy JSON")
        return value


class AssetGenerationPolicyUpdate(_FrozenContract):
    status: AssetGenerationPolicyStatus | None = None
    budget_json: dict[str, Any] | None = None
    lookahead_json: dict[str, Any] | None = None
    provider_preferences_json: dict[str, Any] | None = None
    rules_json: dict[str, Any] | None = None

    @field_validator(
        "budget_json",
        "lookahead_json",
        "provider_preferences_json",
        "rules_json",
        mode="after",
    )
    @classmethod
    def validate_safe_json(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            _assert_safe_json(value, "policy JSON")
        return value


class AssetGenerationPolicyRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    policy_key: str
    status: AssetGenerationPolicyStatus
    budget_json: dict[str, Any]
    lookahead_json: dict[str, Any]
    provider_preferences_json: dict[str, Any]
    rules_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class AssetGenerationProposalRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    run_id: uuid.UUID
    proposal_kind: AssetGenerationProposalKind
    target_ref_kind: str
    target_ref_id: uuid.UUID
    reason: str
    evidence_json: dict[str, Any]
    priority: int
    estimated_cost: float | None
    provider_kind: str | None
    provider_id: uuid.UUID | None
    request_json: dict[str, Any]
    status: AssetGenerationProposalStatus
    resulting_media_job_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class AssetGenerationRunRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    policy_id: uuid.UUID | None
    run_kind: AssetGenerationRunKind
    status: AssetGenerationRunStatus
    summary_json: dict[str, Any]
    created_by_actor_ref: str
    created_at: datetime
    updated_at: datetime
    proposals: list[AssetGenerationProposalRead] = Field(default_factory=list)

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class AssetGenerationPreviewRequest(_FrozenContract):
    worldline_id: uuid.UUID
    policy_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    current_turn_id: uuid.UUID | None = None
    lookahead_turns: int = Field(default=2, ge=0, le=20)
    include_visual: bool = True
    include_speech: bool = True
    max_total_estimated_cost: float | None = Field(default=None, ge=0)
    max_proposals: int | None = Field(default=None, ge=1, le=200)


class AssetGenerationPreviewResult(_FrozenContract):
    run: AssetGenerationRunRead


class AssetGenerationApplyRequest(_FrozenContract):
    worldline_id: uuid.UUID
    run_id: uuid.UUID
    proposal_ids: tuple[uuid.UUID, ...] = ()


class AssetGenerationApplyResult(_FrozenContract):
    source_run_id: uuid.UUID
    apply_run: AssetGenerationRunRead
    applied_proposals: list[AssetGenerationProposalRead]
    media_jobs: list[MediaJobRecord]


class MediaJobReprioritizeRequest(_FrozenContract):
    worldline_id: uuid.UUID
    job_ids: tuple[uuid.UUID, ...] = ()
    invalidation_key: str | None = Field(default=None, min_length=1, max_length=160)
    priority: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_target(self) -> MediaJobReprioritizeRequest:
        if not self.job_ids and self.invalidation_key is None:
            raise ValueError("job_ids or invalidation_key is required")
        return self


class MediaJobReprioritizeResult(_FrozenContract):
    jobs: list[MediaJobRecord]


class MediaJobCancelSupersededRequest(_FrozenContract):
    worldline_id: uuid.UUID
    job_ids: tuple[uuid.UUID, ...] = ()
    invalidation_key: str | None = Field(default=None, min_length=1, max_length=160)

    @model_validator(mode="after")
    def validate_target(self) -> MediaJobCancelSupersededRequest:
        if not self.job_ids and self.invalidation_key is None:
            raise ValueError("job_ids or invalidation_key is required")
        return self


class MediaJobCancelSupersededResult(_FrozenContract):
    cancelled_job_ids: list[uuid.UUID]
    skipped_job_ids: list[uuid.UUID]


def _assert_safe_json(value: dict[str, Any], field_name: str) -> None:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be JSON serializable") from exc
    _reject_leaky_json(value)


def _reject_leaky_json(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in LEAKY_KEYS:
                raise ValueError(f"{key} is not allowed in asset generation JSON")
            _reject_leaky_json(item)
    elif isinstance(value, list | tuple):
        for item in value:
            _reject_leaky_json(item)
    elif isinstance(value, str):
        lowered = value.lower()
        if lowered.startswith(("local://", "file://")):
            raise ValueError("storage or file paths are not allowed in asset generation JSON")
        if "base64," in lowered:
            raise ValueError("base64 data is not allowed in asset generation JSON")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
