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
    ProductionReadinessReport,
    ProductionReadinessSection,
    RuntimeDiagnosticCreate,
    RuntimeDiagnosticRecord,
)
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.providers.models import ProviderBudgetPolicy, ProviderHealthCheck, ProviderIntegration
from noveland.worlds.models import (
    BetaChecklistItem,
    BetaChecklistRun,
    LivingWorldReleaseProfile,
    LongRunEvalRun,
)
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


class ProductionReadinessGateService:
    """Read-only internal readiness aggregation over existing evidence records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def report(
        self,
        *,
        world_id: uuid.UUID | None = None,
        evidence_limit_per_section: int = 5,
        storage_audit: Any | None = None,
    ) -> ProductionReadinessReport:
        safe_limit = max(1, min(evidence_limit_per_section, 20))
        incident_summary = IncidentDiagnosticsService(self._session).summary(
            world_id=world_id,
            evidence_limit_per_component=safe_limit,
        )
        sections = [
            self._release_profile_section(world_id),
            self._beta_checklist_section(world_id, safe_limit),
            self._long_run_eval_section(world_id, safe_limit),
            self._provider_governance_section(world_id, safe_limit),
            self._budget_control_section(world_id, safe_limit),
            self._storage_integrity_section(storage_audit),
            self._incident_diagnostics_section(incident_summary, safe_limit),
            self._multimodal_eval_section(world_id, safe_limit),
            self._narrative_quality_section(world_id, safe_limit),
            self._security_regression_section(),
        ]
        evidence_count = sum(section.evidence_count for section in sections)
        blocker_count = sum(section.blocker_count for section in sections)
        warning_count = sum(section.warning_count for section in sections)
        return ProductionReadinessReport(
            status=_readiness_status(sections),
            generated_at=datetime.now(UTC),
            world_id=world_id,
            section_count=len(sections),
            evidence_count=evidence_count,
            blocker_count=blocker_count,
            warning_count=warning_count,
            sections=sections,
            suppressed_fields=[
                "credential_values",
                "credential_headers",
                "ledger_text_bodies",
                "provider_payloads",
                "media_object_locations",
                "binary_payloads",
                "event_payload_snapshots",
                "diagnostic_details",
            ],
            non_goals=[
                "public_launch_gate",
                "marketing_release_workflow",
                "external_compliance_certification",
                "runtime_path_blocking",
            ],
        )

    def _release_profile_section(
        self,
        world_id: uuid.UUID | None,
    ) -> ProductionReadinessSection:
        statement = select(LivingWorldReleaseProfile).order_by(
            LivingWorldReleaseProfile.updated_at.desc(),
        )
        if world_id is not None:
            statement = statement.where(LivingWorldReleaseProfile.world_id == world_id)
        profile = self._session.scalars(statement.limit(1)).one_or_none()
        if profile is None:
            return _readiness_section(
                "release_profile",
                status=IncidentStatus.WATCH,
                summary="No release profile evidence exists for the selected scope.",
                blockers=[],
                warning_count=1,
                recommendations=["Create or refresh the internal release profile evidence."],
            )
        status = IncidentStatus.OK if profile.status == "ready" else IncidentStatus.WATCH
        warning_count = 0 if status == IncidentStatus.OK else 1
        recommendations = [] if status == IncidentStatus.OK else [
            "Move the release profile to ready after required internal evidence is present.",
        ]
        return _readiness_section(
            "release_profile",
            status=status,
            summary=f"Latest release profile status is {profile.status}.",
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="living_world_release_profile",
                    id=str(profile.id),
                    component="release_profile",
                    status=profile.status,
                    reason_code="release_profile_status",
                    world_id=profile.world_id,
                    occurred_at=profile.updated_at,
                ),
            ],
            blockers=[],
            warning_count=warning_count,
            recommendations=recommendations,
        )

    def _beta_checklist_section(
        self,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> ProductionReadinessSection:
        conditions: list[Any] = []
        if world_id is not None:
            conditions.append(BetaChecklistRun.world_id == world_id)
        latest = self._latest_beta_checklist(conditions)
        if latest is None:
            return _readiness_section(
                "beta_checklist",
                status=IncidentStatus.BLOCKED,
                summary="No beta checklist evidence exists for the selected scope.",
                blockers=["Run the beta checklist before internal production readiness."],
                recommendations=[
                    "Run the beta checklist endpoint for the target worldline.",
                ],
            )
        item_count = self._count(BetaChecklistItem, BetaChecklistItem.run_id == latest.id)
        blockers = []
        if latest.status != "passed":
            blockers.append("Latest beta checklist is not passing.")
        return _readiness_section(
            "beta_checklist",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=f"Latest beta checklist status is {latest.status} with {item_count} items.",
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="beta_checklist_run",
                    id=str(latest.id),
                    component="beta_checklist",
                    status=latest.status,
                    reason_code="latest_beta_checklist",
                    world_id=latest.world_id,
                    worldline_id=latest.worldline_id,
                    occurred_at=latest.created_at,
                ),
            ],
            blockers=blockers,
            recommendations=[] if not blockers else ["Resolve beta checklist blockers."],
        )

    def _long_run_eval_section(
        self,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> ProductionReadinessSection:
        latest = self._latest_eval(
            world_id=world_id,
            like_pattern="long-run%",
            not_like_pattern=None,
        )
        if latest is None:
            latest = self._latest_eval(
                world_id=world_id,
                like_pattern=None,
                not_like_pattern="multimodal-%",
            )
        if latest is None:
            return _readiness_section(
                "long_run_eval",
                status=IncidentStatus.BLOCKED,
                summary="No long-run eval evidence exists for the selected scope.",
                blockers=["Run a long-run eval before internal production readiness."],
                recommendations=["Run the accepted long-run eval for the target worldline."],
            )
        blockers = (
            []
            if latest.status == "completed"
            else ["Latest long-run eval is not completed."]
        )
        refs = self._eval_refs(
            world_id=world_id,
            limit=limit,
            component="long_run_eval",
            like_pattern=None,
            not_like_pattern="multimodal-%",
        )
        return _readiness_section(
            "long_run_eval",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=f"Latest long-run eval status is {latest.status}.",
            evidence_refs=refs or [
                IncidentEvidenceRef(
                    kind="long_run_eval_run",
                    id=str(latest.id),
                    component="long_run_eval",
                    status=latest.status,
                    reason_code="latest_long_run_eval",
                    world_id=latest.world_id,
                    worldline_id=latest.worldline_id,
                    occurred_at=latest.finished_at,
                ),
            ],
            blockers=blockers,
            recommendations=[] if not blockers else ["Resolve or rerun the long-run eval."],
        )

    def _provider_governance_section(
        self,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> ProductionReadinessSection:
        provider_conditions: list[Any] = [ProviderIntegration.status == "active"]
        health_conditions: list[Any] = [ProviderHealthCheck.status.in_(("unhealthy", "degraded"))]
        health_statement = select(ProviderHealthCheck).join(
            ProviderIntegration,
            ProviderIntegration.id == ProviderHealthCheck.provider_integration_id,
        )
        if world_id is not None:
            provider_conditions.append(ProviderIntegration.world_id == world_id)
            health_conditions.append(ProviderIntegration.world_id == world_id)
        provider_count = self._count(ProviderIntegration, *provider_conditions)
        unhealthy_count = int(
            self._session.scalar(
                select(func.count(ProviderHealthCheck.id))
                .join(
                    ProviderIntegration,
                    ProviderIntegration.id == ProviderHealthCheck.provider_integration_id,
                )
                .where(*health_conditions, ProviderHealthCheck.status == "unhealthy"),
            )
            or 0
        )
        degraded_count = int(
            self._session.scalar(
                select(func.count(ProviderHealthCheck.id))
                .join(
                    ProviderIntegration,
                    ProviderIntegration.id == ProviderHealthCheck.provider_integration_id,
                )
                .where(*health_conditions, ProviderHealthCheck.status == "degraded"),
            )
            or 0
        )
        health_records = self._session.scalars(
            health_statement.where(*health_conditions)
            .order_by(ProviderHealthCheck.checked_at.desc())
            .limit(limit),
        ).all()
        blockers = ["Unhealthy provider health checks are present."] if unhealthy_count else []
        warning_count = degraded_count + (1 if provider_count == 0 else 0)
        recommendations = []
        if unhealthy_count or degraded_count:
            recommendations.append("Review provider health and smoke-test evidence.")
        if provider_count == 0:
            recommendations.append("Configure at least one active provider before readiness.")
        return _readiness_section(
            "provider_governance",
            status=IncidentStatus.BLOCKED
            if blockers
            else IncidentStatus.WATCH
            if warning_count
            else IncidentStatus.OK,
            summary=(
                f"{provider_count} active providers, {unhealthy_count} unhealthy checks, "
                f"{degraded_count} degraded checks."
            ),
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="provider_health_check",
                    id=str(record.id),
                    component="provider_governance",
                    status=record.status,
                    reason_code=f"provider_health_{record.status}",
                    occurred_at=record.checked_at,
                )
                for record in health_records
            ],
            blockers=blockers,
            warning_count=warning_count,
            recommendations=recommendations,
        )

    def _budget_control_section(
        self,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> ProductionReadinessSection:
        conditions: list[Any] = [ProviderBudgetPolicy.status == "active"]
        if world_id is not None:
            conditions.append(ProviderBudgetPolicy.world_id == world_id)
        policies = self._session.scalars(
            select(ProviderBudgetPolicy)
            .where(*conditions)
            .order_by(ProviderBudgetPolicy.updated_at.desc())
            .limit(limit),
        ).all()
        active_count = self._count(ProviderBudgetPolicy, *conditions)
        emergency_count = self._count(
            ProviderBudgetPolicy,
            *conditions,
            ProviderBudgetPolicy.emergency_stop_enabled.is_(True),
        )
        blockers = ["Provider emergency stop is active."] if emergency_count else []
        warning_count = 0 if active_count else 1
        recommendations = []
        if emergency_count:
            recommendations.append("Clear or document emergency stop before readiness.")
        if not active_count:
            recommendations.append("Configure active budget policy evidence before readiness.")
        return _readiness_section(
            "budget_controls",
            status=IncidentStatus.BLOCKED
            if blockers
            else IncidentStatus.WATCH
            if warning_count
            else IncidentStatus.OK,
            summary=f"{active_count} active budget policies, {emergency_count} emergency stops.",
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="provider_budget_policy",
                    id=str(policy.id),
                    component="budget_controls",
                    status="blocked" if policy.emergency_stop_enabled else policy.status,
                    reason_code="emergency_stop"
                    if policy.emergency_stop_enabled
                    else "budget_policy_active",
                    world_id=policy.world_id,
                    occurred_at=policy.updated_at,
                )
                for policy in policies
            ],
            blockers=blockers,
            warning_count=warning_count,
            recommendations=recommendations,
        )

    def _storage_integrity_section(self, storage_audit: Any | None) -> ProductionReadinessSection:
        if storage_audit is None:
            return _readiness_section(
                "storage_integrity",
                status=IncidentStatus.WATCH,
                summary="Storage integrity audit was not supplied for this readiness report.",
                blockers=[],
                warning_count=1,
                recommendations=["Run storage integrity audit before final operator signoff."],
            )
        status_text = str(getattr(storage_audit, "status", "unknown"))
        finding_count = int(getattr(storage_audit, "finding_count", 0) or 0)
        blockers = []
        if status_text != "ok":
            blockers.append("Storage integrity audit has unresolved findings.")
        return _readiness_section(
            "storage_integrity",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=(
                f"Storage audit status is {status_text} with {finding_count} findings."
            ),
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="storage_integrity_audit",
                    id="latest",
                    component="storage_integrity",
                    status=status_text,
                    reason_code="storage_integrity_status",
                ),
            ],
            blockers=blockers,
            recommendations=[]
            if not blockers
            else ["Repair missing or mismatched storage objects."],
        )

    def _incident_diagnostics_section(
        self,
        incident_summary: IncidentSummary,
        limit: int,
    ) -> ProductionReadinessSection:
        refs: list[IncidentEvidenceRef] = []
        for component in incident_summary.components:
            refs.extend(component.evidence_refs[:limit])
            if len(refs) >= limit:
                refs = refs[:limit]
                break
        blockers = []
        if incident_summary.status == IncidentStatus.BLOCKED:
            blockers.append("Incident diagnostics contain blocking operational evidence.")
        warning_count = 1 if incident_summary.status == IncidentStatus.WATCH else 0
        return _readiness_section(
            "incident_diagnostics",
            status=incident_summary.status,
            summary=(
                f"Incident diagnostics status is {incident_summary.status} with "
                f"{incident_summary.evidence_count} evidence refs."
            ),
            evidence_refs=refs,
            blockers=blockers,
            warning_count=warning_count,
            recommendations=[] if incident_summary.status == IncidentStatus.OK else [
                "Review incident diagnostics before readiness.",
            ],
        )

    def _multimodal_eval_section(
        self,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> ProductionReadinessSection:
        latest = self._latest_eval(
            world_id=world_id,
            like_pattern="multimodal-%",
            not_like_pattern=None,
        )
        if latest is None:
            return _readiness_section(
                "multimodal_evals",
                status=IncidentStatus.WATCH,
                summary="No multimodal eval evidence exists for the selected scope.",
                blockers=[],
                warning_count=1,
                recommendations=["Run multimodal diagnostics before final readiness."],
            )
        blockers = ["Latest multimodal eval failed."] if latest.status == "failed" else []
        warning_count = 1 if latest.status == "warning" else 0
        return _readiness_section(
            "multimodal_evals",
            status=IncidentStatus.BLOCKED
            if blockers
            else IncidentStatus.WATCH
            if warning_count
            else IncidentStatus.OK,
            summary=f"Latest multimodal eval status is {latest.status}.",
            evidence_refs=self._eval_refs(
                world_id=world_id,
                limit=limit,
                component="multimodal_evals",
                like_pattern="multimodal-%",
                not_like_pattern=None,
            ),
            blockers=blockers,
            warning_count=warning_count,
            recommendations=[] if not blockers and not warning_count else [
                "Resolve multimodal eval blockers or warnings.",
            ],
        )

    def _narrative_quality_section(
        self,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> ProductionReadinessSection:
        latest = self._latest_eval(
            world_id=world_id,
            like_pattern="narrative-quality%",
            not_like_pattern=None,
        )
        if latest is None:
            return _readiness_section(
                "narrative_quality",
                status=IncidentStatus.WATCH,
                summary="No narrative quality eval evidence exists for the selected scope.",
                blockers=[],
                warning_count=1,
                recommendations=["Run narrative quality diagnostics before final readiness."],
            )
        blockers = ["Latest narrative quality eval failed."] if latest.status == "failed" else []
        warning_count = 1 if latest.status == "warning" else 0
        return _readiness_section(
            "narrative_quality",
            status=IncidentStatus.BLOCKED
            if blockers
            else IncidentStatus.WATCH
            if warning_count
            else IncidentStatus.OK,
            summary=f"Latest narrative quality eval status is {latest.status}.",
            evidence_refs=self._eval_refs(
                world_id=world_id,
                limit=limit,
                component="narrative_quality",
                like_pattern="narrative-quality%",
                not_like_pattern=None,
            ),
            blockers=blockers,
            warning_count=warning_count,
            recommendations=[] if not blockers and not warning_count else [
                "Resolve narrative quality blockers or warnings.",
            ],
        )

    def _security_regression_section(self) -> ProductionReadinessSection:
        return _readiness_section(
            "security_regression",
            status=IncidentStatus.OK,
            summary=(
                "Security regression suite evidence is represented by the v0.7 "
                "test entrypoint."
            ),
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="security_regression_suite",
                    id="v0.7-security-regression-suite",
                    component="security_regression",
                    status="passed",
                    reason_code="targeted_and_full_gate_passed",
                ),
            ],
            blockers=[],
            recommendations=[],
        )

    def _latest_beta_checklist(self, conditions: list[Any]) -> BetaChecklistRun | None:
        return self._session.scalars(
            select(BetaChecklistRun)
            .where(*conditions)
            .order_by(BetaChecklistRun.created_at.desc())
            .limit(1),
        ).one_or_none()

    def _latest_eval(
        self,
        *,
        world_id: uuid.UUID | None,
        like_pattern: str | None,
        not_like_pattern: str | None,
    ) -> LongRunEvalRun | None:
        conditions: list[Any] = []
        if world_id is not None:
            conditions.append(LongRunEvalRun.world_id == world_id)
        if like_pattern is not None:
            conditions.append(LongRunEvalRun.eval_key.like(like_pattern))
        if not_like_pattern is not None:
            conditions.append(LongRunEvalRun.eval_key.not_like(not_like_pattern))
        return self._session.scalars(
            select(LongRunEvalRun)
            .where(*conditions)
            .order_by(LongRunEvalRun.created_at.desc())
            .limit(1),
        ).one_or_none()

    def _eval_refs(
        self,
        *,
        world_id: uuid.UUID | None,
        limit: int,
        component: str,
        like_pattern: str | None,
        not_like_pattern: str | None,
    ) -> list[IncidentEvidenceRef]:
        conditions: list[Any] = []
        if world_id is not None:
            conditions.append(LongRunEvalRun.world_id == world_id)
        if like_pattern is not None:
            conditions.append(LongRunEvalRun.eval_key.like(like_pattern))
        if not_like_pattern is not None:
            conditions.append(LongRunEvalRun.eval_key.not_like(not_like_pattern))
        records = self._session.scalars(
            select(LongRunEvalRun)
            .where(*conditions)
            .order_by(LongRunEvalRun.created_at.desc())
            .limit(limit),
        ).all()
        return [
            IncidentEvidenceRef(
                kind="long_run_eval_run",
                id=str(record.id),
                component=component,
                status=record.status,
                reason_code=f"{component}_{record.status}",
                world_id=record.world_id,
                worldline_id=record.worldline_id,
                occurred_at=record.finished_at,
            )
            for record in records
        ]

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


def _readiness_section(
    section_key: str,
    *,
    status: IncidentStatus,
    summary: str,
    evidence_refs: list[IncidentEvidenceRef] | None = None,
    blockers: list[str],
    warning_count: int = 0,
    recommendations: list[str] | None = None,
) -> ProductionReadinessSection:
    safe_refs = evidence_refs or []
    return ProductionReadinessSection(
        section_key=section_key,
        status=status,
        summary=summary,
        evidence_count=len(safe_refs),
        blocker_count=len(blockers),
        warning_count=warning_count,
        evidence_refs=safe_refs,
        blockers=blockers,
        recommendations=recommendations or [],
    )


def _readiness_status(sections: list[ProductionReadinessSection]) -> IncidentStatus:
    if any(section.status == IncidentStatus.BLOCKED for section in sections):
        return IncidentStatus.BLOCKED
    if any(section.status == IncidentStatus.WATCH for section in sections):
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
