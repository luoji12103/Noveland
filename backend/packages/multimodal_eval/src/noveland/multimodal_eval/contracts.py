from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_MULTIMODAL_EVAL_KEY = "multimodal-smoke"


class MultimodalFindingSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BLOCKER = "blocker"


class MultimodalEvalStatus(StrEnum):
    COMPLETED = "completed"
    WARNING = "warning"
    FAILED = "failed"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class MultimodalEvidenceRef(_FrozenContract):
    kind: str = Field(min_length=1, max_length=120)
    id: str = Field(min_length=1, max_length=200)


class MultimodalDiagnosticFinding(_FrozenContract):
    code: str = Field(min_length=1, max_length=120)
    severity: MultimodalFindingSeverity
    message: str = Field(min_length=1, max_length=500)
    evidence_refs: list[MultimodalEvidenceRef] = Field(default_factory=list)


class MultimodalDiagnosticsResult(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    status: MultimodalEvalStatus
    metrics: dict[str, Any]
    blockers: list[MultimodalDiagnosticFinding] = Field(default_factory=list)
    warnings: list[MultimodalDiagnosticFinding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    evidence_refs: list[MultimodalEvidenceRef] = Field(default_factory=list)
    generated_at: datetime

    @field_validator("generated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class MultimodalEvalRunRequest(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    eval_key: str = Field(default=DEFAULT_MULTIMODAL_EVAL_KEY, min_length=1, max_length=120)
    horizon_days: int = Field(default=7, ge=1, le=90)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("eval_key", mode="after")
    @classmethod
    def validate_eval_key(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith("multimodal-"):
            raise ValueError("multimodal eval_key must start with multimodal-")
        return normalized


class MultimodalEvalRunRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    eval_key: str
    horizon_days: int
    status: MultimodalEvalStatus
    started_at: datetime
    finished_at: datetime
    metrics: dict[str, Any]
    recommendations: list[dict[str, Any]]
    blockers: list[dict[str, Any]]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("started_at", "finished_at", "created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
