from __future__ import annotations

import builtins
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from noveland.invocations.models import ModelInvocation
from noveland.media.models import MediaJob
from noveland.observability.contracts import (
    DiagnosticComponent,
    DiagnosticRetentionDryRun,
    DiagnosticRetentionPruneResult,
    DiagnosticSeverity,
    IncidentComponentSummary,
    IncidentEvidenceRef,
    IncidentRetentionSummary,
    IncidentStatus,
    IncidentSummary,
    RuntimeDiagnosticCreate,
    RuntimeDiagnosticRecord,
)
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.providers.models import ProviderBudgetPolicy, ProviderHealthCheck, ProviderIntegration
from noveland.worlds.models import LongRunEvalRun
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

REDACTED_VALUE = "[redacted]"
SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
    "secret",
    "session",
    "token",
)


class RuntimeDiagnosticsService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(self, diagnostic_create: RuntimeDiagnosticCreate) -> RuntimeDiagnosticRecord:
        model = RuntimeDiagnosticEvent(
            id=uuid.uuid4(),
            severity=diagnostic_create.severity.value,
            component=diagnostic_create.component.value,
            event_type=diagnostic_create.event_type,
            message=diagnostic_create.message,
            details=redact_diagnostic_details(diagnostic_create.details),
            occurred_at=diagnostic_create.occurred_at or datetime.now(UTC),
            world_id=diagnostic_create.world_id,
            agent_id=diagnostic_create.agent_id,
            run_id=diagnostic_create.run_id,
            provider_profile_id=diagnostic_create.provider_profile_id,
        )
        self._session.add(model)
        self._session.flush()
        return _record(model)

    def list(
        self,
        *,
        severity: DiagnosticSeverity | None = None,
        component: DiagnosticComponent | None = None,
        limit: int = 20,
    ) -> builtins.list[RuntimeDiagnosticRecord]:
        statement = select(RuntimeDiagnosticEvent)
        if severity is not None:
            statement = statement.where(RuntimeDiagnosticEvent.severity == severity.value)
        if component is not None:
            statement = statement.where(RuntimeDiagnosticEvent.component == component.value)
        return self._records(_limited(statement, limit))

    def list_for_world(
        self,
        world_id: uuid.UUID,
        *,
        agent_id: uuid.UUID | None = None,
        component: DiagnosticComponent | None = None,
        limit: int = 20,
    ) -> builtins.list[RuntimeDiagnosticRecord]:
        statement = select(RuntimeDiagnosticEvent).where(
            RuntimeDiagnosticEvent.world_id == world_id,
        )
        if agent_id is not None:
            statement = statement.where(RuntimeDiagnosticEvent.agent_id == agent_id)
        if component is not None:
            statement = statement.where(RuntimeDiagnosticEvent.component == component.value)
        return self._records(_limited(statement, limit))

    def dry_run_retention(self, *, retention_days: int) -> DiagnosticRetentionDryRun:
        safe_retention_days = max(1, retention_days)
        cutoff = datetime.now(UTC) - timedelta(days=safe_retention_days)
        pruneable_count = self._count_before(cutoff)
        retained_count = self._count_since(cutoff)
        return DiagnosticRetentionDryRun(
            retention_days=safe_retention_days,
            cutoff=cutoff,
            pruneable_count=pruneable_count,
            retained_count=retained_count,
        )

    def prune_retention(
        self,
        *,
        retention_days: int,
        limit: int = 1000,
    ) -> DiagnosticRetentionPruneResult:
        dry_run = self.dry_run_retention(retention_days=retention_days)
        safe_limit = max(1, min(limit, 10_000))
        models = self._session.scalars(
            select(RuntimeDiagnosticEvent)
            .where(RuntimeDiagnosticEvent.occurred_at < dry_run.cutoff)
            .order_by(RuntimeDiagnosticEvent.occurred_at.asc())
            .limit(safe_limit),
        ).all()
        for model in models:
            self._session.delete(model)
        self._session.flush()
        retained_count = self._count_since(dry_run.cutoff)
        remaining_pruneable_count = self._count_before(dry_run.cutoff)
        return DiagnosticRetentionPruneResult(
            retention_days=dry_run.retention_days,
            cutoff=dry_run.cutoff,
            pruneable_count=remaining_pruneable_count,
            retained_count=retained_count,
            pruned_count=len(models),
        )

    def _records(
        self,
        statement: Select[tuple[RuntimeDiagnosticEvent]],
    ) -> builtins.list[RuntimeDiagnosticRecord]:
        return [_record(model) for model in self._session.scalars(statement).all()]

    def _count_before(self, cutoff: datetime) -> int:
        return int(
            self._session.scalar(
                select(func.count(RuntimeDiagnosticEvent.id)).where(
                    RuntimeDiagnosticEvent.occurred_at < cutoff,
                ),
            )
            or 0
        )

    def _count_since(self, cutoff: datetime) -> int:
        return int(
            self._session.scalar(
                select(func.count(RuntimeDiagnosticEvent.id)).where(
                    RuntimeDiagnosticEvent.occurred_at >= cutoff,
                ),
            )
            or 0
        )


def redact_diagnostic_details(details: dict[str, Any]) -> dict[str, Any]:
    redacted = _redact_value(details)
    if not isinstance(redacted, dict):
        return {}
    return redacted


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, nested_value in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                output[key_text] = REDACTED_VALUE
            else:
                output[key_text] = _redact_value(nested_value)
        return output
    if isinstance(value, list | tuple):
        return [_redact_value(item) for item in value]
    if isinstance(value, str) and len(value) > 500:
        return f"{value[:500]}..."
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(fragment in normalized for fragment in SENSITIVE_KEY_FRAGMENTS)


def _limited(
    statement: Select[tuple[RuntimeDiagnosticEvent]],
    limit: int,
) -> Select[tuple[RuntimeDiagnosticEvent]]:
    safe_limit = max(1, min(limit, 100))
    return statement.order_by(RuntimeDiagnosticEvent.occurred_at.desc()).limit(safe_limit)


class IncidentDiagnosticsService:
    """Safe incident-summary aggregation over existing operational evidence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def summary(
        self,
        *,
        world_id: uuid.UUID | None = None,
        retention_days: int = 30,
        evidence_limit_per_component: int = 5,
    ) -> IncidentSummary:
        safe_limit = max(1, min(evidence_limit_per_component, 20))
        components = [
            self._runtime_component(world_id, safe_limit),
            self._provider_health_component(world_id, safe_limit),
            self._provider_budget_component(world_id, safe_limit),
            self._invocation_component(world_id, safe_limit),
            self._media_job_component(world_id, safe_limit),
            self._multimodal_eval_component(world_id, safe_limit),
            self._narrative_quality_component(world_id, safe_limit),
        ]
        evidence_count = sum(component.evidence_count for component in components)
        error_count = sum(component.error_count for component in components)
        warning_count = sum(component.warning_count for component in components)
        status = _summary_status(components)
        retention = RuntimeDiagnosticsService(self._session).dry_run_retention(
            retention_days=retention_days,
        )
        return IncidentSummary(
            status=status,
            generated_at=datetime.now(UTC),
            component_count=len(components),
            evidence_count=evidence_count,
            error_count=error_count,
            warning_count=warning_count,
            world_id=world_id,
            components=components,
            retention=IncidentRetentionSummary(
                authority="runtime_diagnostic_events",
                retention_days=retention.retention_days,
                cutoff=retention.cutoff,
                pruneable_count=retention.pruneable_count,
                retained_count=retention.retained_count,
            ),
            suppressed_fields=[
                "diagnostic_details",
                "error_payloads",
                "ledger_text_payloads",
                "prompt_snapshot_bodies",
                "provider_payloads",
                "media_object_locations",
                "binary_payloads",
                "resolved_credentials",
            ],
        )

    def _runtime_component(
        self,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> IncidentComponentSummary:
        conditions: list[Any] = [RuntimeDiagnosticEvent.severity.in_(("warning", "error"))]
        if world_id is not None:
            conditions.append(RuntimeDiagnosticEvent.world_id == world_id)
        records = self._session.scalars(
            select(RuntimeDiagnosticEvent)
            .where(*conditions)
            .order_by(RuntimeDiagnosticEvent.occurred_at.desc())
            .limit(limit),
        ).all()
        error_count = self._count(
            RuntimeDiagnosticEvent,
            *conditions,
            RuntimeDiagnosticEvent.severity == "error",
        )
        warning_count = self._count(
            RuntimeDiagnosticEvent,
            *conditions,
            RuntimeDiagnosticEvent.severity == "warning",
        )
        refs = [
            IncidentEvidenceRef(
                kind="runtime_diagnostic_event",
                id=str(record.id),
                component="runtime_diagnostics",
                status=record.severity,
                reason_code=f"runtime_{record.severity}",
                world_id=record.world_id,
                occurred_at=record.occurred_at,
            )
            for record in records
        ]
        return _component(
            "runtime_diagnostics",
            error_count=error_count,
            warning_count=warning_count,
            evidence_refs=refs,
        )

    def _provider_health_component(
        self,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> IncidentComponentSummary:
        conditions: list[Any] = [ProviderHealthCheck.status.in_(("unhealthy", "degraded"))]
        statement = select(ProviderHealthCheck).join(
            ProviderIntegration,
            ProviderIntegration.id == ProviderHealthCheck.provider_integration_id,
        )
        count_statement = select(func.count(ProviderHealthCheck.id)).join(
            ProviderIntegration,
            ProviderIntegration.id == ProviderHealthCheck.provider_integration_id,
        )
        if world_id is not None:
            conditions.append(ProviderIntegration.world_id == world_id)
        records = self._session.scalars(
            statement.where(*conditions)
            .order_by(ProviderHealthCheck.checked_at.desc())
            .limit(limit),
        ).all()
        error_count = int(
            self._session.scalar(
                count_statement.where(*conditions, ProviderHealthCheck.status == "unhealthy"),
            )
            or 0
        )
        warning_count = int(
            self._session.scalar(
                count_statement.where(*conditions, ProviderHealthCheck.status == "degraded"),
            )
            or 0
        )
        refs = [
            IncidentEvidenceRef(
                kind="provider_health_check",
                id=str(record.id),
                component="provider_health",
                status=record.status,
                reason_code=f"provider_health_{record.status}",
                occurred_at=record.checked_at,
            )
            for record in records
        ]
        return _component(
            "provider_health",
            error_count=error_count,
            warning_count=warning_count,
            evidence_refs=refs,
        )

    def _provider_budget_component(
        self,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> IncidentComponentSummary:
        conditions: list[Any] = [
            ProviderBudgetPolicy.status == "active",
            ProviderBudgetPolicy.emergency_stop_enabled.is_(True),
        ]
        if world_id is not None:
            conditions.append(ProviderBudgetPolicy.world_id == world_id)
        records = self._session.scalars(
            select(ProviderBudgetPolicy)
            .where(*conditions)
            .order_by(ProviderBudgetPolicy.updated_at.desc())
            .limit(limit),
        ).all()
        error_count = self._count(ProviderBudgetPolicy, *conditions)
        refs = [
            IncidentEvidenceRef(
                kind="provider_budget_policy",
                id=str(record.id),
                component="provider_budget",
                status="blocked",
                reason_code="emergency_stop",
                world_id=record.world_id,
                occurred_at=record.updated_at,
            )
            for record in records
        ]
        return _component(
            "provider_budget",
            error_count=error_count,
            warning_count=0,
            evidence_refs=refs,
        )

    def _invocation_component(
        self,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> IncidentComponentSummary:
        conditions: list[Any] = [ModelInvocation.status == "failed"]
        if world_id is not None:
            conditions.append(ModelInvocation.world_id == world_id)
        records = self._session.scalars(
            select(ModelInvocation)
            .where(*conditions)
            .order_by(ModelInvocation.created_at.desc())
            .limit(limit),
        ).all()
        error_count = self._count(ModelInvocation, *conditions)
        refs = [
            IncidentEvidenceRef(
                kind="model_invocation",
                id=str(record.id),
                component="model_invocations",
                status=record.status,
                reason_code=f"{record.invocation_kind}_{record.status}",
                world_id=record.world_id,
                worldline_id=record.worldline_id,
                occurred_at=record.updated_at,
            )
            for record in records
        ]
        return _component(
            "model_invocations",
            error_count=error_count,
            warning_count=0,
            evidence_refs=refs,
        )

    def _media_job_component(
        self,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> IncidentComponentSummary:
        conditions: list[Any] = [MediaJob.status == "failed"]
        if world_id is not None:
            conditions.append(MediaJob.world_id == world_id)
        records = self._session.scalars(
            select(MediaJob).where(*conditions).order_by(MediaJob.created_at.desc()).limit(limit),
        ).all()
        error_count = self._count(MediaJob, *conditions)
        refs = [
            IncidentEvidenceRef(
                kind="media_job",
                id=str(record.id),
                component="media_jobs",
                status=record.status,
                reason_code=f"{record.job_kind}_{record.status}",
                world_id=record.world_id,
                worldline_id=record.worldline_id,
                occurred_at=record.updated_at,
            )
            for record in records
        ]
        return _component(
            "media_jobs",
            error_count=error_count,
            warning_count=0,
            evidence_refs=refs,
        )

    def _multimodal_eval_component(
        self,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> IncidentComponentSummary:
        conditions: list[Any] = [
            LongRunEvalRun.eval_key.like("multimodal-%"),
            LongRunEvalRun.status.in_(("warning", "failed")),
        ]
        if world_id is not None:
            conditions.append(LongRunEvalRun.world_id == world_id)
        records = self._session.scalars(
            select(LongRunEvalRun)
            .where(*conditions)
            .order_by(LongRunEvalRun.created_at.desc())
            .limit(limit),
        ).all()
        error_count = self._count(LongRunEvalRun, *conditions, LongRunEvalRun.status == "failed")
        warning_count = self._count(
            LongRunEvalRun,
            *conditions,
            LongRunEvalRun.status == "warning",
        )
        refs = [
            IncidentEvidenceRef(
                kind="long_run_eval_run",
                id=str(record.id),
                component="multimodal_evals",
                status=record.status,
                reason_code=f"multimodal_eval_{record.status}",
                world_id=record.world_id,
                worldline_id=record.worldline_id,
                occurred_at=record.finished_at,
            )
            for record in records
        ]
        return _component(
            "multimodal_evals",
            error_count=error_count,
            warning_count=warning_count,
            evidence_refs=refs,
        )

    def _narrative_quality_component(
        self,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> IncidentComponentSummary:
        conditions: list[Any] = [
            LongRunEvalRun.eval_key.not_like("multimodal-%"),
            LongRunEvalRun.status.in_(("warning", "failed")),
        ]
        if world_id is not None:
            conditions.append(LongRunEvalRun.world_id == world_id)
        records = self._session.scalars(
            select(LongRunEvalRun)
            .where(*conditions)
            .order_by(LongRunEvalRun.created_at.desc())
            .limit(limit),
        ).all()
        error_count = self._count(LongRunEvalRun, *conditions, LongRunEvalRun.status == "failed")
        warning_count = self._count(
            LongRunEvalRun,
            *conditions,
            LongRunEvalRun.status == "warning",
        )
        refs = [
            IncidentEvidenceRef(
                kind="long_run_eval_run",
                id=str(record.id),
                component="narrative_quality",
                status=record.status,
                reason_code=f"narrative_quality_eval_{record.status}",
                world_id=record.world_id,
                worldline_id=record.worldline_id,
                occurred_at=record.finished_at,
            )
            for record in records
        ]
        return _component(
            "narrative_quality",
            error_count=error_count,
            warning_count=warning_count,
            evidence_refs=refs,
        )

    def _count(self, model: type[Any], *conditions: Any) -> int:
        return int(
            self._session.scalar(select(func.count(model.id)).where(*conditions))
            or 0
        )


def _component(
    component: str,
    *,
    error_count: int,
    warning_count: int,
    evidence_refs: list[IncidentEvidenceRef],
) -> IncidentComponentSummary:
    status = IncidentStatus.OK
    if error_count > 0:
        status = IncidentStatus.BLOCKED
    elif warning_count > 0:
        status = IncidentStatus.WATCH
    latest_at = max(
        (ref.occurred_at for ref in evidence_refs if ref.occurred_at is not None),
        default=None,
    )
    return IncidentComponentSummary(
        component=component,
        status=status,
        evidence_count=error_count + warning_count,
        error_count=error_count,
        warning_count=warning_count,
        latest_at=latest_at,
        evidence_refs=evidence_refs,
    )


def _summary_status(components: list[IncidentComponentSummary]) -> IncidentStatus:
    if any(component.status == IncidentStatus.BLOCKED for component in components):
        return IncidentStatus.BLOCKED
    if any(component.status == IncidentStatus.WATCH for component in components):
        return IncidentStatus.WATCH
    return IncidentStatus.OK


def _record(model: RuntimeDiagnosticEvent) -> RuntimeDiagnosticRecord:
    return RuntimeDiagnosticRecord(
        id=model.id,
        severity=DiagnosticSeverity(model.severity),
        component=DiagnosticComponent(model.component),
        event_type=model.event_type,
        message=model.message,
        details=model.details,
        occurred_at=_utc(model.occurred_at),
        world_id=model.world_id,
        agent_id=model.agent_id,
        run_id=model.run_id,
        provider_profile_id=model.provider_profile_id,
        created_at=_utc(model.created_at),
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
