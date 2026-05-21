from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class IncidentStatus(StrEnum):
    OK = "ok"
    WATCH = "watch"
    BLOCKED = "blocked"


class DiagnosticComponent(StrEnum):
    RUNTIME = "runtime"
    PROVIDER = "provider"
    AGENT = "agent"
    CONVERSATION = "conversation"
    EVENT_PUBLISHER = "event_publisher"
    API = "api"
    PLUGIN = "plugin"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class RuntimeDiagnosticCreate(_FrozenContract):
    severity: DiagnosticSeverity
    component: DiagnosticComponent
    event_type: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=500)
    details: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None
    world_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    run_id: uuid.UUID | None = None
    provider_profile_id: uuid.UUID | None = None

    @field_validator("occurred_at", mode="after")
    @classmethod
    def normalize_occurred_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value.astimezone(UTC)


class RuntimeDiagnosticRecord(_FrozenContract):
    id: uuid.UUID
    severity: DiagnosticSeverity
    component: DiagnosticComponent
    event_type: str
    message: str
    details: dict[str, Any]
    occurred_at: datetime
    world_id: uuid.UUID | None
    agent_id: uuid.UUID | None
    run_id: uuid.UUID | None
    provider_profile_id: uuid.UUID | None
    created_at: datetime


class DiagnosticRetentionDryRun(_FrozenContract):
    retention_days: int = Field(ge=1)
    cutoff: datetime
    pruneable_count: int = Field(ge=0)
    retained_count: int = Field(ge=0)

    @field_validator("cutoff", mode="after")
    @classmethod
    def normalize_cutoff(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("cutoff must be timezone-aware")
        return value.astimezone(UTC)


class DiagnosticRetentionPruneResult(DiagnosticRetentionDryRun):
    pruned_count: int = Field(ge=0)


class IncidentEvidenceRef(_FrozenContract):
    kind: str = Field(min_length=1, max_length=120)
    id: str = Field(min_length=1, max_length=200)
    component: str = Field(min_length=1, max_length=120)
    status: str = Field(min_length=1, max_length=80)
    reason_code: str = Field(min_length=1, max_length=120)
    world_id: uuid.UUID | None = None
    worldline_id: uuid.UUID | None = None
    occurred_at: datetime | None = None

    @field_validator("occurred_at", mode="after")
    @classmethod
    def normalize_occurred_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class IncidentComponentSummary(_FrozenContract):
    component: str = Field(min_length=1, max_length=120)
    status: IncidentStatus
    evidence_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    latest_at: datetime | None = None
    evidence_refs: list[IncidentEvidenceRef] = Field(default_factory=list)

    @field_validator("latest_at", mode="after")
    @classmethod
    def normalize_latest_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class IncidentRetentionSummary(_FrozenContract):
    authority: str = Field(min_length=1, max_length=120)
    retention_days: int = Field(ge=1)
    cutoff: datetime
    pruneable_count: int = Field(ge=0)
    retained_count: int = Field(ge=0)

    @field_validator("cutoff", mode="after")
    @classmethod
    def normalize_cutoff(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class IncidentSummary(_FrozenContract):
    status: IncidentStatus
    generated_at: datetime
    component_count: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    world_id: uuid.UUID | None = None
    components: list[IncidentComponentSummary] = Field(default_factory=list)
    retention: IncidentRetentionSummary
    suppressed_fields: list[str] = Field(default_factory=list)

    @field_validator("generated_at", mode="after")
    @classmethod
    def normalize_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class ProductionReadinessSection(_FrozenContract):
    section_key: str = Field(min_length=1, max_length=120)
    status: IncidentStatus
    summary: str = Field(min_length=1, max_length=500)
    evidence_count: int = Field(ge=0)
    blocker_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    evidence_refs: list[IncidentEvidenceRef] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class SelfUseMvpManualChecklistItem(_FrozenContract):
    item_key: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=240)
    status: IncidentStatus
    evidence_hint: str = Field(min_length=1, max_length=500)
    required_for_pass: bool = True


class SelfUseMvpGateReport(_FrozenContract):
    status: IncidentStatus
    generated_at: datetime
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    conversation_id: uuid.UUID | None = None
    readiness_kind: str = Field(default="self_use_mvp_gate", min_length=1)
    section_count: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    blocker_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    sections: list[ProductionReadinessSection] = Field(default_factory=list)
    manual_checklist: list[SelfUseMvpManualChecklistItem] = Field(default_factory=list)
    suppressed_fields: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    archive_recommendation: str = Field(min_length=1, max_length=500)

    @field_validator("generated_at", mode="after")
    @classmethod
    def normalize_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class ProductionReadinessReport(_FrozenContract):
    status: IncidentStatus
    generated_at: datetime
    world_id: uuid.UUID | None = None
    readiness_kind: str = Field(default="internal_production_readiness", min_length=1)
    section_count: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    blocker_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    sections: list[ProductionReadinessSection] = Field(default_factory=list)
    suppressed_fields: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)

    @field_validator("generated_at", mode="after")
    @classmethod
    def normalize_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class PublicLaunchReadinessReport(_FrozenContract):
    status: IncidentStatus
    generated_at: datetime
    world_id: uuid.UUID | None = None
    readiness_kind: str = Field(default="public_launch_readiness", min_length=1)
    section_count: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    blocker_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    sections: list[ProductionReadinessSection] = Field(default_factory=list)
    internal_readiness: ProductionReadinessReport
    required_signoffs: dict[str, bool] = Field(default_factory=dict)
    auto_launch_enabled: bool = False
    suppressed_fields: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)

    @field_validator("generated_at", mode="after")
    @classmethod
    def normalize_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class PrivateBetaSetupReadinessReport(ProductionReadinessReport):
    readiness_kind: str = Field(default="private_beta_world_setup", min_length=1)


class PrivateBetaGateReport(ProductionReadinessReport):
    readiness_kind: str = Field(default="private_beta_gate", min_length=1)
    private_beta_setup: PrivateBetaSetupReadinessReport
    manual_checklist: list[SelfUseMvpManualChecklistItem] = Field(default_factory=list)
    public_launch_ready: bool = False


class BackupRestoreDrillCheck(_FrozenContract):
    check_key: str = Field(min_length=1, max_length=120)
    status: IncidentStatus
    summary: str = Field(min_length=1, max_length=500)
    evidence_count: int = Field(ge=0)
    blocker_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    evidence_refs: list[dict[str, str]] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class BackupRestoreDrillReport(_FrozenContract):
    status: IncidentStatus
    generated_at: datetime
    readiness_kind: str = Field(default="backup_restore_drill", min_length=1)
    target_profile: str = Field(min_length=1, max_length=120)
    check_count: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    blocker_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    checks: list[BackupRestoreDrillCheck] = Field(default_factory=list)
    suppressed_fields: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)

    @field_validator("generated_at", mode="after")
    @classmethod
    def normalize_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
