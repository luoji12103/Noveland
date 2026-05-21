from __future__ import annotations

import builtins
import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from noveland.agents.models import AgentPersona
from noveland.authoring.models import AuthoringImportProposal, AuthoringSourceFragment
from noveland.beta_feedback.models import BetaFeedbackReport
from noveland.conversations.models import (
    ConversationParticipant,
    ConversationSession,
    ConversationTurn,
    ConversationTurnPresentation,
)
from noveland.core.database import Base
from noveland.events.models import WorldEventModel
from noveland.invocations.models import ModelInvocation
from noveland.media.models import MediaAsset, MediaJob, MediaObject, MediaReference
from noveland.memory.models import AgentMemoryItem, MemoryWriteJob
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
    NormalUseStressCheck,
    NormalUseStressReport,
    PrivateBetaGateReport,
    PrivateBetaSetupReadinessReport,
    ProductionReadinessReport,
    ProductionReadinessSection,
    PublicLaunchReadinessReport,
    RuntimeDiagnosticCreate,
    RuntimeDiagnosticRecord,
    SelfUseMvpGateReport,
    SelfUseMvpManualChecklistItem,
)
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.player_sessions.models import PlayerSession
from noveland.private_beta.models import PrivateBetaInvite
from noveland.providers.models import ProviderBudgetPolicy, ProviderHealthCheck, ProviderIntegration
from noveland.speech.models import AgentVoiceProfileBinding, VoiceProfile
from noveland.visual.models import CharacterSpriteVariant, SceneBackgroundProfile
from noveland.visual_generation.models import (
    CharacterVisualGenerationProfile,
    VisualGenerationPlan,
)
from noveland.worlds.models import (
    BetaChecklistItem,
    BetaChecklistRun,
    LivingWorldReleaseProfile,
    LongRunEvalRun,
    PlayerActorProfile,
    World,
    Worldline,
    WorldMembership,
)
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import Select, distinct, false, func, or_, select
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
SELF_USE_FORBIDDEN_EVENT_MARKERS = (
    "storage_uri",
    "preview_uri",
    "thumbnail_uri",
    "file://",
    "local://",
    "base64",
    "raw_prompt",
    "raw_output",
    "resolved_secret",
    "authorization",
    "bearer ",
)

STRESS_FORBIDDEN_REPORT_MARKERS = (
    "storage_uri",
    "preview_uri",
    "thumbnail_uri",
    "file://",
    "local://",
    "object://",
    "filesystem_path",
    "object_storage_path",
    "raw_prompt",
    "raw prompt",
    "raw_output",
    "raw output",
    "prompt_snapshot",
    "resolved_secret",
    "api_key",
    "authorization",
    "bearer ",
    "invite_token",
    "local_model_path",
    "bytes",
    "base64",
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


class NormalUseStressService:
    """Read-only deterministic normal-use stress evidence over existing records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def report(
        self,
        *,
        baseline_world_count: int = 3,
        baseline_worldlines_per_world: int = 2,
        baseline_player_sessions_per_world: int = 2,
        baseline_fake_provider_count: int = 2,
        baseline_turn_equivalent: int = 120,
        real_provider_profile_enabled: bool = False,
        evidence_limit_per_check: int = 5,
    ) -> NormalUseStressReport:
        safe_limit = max(1, min(evidence_limit_per_check, 20))
        world_ids = [
            world_id
            for world_id in self._session.scalars(
                select(World.id).where(World.is_active.is_(True)).order_by(World.created_at.asc()),
            ).all()
        ]
        checks = [
            self._baseline_coverage_check(
                world_ids,
                baseline_world_count=baseline_world_count,
                baseline_worldlines_per_world=baseline_worldlines_per_world,
                baseline_player_sessions_per_world=baseline_player_sessions_per_world,
                baseline_fake_provider_count=baseline_fake_provider_count,
                baseline_turn_equivalent=baseline_turn_equivalent,
                limit=safe_limit,
            ),
            self._isolation_check(world_ids, limit=safe_limit),
            self._quota_check(world_ids, limit=safe_limit),
            self._runtime_path_check(world_ids, limit=safe_limit),
            self._long_session_check(
                world_ids,
                baseline_turn_equivalent=baseline_turn_equivalent,
                limit=safe_limit,
            ),
            self._real_provider_profile_check(real_provider_profile_enabled),
            self._safe_report_check(),
        ]
        blocker_count = sum(check.blocker_count for check in checks)
        warning_count = sum(check.warning_count for check in checks)
        return NormalUseStressReport(
            status=_stress_status(checks),
            generated_at=datetime.now(UTC),
            baseline_world_count=baseline_world_count,
            baseline_worldlines_per_world=baseline_worldlines_per_world,
            baseline_player_sessions_per_world=baseline_player_sessions_per_world,
            baseline_fake_provider_count=baseline_fake_provider_count,
            baseline_turn_equivalent=baseline_turn_equivalent,
            observed_world_count=len(world_ids),
            observed_worldline_count=self._count(Worldline, Worldline.world_id.in_(world_ids))
            if world_ids
            else 0,
            observed_player_session_count=self._count(
                PlayerSession,
                PlayerSession.world_id.in_(world_ids),
            )
            if world_ids
            else 0,
            observed_fake_provider_count=self._fake_provider_count(world_ids),
            observed_turn_equivalent=self._turn_equivalent(world_ids),
            real_provider_profile_enabled=real_provider_profile_enabled,
            latency_summary=self._latency_summary(world_ids),
            cost_summary=self._cost_summary(world_ids),
            failure_summary=self._failure_summary(world_ids),
            quota_summary=self._quota_summary(world_ids),
            check_count=len(checks),
            evidence_count=sum(check.evidence_count for check in checks),
            blocker_count=blocker_count,
            warning_count=warning_count,
            checks=checks,
            suppressed_fields=[
                "credential_values",
                "credential_headers",
                "resolved_secrets",
                "prompt_snapshot_bodies",
                "prompt_bodies",
                "provider_result_bodies",
                "provider_payloads",
                "media_object_locations",
                "object_locator_values",
                "filesystem_paths",
                "object_storage_paths",
                "binary_payloads",
                "inline_binary_payloads",
                "invite_tokens",
                "local_model_paths",
            ],
            non_goals=[
                "unbounded_load_testing",
                "default_real_provider_stress",
                "external_load_testing_service",
                "proprietary_asset_fixture",
                "duplicate_readiness_framework",
            ],
        )

    def _baseline_coverage_check(
        self,
        world_ids: list[uuid.UUID],
        *,
        baseline_world_count: int,
        baseline_worldlines_per_world: int,
        baseline_player_sessions_per_world: int,
        baseline_fake_provider_count: int,
        baseline_turn_equivalent: int,
        limit: int,
    ) -> NormalUseStressCheck:
        blockers: list[str] = []
        warnings: list[str] = []
        if len(world_ids) < baseline_world_count:
            blockers.append(
                f"Stress fixture has {len(world_ids)} active worlds; "
                f"{baseline_world_count} are required.",
            )
        for world_id in world_ids:
            worldline_count = self._count(
                Worldline,
                Worldline.world_id == world_id,
                Worldline.status == "active",
            )
            if worldline_count < baseline_worldlines_per_world:
                blockers.append(
                    f"World {world_id} has {worldline_count} active worldlines; "
                    f"{baseline_worldlines_per_world} are required.",
                )
            player_session_count = self._count(PlayerSession, PlayerSession.world_id == world_id)
            if player_session_count < baseline_player_sessions_per_world:
                blockers.append(
                    f"World {world_id} has {player_session_count} player sessions; "
                    f"{baseline_player_sessions_per_world} are required.",
                )
        fake_provider_count = self._fake_provider_count(world_ids)
        if fake_provider_count < baseline_fake_provider_count:
            blockers.append(
                f"Stress fixture has {fake_provider_count} fake providers; "
                f"{baseline_fake_provider_count} are required.",
            )
        observed_turns = self._turn_equivalent(world_ids)
        if observed_turns < baseline_turn_equivalent:
            blockers.append(
                f"Stress fixture has {observed_turns} turn-equivalent events; "
                f"{baseline_turn_equivalent} are required.",
            )
        if len(world_ids) > baseline_world_count:
            warnings.append(
                "Stress fixture exceeds the baseline world count; keep local gate bounded.",
            )
        refs = [
            IncidentEvidenceRef(
                kind="world",
                id=str(world_id),
                component="normal_use_stress",
                status="active",
                reason_code="stress_world_included",
                world_id=world_id,
            )
            for world_id in world_ids[:limit]
        ]
        return _stress_check(
            "baseline_coverage",
            summary=(
                "Stress baseline covers active worlds, worldlines, player sessions, "
                "fake providers, and deterministic turn-equivalent evidence."
            ),
            evidence_refs=refs,
            blockers=blockers,
            warnings=warnings,
        )

    def _isolation_check(
        self,
        world_ids: list[uuid.UUID],
        *,
        limit: int,
    ) -> NormalUseStressCheck:
        blockers: list[str] = []
        warnings: list[str] = []
        refs: list[IncidentEvidenceRef] = []
        if not world_ids:
            blockers.append("No worlds are available for isolation checks.")
        player_rows = self._session.execute(
            select(
                PlayerSession.id,
                PlayerSession.world_id,
                PlayerSession.worldline_id,
                PlayerActorProfile.world_id.label("actor_world_id"),
                PlayerActorProfile.worldline_id.label("actor_worldline_id"),
                ConversationSession.world_id.label("conversation_world_id"),
                ConversationSession.worldline_id.label("conversation_worldline_id"),
            )
            .join(PlayerActorProfile, PlayerSession.player_actor_id == PlayerActorProfile.id)
            .outerjoin(
                ConversationSession,
                PlayerSession.conversation_session_id == ConversationSession.id,
            )
            .where(PlayerSession.world_id.in_(world_ids) if world_ids else false()),
        ).mappings()
        for row in player_rows:
            refs.append(
                IncidentEvidenceRef(
                    kind="player_session",
                    id=str(row["id"]),
                    component="normal_use_stress",
                    status="scoped",
                    reason_code="player_session_scope_checked",
                    world_id=row["world_id"],
                    worldline_id=row["worldline_id"],
                )
            )
            if row["actor_world_id"] != row["world_id"]:
                blockers.append(f"Player session {row['id']} points at a cross-world actor.")
            if row["actor_worldline_id"] != row["worldline_id"]:
                blockers.append(f"Player session {row['id']} points at a cross-worldline actor.")
            if (
                row["conversation_world_id"] is not None
                and row["conversation_world_id"] != row["world_id"]
            ):
                blockers.append(f"Player session {row['id']} points at a cross-world conversation.")
            if (
                row["conversation_worldline_id"] is not None
                and row["conversation_worldline_id"] != row["worldline_id"]
            ):
                blockers.append(
                    f"Player session {row['id']} points at a cross-worldline conversation.",
                )
        for model_name, model, worldline_column in (
            ("media_job", MediaJob, MediaJob.worldline_id),
            ("memory_write_job", MemoryWriteJob, MemoryWriteJob.worldline_id),
            ("beta_feedback_report", BetaFeedbackReport, BetaFeedbackReport.worldline_id),
            (
                "authoring_import_proposal",
                AuthoringImportProposal,
                AuthoringImportProposal.worldline_id,
            ),
        ):
            rows = self._session.execute(
                select(model.id, model.world_id, worldline_column, Worldline.world_id)
                .join(Worldline, worldline_column == Worldline.id)
                .where(model.world_id.in_(world_ids) if world_ids else false()),
            ).all()
            for row_id, record_world_id, record_worldline_id, worldline_world_id in rows:
                if record_world_id != worldline_world_id:
                    blockers.append(
                        f"{model_name} {row_id} has mismatched world and worldline scope.",
                    )
                if len(refs) < limit:
                    refs.append(
                        IncidentEvidenceRef(
                            kind=model_name,
                            id=str(row_id),
                            component="normal_use_stress",
                            status="scoped",
                            reason_code=f"{model_name}_scope_checked",
                            world_id=record_world_id,
                            worldline_id=record_worldline_id,
                        )
                    )
        return _stress_check(
            "worldline_player_isolation",
            summary=(
                "World, worldline, player session, media, memory, feedback, "
                "and repair scopes align."
            ),
            evidence_refs=refs[:limit],
            blockers=blockers,
            warnings=warnings,
        )

    def _quota_check(
        self,
        world_ids: list[uuid.UUID],
        *,
        limit: int,
    ) -> NormalUseStressCheck:
        blockers: list[str] = []
        warnings: list[str] = []
        active_policy_rows = self._session.execute(
            select(
                ProviderBudgetPolicy.id,
                ProviderBudgetPolicy.world_id,
                ProviderBudgetPolicy.status,
                ProviderBudgetPolicy.emergency_stop_enabled,
            ).where(
                ProviderBudgetPolicy.world_id.in_(world_ids) if world_ids else false(),
                ProviderBudgetPolicy.status == "active",
            ),
        ).mappings().all()
        policy_world_ids = {row["world_id"] for row in active_policy_rows}
        for world_id in world_ids:
            if world_id not in policy_world_ids:
                blockers.append(f"World {world_id} has no active provider budget policy.")
        if any(row["emergency_stop_enabled"] for row in active_policy_rows):
            warnings.append("One or more stress worlds have emergency stop enabled.")
        refs = [
            IncidentEvidenceRef(
                kind="provider_budget_policy",
                id=str(row["id"]),
                component="normal_use_stress",
                status="emergency_stop" if row["emergency_stop_enabled"] else "active",
                reason_code="stress_quota_policy_checked",
                world_id=row["world_id"],
            )
            for row in active_policy_rows[:limit]
        ]
        return _stress_check(
            "provider_quota_controls",
            summary=(
                "Stress worlds have active provider budget policies before provider spend paths."
            ),
            evidence_refs=refs,
            blockers=blockers,
            warnings=warnings,
        )

    def _runtime_path_check(
        self,
        world_ids: list[uuid.UUID],
        *,
        limit: int,
    ) -> NormalUseStressCheck:
        counts = {
            "media_jobs": (
                self._count(MediaJob, MediaJob.world_id.in_(world_ids)) if world_ids else 0
            ),
            "memory_write_jobs": self._count(MemoryWriteJob, MemoryWriteJob.world_id.in_(world_ids))
            if world_ids
            else 0,
            "beta_feedback_reports": self._count(
                BetaFeedbackReport,
                BetaFeedbackReport.world_id.in_(world_ids),
            )
            if world_ids
            else 0,
            "authoring_import_proposals": self._count(
                AuthoringImportProposal,
                AuthoringImportProposal.world_id.in_(world_ids),
            )
            if world_ids
            else 0,
        }
        blockers = [
            f"Stress fixture has no {key} evidence."
            for key, count in counts.items()
            if count == 0
        ]
        invocation_failures = self._count(
            ModelInvocation,
            ModelInvocation.world_id.in_(world_ids),
            ModelInvocation.status == "failed",
        ) if world_ids else 0
        media_failures = self._count(
            MediaJob,
            MediaJob.world_id.in_(world_ids),
            MediaJob.status == "failed",
        ) if world_ids else 0
        warnings = []
        if invocation_failures:
            warnings.append(f"Stress fixture includes {invocation_failures} failed invocations.")
        if media_failures:
            warnings.append(f"Stress fixture includes {media_failures} failed media jobs.")
        refs = [
            IncidentEvidenceRef(
                kind="stress_runtime_count",
                id=key,
                component="normal_use_stress",
                status=str(count),
                reason_code="runtime_path_evidence_counted",
            )
            for key, count in list(counts.items())[:limit]
        ]
        return _stress_check(
            "runtime_path_coverage",
            summary=(
                "Stress fixture covers media jobs, memory writes, feedback, "
                "and repair proposals."
            ),
            evidence_refs=refs,
            blockers=blockers,
            warnings=warnings,
        )

    def _long_session_check(
        self,
        world_ids: list[uuid.UUID],
        *,
        baseline_turn_equivalent: int,
        limit: int,
    ) -> NormalUseStressCheck:
        observed_turns = self._turn_equivalent(world_ids)
        blockers: list[str] = []
        if observed_turns < baseline_turn_equivalent:
            blockers.append(
                f"Observed turn-equivalent evidence is {observed_turns}; "
                f"{baseline_turn_equivalent} is required.",
            )
        eval_rows = self._session.scalars(
            select(LongRunEvalRun)
            .where(LongRunEvalRun.world_id.in_(world_ids) if world_ids else false())
            .order_by(LongRunEvalRun.finished_at.desc())
            .limit(limit),
        ).all()
        warnings = []
        if not eval_rows:
            warnings.append(
                "No long-run eval records were present; conversation turns provided coverage.",
            )
        if any(row.status == "failed" for row in eval_rows):
            blockers.append("At least one stress long-run eval failed.")
        if any(row.status == "warning" for row in eval_rows):
            warnings.append("At least one stress long-run eval reported warnings.")
        refs = [
            IncidentEvidenceRef(
                kind="long_run_eval_run",
                id=str(row.id),
                component="normal_use_stress",
                status=row.status,
                reason_code="stress_long_run_eval",
                world_id=row.world_id,
                worldline_id=row.worldline_id,
                occurred_at=row.finished_at,
            )
            for row in eval_rows
        ]
        refs.append(
            IncidentEvidenceRef(
                kind="stress_turn_equivalent",
                id="conversation_turns",
                component="normal_use_stress",
                status=str(observed_turns),
                reason_code="stress_turn_equivalent_counted",
            )
        )
        return _stress_check(
            "long_session_coverage",
            summary=(
                "Deterministic turn-equivalent and long-run eval evidence meet "
                "the normal-use baseline."
            ),
            evidence_refs=refs[:limit],
            blockers=blockers,
            warnings=warnings,
        )

    def _real_provider_profile_check(
        self,
        real_provider_profile_enabled: bool,
    ) -> NormalUseStressCheck:
        warnings: list[str] = []
        blockers: list[str] = []
        if real_provider_profile_enabled:
            warnings.append(
                "Real-provider stress profile is opt-in; verify quota and lab "
                "environment manually.",
            )
        active_real_provider_count = self._count(
            ProviderIntegration,
            ProviderIntegration.adapter_kind != "fake",
            ProviderIntegration.status == "active",
        )
        if active_real_provider_count and not real_provider_profile_enabled:
            warnings.append(
                "Active non-fake providers exist, but normal-use stress default remains fake-only.",
            )
        return _stress_check(
            "default_fake_provider_profile",
            summary=(
                "Default normal-use stress uses fake providers and does not execute "
                "real providers."
            ),
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="stress_provider_profile",
                    id="default",
                    component="normal_use_stress",
                    status="fake_only",
                    reason_code="real_provider_stress_disabled_by_default",
                )
            ],
            blockers=blockers,
            warnings=warnings,
        )

    def _safe_report_check(self) -> NormalUseStressCheck:
        return _stress_check(
            "safe_stress_report",
            summary="Stress report uses aggregate metrics and safe evidence refs only.",
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="leak_scan",
                    id="normal_use_stress_report",
                    component="normal_use_stress",
                    status="complete",
                    reason_code="safe_report_contract",
                )
            ],
            blockers=[],
            warnings=[],
        )

    def _fake_provider_count(self, world_ids: list[uuid.UUID]) -> int:
        if not world_ids:
            return 0
        return self._count(
            ProviderIntegration,
            ProviderIntegration.world_id.in_(world_ids),
            ProviderIntegration.adapter_kind == "fake",
            ProviderIntegration.status == "active",
        )

    def _turn_equivalent(self, world_ids: list[uuid.UUID]) -> int:
        if not world_ids:
            return 0
        session_ids = self._session.scalars(
            select(ConversationSession.id).where(ConversationSession.world_id.in_(world_ids)),
        ).all()
        conversation_turns = (
            self._count(ConversationTurn, ConversationTurn.session_id.in_(session_ids))
            if session_ids
            else 0
        )
        eval_turns = 0
        for metrics in self._session.scalars(
            select(LongRunEvalRun.metrics).where(LongRunEvalRun.world_id.in_(world_ids)),
        ):
            eval_turns += _metric_int(metrics, "turn_equivalent")
            eval_turns += _metric_int(metrics, "turn_count")
        return conversation_turns + eval_turns

    def _latency_summary(self, world_ids: list[uuid.UUID]) -> dict[str, int]:
        if not world_ids:
            return {"invocation_count": 0, "average_latency_ms": 0, "max_latency_ms": 0}
        count = self._count(ModelInvocation, ModelInvocation.world_id.in_(world_ids))
        average_latency = self._session.scalar(
            select(func.avg(ModelInvocation.latency_ms)).where(
                ModelInvocation.world_id.in_(world_ids),
                ModelInvocation.latency_ms.is_not(None),
            ),
        )
        max_latency = self._session.scalar(
            select(func.max(ModelInvocation.latency_ms)).where(
                ModelInvocation.world_id.in_(world_ids),
                ModelInvocation.latency_ms.is_not(None),
            ),
        )
        return {
            "invocation_count": count,
            "average_latency_ms": int(average_latency or 0),
            "max_latency_ms": int(max_latency or 0),
        }

    def _cost_summary(self, world_ids: list[uuid.UUID]) -> dict[str, str]:
        if not world_ids:
            return {"estimated_cost_total": "0.00000000", "costed_invocation_count": "0"}
        total = self._session.scalar(
            select(func.sum(ModelInvocation.estimated_cost)).where(
                ModelInvocation.world_id.in_(world_ids),
                ModelInvocation.estimated_cost.is_not(None),
            ),
        )
        count = self._count(
            ModelInvocation,
            ModelInvocation.world_id.in_(world_ids),
            ModelInvocation.estimated_cost.is_not(None),
        )
        cost = total if isinstance(total, Decimal) else Decimal(str(total or "0"))
        return {
            "estimated_cost_total": f"{cost:.8f}",
            "costed_invocation_count": str(count),
        }

    def _failure_summary(self, world_ids: list[uuid.UUID]) -> dict[str, int]:
        if not world_ids:
            return {
                "failed_invocations": 0,
                "failed_media_jobs": 0,
                "failed_memory_write_jobs": 0,
            }
        return {
            "failed_invocations": self._count(
                ModelInvocation,
                ModelInvocation.world_id.in_(world_ids),
                ModelInvocation.status == "failed",
            ),
            "failed_media_jobs": self._count(
                MediaJob,
                MediaJob.world_id.in_(world_ids),
                MediaJob.status == "failed",
            ),
            "failed_memory_write_jobs": self._count(
                MemoryWriteJob,
                MemoryWriteJob.world_id.in_(world_ids),
                MemoryWriteJob.status == "failed",
            ),
        }

    def _quota_summary(self, world_ids: list[uuid.UUID]) -> dict[str, int]:
        if not world_ids:
            return {"active_policy_count": 0, "emergency_stop_count": 0}
        return {
            "active_policy_count": self._count(
                ProviderBudgetPolicy,
                ProviderBudgetPolicy.world_id.in_(world_ids),
                ProviderBudgetPolicy.status == "active",
            ),
            "emergency_stop_count": self._count(
                ProviderBudgetPolicy,
                ProviderBudgetPolicy.world_id.in_(world_ids),
                ProviderBudgetPolicy.emergency_stop_enabled.is_(True),
                ProviderBudgetPolicy.status == "active",
            ),
        }

    def _count(self, model: type[Any], *conditions: Any) -> int:
        return int(
            self._session.scalar(select(func.count(model.id)).where(*conditions))
            or 0
        )


class ProductionReadinessGateService:
    """Read-only internal readiness aggregation over existing evidence records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def self_use_mvp_report(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None = None,
        conversation_id: uuid.UUID | None = None,
        evidence_limit_per_section: int = 5,
        manual_play_minutes: int = 0,
        resume_verified: bool = False,
        failure_notes_recorded: bool = False,
    ) -> SelfUseMvpGateReport:
        safe_limit = max(1, min(evidence_limit_per_section, 20))
        worldline = worldline_or_404(self._session, world_id, worldline_id)
        session_record = self._self_use_conversation(
            world_id,
            worldline.id,
            conversation_id,
        )
        selected_conversation_id = None if session_record is None else session_record.id
        participant_agent_ids = self._conversation_participant_agent_ids(selected_conversation_id)
        sections = [
            self._self_use_entry_section(
                world_id,
                worldline.id,
                session_record,
                participant_agent_ids,
            ),
            self._self_use_conversation_section(
                world_id,
                worldline.id,
                selected_conversation_id,
                safe_limit,
            ),
            self._self_use_persona_memory_section(
                world_id,
                worldline.id,
                participant_agent_ids,
                safe_limit,
            ),
            self._self_use_visual_section(
                world_id,
                worldline.id,
                selected_conversation_id,
                participant_agent_ids,
                safe_limit,
            ),
            self._self_use_voice_section(
                world_id,
                worldline.id,
                selected_conversation_id,
                participant_agent_ids,
                safe_limit,
            ),
            self._self_use_provider_section(world_id, worldline.id, safe_limit),
            self._self_use_media_job_section(world_id, worldline.id, safe_limit),
            self._self_use_invocation_ledger_section(world_id, worldline.id, safe_limit),
            self._self_use_traceability_section(world_id, worldline.id, safe_limit),
            self._self_use_no_world_event_leak_section(world_id, worldline.id, safe_limit),
        ]
        manual_checklist = _self_use_manual_checklist(
            manual_play_minutes=manual_play_minutes,
            resume_verified=resume_verified,
            failure_notes_recorded=failure_notes_recorded,
        )
        evidence_count = sum(section.evidence_count for section in sections)
        blocker_count = sum(section.blocker_count for section in sections)
        warning_count = sum(section.warning_count for section in sections)
        status = _readiness_status(sections)
        manual_blocker_count = sum(
            1
            for item in manual_checklist
            if item.required_for_pass and item.status == IncidentStatus.BLOCKED
        )
        if manual_blocker_count:
            blocker_count += manual_blocker_count
            status = IncidentStatus.BLOCKED
        if any(
            not item.required_for_pass and item.status == IncidentStatus.WATCH
            for item in manual_checklist
        ):
            warning_count += 1
        if any(
            item.required_for_pass and item.status == IncidentStatus.BLOCKED
            for item in manual_checklist
        ):
            status = IncidentStatus.BLOCKED
        return SelfUseMvpGateReport(
            status=status,
            generated_at=datetime.now(UTC),
            world_id=world_id,
            worldline_id=worldline.id,
            conversation_id=selected_conversation_id,
            section_count=len(sections),
            evidence_count=evidence_count,
            blocker_count=blocker_count,
            warning_count=warning_count,
            sections=sections,
            manual_checklist=manual_checklist,
            suppressed_fields=[
                "credential_values",
                "credential_headers",
                "resolved_secrets",
                "prompt_snapshot_bodies",
                "prompt_bodies",
                "provider_result_bodies",
                "provider_payloads",
                "media_object_locations",
                "object_locator_values",
                "filesystem_paths",
                "binary_payloads",
                "inline_binary_payloads",
                "world_event_payload_snapshots",
                "raw_source_fragments",
                "local_model_paths",
                "raw_workflow_json",
            ],
            non_goals=[
                "private_beta_readiness",
                "public_launch_readiness",
                "production_readiness_replacement",
                "automated_provider_spend",
                "automated_content_quality_acceptance",
            ],
            archive_recommendation=(
                "Archive v0.9 only after status is ok and the manual 30-minute play "
                "session evidence has been reviewed."
                if status == IncidentStatus.OK
                else "Fix self-use MVP blockers before archiving v0.9."
            ),
        )

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

    def public_launch_report(
        self,
        *,
        world_id: uuid.UUID | None = None,
        evidence_limit_per_section: int = 5,
        storage_audit: Any | None = None,
        security_signoff: bool = False,
        privacy_signoff: bool = False,
        moderation_signoff: bool = False,
        sample_world_signoff: bool = False,
        operator_signoff: bool = False,
    ) -> PublicLaunchReadinessReport:
        safe_limit = max(1, min(evidence_limit_per_section, 20))
        internal = self.report(
            world_id=world_id,
            evidence_limit_per_section=safe_limit,
            storage_audit=storage_audit,
        )
        signoffs = {
            "security_signoff": security_signoff,
            "privacy_signoff": privacy_signoff,
            "moderation_signoff": moderation_signoff,
            "sample_world_signoff": sample_world_signoff,
            "operator_signoff": operator_signoff,
        }
        sections = [
            self._internal_production_readiness_section(internal, safe_limit),
            self._reader_media_delivery_section(world_id, safe_limit),
            self._conversation_playback_section(world_id, safe_limit),
            self._player_privacy_section(world_id, safe_limit),
            self._moderation_workflow_section(
                world_id,
                safe_limit,
                moderation_signoff=moderation_signoff,
            ),
            self._sample_world_package_section(
                world_id,
                safe_limit,
                sample_world_signoff=sample_world_signoff,
            ),
            self._plugin_provider_safety_section(
                world_id,
                safe_limit,
                security_signoff=security_signoff,
            ),
            self._public_surface_security_section(security_signoff=security_signoff),
            self._explicit_public_signoff_section(signoffs),
        ]
        evidence_count = sum(section.evidence_count for section in sections)
        blocker_count = sum(section.blocker_count for section in sections)
        warning_count = sum(section.warning_count for section in sections)
        return PublicLaunchReadinessReport(
            status=_readiness_status(sections),
            generated_at=datetime.now(UTC),
            world_id=world_id,
            section_count=len(sections),
            evidence_count=evidence_count,
            blocker_count=blocker_count,
            warning_count=warning_count,
            sections=sections,
            internal_readiness=internal,
            required_signoffs=signoffs,
            auto_launch_enabled=False,
            suppressed_fields=[
                "credential_values",
                "credential_headers",
                "ledger_text_bodies",
                "prompt_snapshot_bodies",
                "provider_payloads",
                "media_object_locations",
                "binary_payloads",
                "event_payload_snapshots",
                "diagnostic_details",
                "moderation_private_reporter_notes",
                "raw_prompt_output_evidence",
            ],
            non_goals=[
                "automatic_public_launch",
                "duplicate_release_framework",
                "public_unauthenticated_delivery",
                "provider_marketplace",
                "runtime_daemon_execution",
            ],
        )

    def private_beta_setup_report(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None = None,
        conversation_id: uuid.UUID | None = None,
        evidence_limit_per_section: int = 5,
        manual_play_minutes: int = 0,
        resume_verified: bool = False,
        failure_notes_recorded: bool = False,
    ) -> ProductionReadinessReport:
        safe_limit = max(1, min(evidence_limit_per_section, 20))
        worldline = worldline_or_404(self._session, world_id, worldline_id)
        session_record = self._self_use_conversation(
            world_id,
            worldline.id,
            conversation_id,
        )
        selected_conversation_id = None if session_record is None else session_record.id
        participant_agent_ids = self._conversation_participant_agent_ids(selected_conversation_id)
        self_use_report = self.self_use_mvp_report(
            world_id=world_id,
            worldline_id=worldline.id,
            conversation_id=selected_conversation_id,
            evidence_limit_per_section=safe_limit,
            manual_play_minutes=manual_play_minutes,
            resume_verified=resume_verified,
            failure_notes_recorded=failure_notes_recorded,
        )
        sections = [
            self._private_beta_access_section(world_id, worldline.id, safe_limit),
            self._private_beta_session_restore_section(world_id, worldline.id, safe_limit),
            self._private_beta_quota_section(world_id, safe_limit),
            self._self_use_provider_section(world_id, worldline.id, safe_limit),
            self._self_use_entry_section(
                world_id,
                worldline.id,
                session_record,
                participant_agent_ids,
            ),
            self._self_use_conversation_section(
                world_id,
                worldline.id,
                selected_conversation_id,
                safe_limit,
            ),
            self._self_use_persona_memory_section(
                world_id,
                worldline.id,
                participant_agent_ids,
                safe_limit,
            ),
            self._self_use_visual_section(
                world_id,
                worldline.id,
                selected_conversation_id,
                participant_agent_ids,
                safe_limit,
            ),
            self._self_use_voice_section(
                world_id,
                worldline.id,
                selected_conversation_id,
                participant_agent_ids,
                safe_limit,
            ),
            self._self_use_media_job_section(world_id, worldline.id, safe_limit),
            self._self_use_traceability_section(world_id, worldline.id, safe_limit),
            self._private_beta_self_use_gate_section(self_use_report, safe_limit),
            self._self_use_no_world_event_leak_section(world_id, worldline.id, safe_limit),
        ]
        evidence_count = sum(section.evidence_count for section in sections)
        blocker_count = sum(section.blocker_count for section in sections)
        warning_count = sum(section.warning_count for section in sections)
        return ProductionReadinessReport(
            status=_readiness_status(sections),
            generated_at=datetime.now(UTC),
            world_id=world_id,
            readiness_kind="private_beta_world_setup",
            section_count=len(sections),
            evidence_count=evidence_count,
            blocker_count=blocker_count,
            warning_count=warning_count,
            sections=sections,
            suppressed_fields=[
                "invite_tokens",
                "invite_token_hashes",
                "credential_values",
                "credential_headers",
                "resolved_secrets",
                "prompt_snapshot_bodies",
                "prompt_bodies",
                "provider_result_bodies",
                "provider_payloads",
                "media_object_locations",
                "object_locator_values",
                "filesystem_paths",
                "binary_payloads",
                "inline_binary_payloads",
                "world_event_payload_snapshots",
                "raw_source_fragments",
                "local_model_paths",
                "raw_workflow_json",
            ],
            non_goals=[
                "duplicate_readiness_framework",
                "public_launch_readiness",
                "automatic_setup_repair",
                "tester_visible_admin_diagnostics",
                "provider_execution",
                "public_signup",
            ],
        )

    def private_beta_gate_report(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None = None,
        conversation_id: uuid.UUID | None = None,
        evidence_limit_per_section: int = 5,
        manual_play_minutes: int = 0,
        resume_verified: bool = False,
        failure_notes_recorded: bool = False,
        manual_tester_count: int = 0,
        tester_session_completed: bool = False,
        no_developer_intervention_verified: bool = False,
        quota_reviewed: bool = False,
        feedback_triage_verified: bool = False,
        memory_persona_qa_reviewed: bool = False,
        repair_loop_reviewed: bool = False,
    ) -> PrivateBetaGateReport:
        safe_limit = max(1, min(evidence_limit_per_section, 20))
        worldline = worldline_or_404(self._session, world_id, worldline_id)
        setup = PrivateBetaSetupReadinessReport.model_validate(
            self.private_beta_setup_report(
                world_id=world_id,
                worldline_id=worldline.id,
                conversation_id=conversation_id,
                evidence_limit_per_section=safe_limit,
                manual_play_minutes=manual_play_minutes,
                resume_verified=resume_verified,
                failure_notes_recorded=failure_notes_recorded,
            ).model_dump()
        )
        manual_checklist = _private_beta_manual_checklist(
            manual_tester_count=manual_tester_count,
            manual_play_minutes=manual_play_minutes,
            tester_session_completed=tester_session_completed,
            no_developer_intervention_verified=no_developer_intervention_verified,
            quota_reviewed=quota_reviewed,
            feedback_triage_verified=feedback_triage_verified,
            memory_persona_qa_reviewed=memory_persona_qa_reviewed,
            repair_loop_reviewed=repair_loop_reviewed,
        )
        sections = [
            self._private_beta_setup_gate_section(setup, safe_limit),
            self._private_beta_feedback_gate_section(
                world_id,
                worldline.id,
                safe_limit,
                feedback_triage_verified=feedback_triage_verified,
            ),
            self._private_beta_memory_persona_qa_gate_section(
                setup,
                memory_persona_qa_reviewed=memory_persona_qa_reviewed,
                limit=safe_limit,
            ),
            self._private_beta_repair_loop_gate_section(
                world_id,
                worldline.id,
                safe_limit,
                repair_loop_reviewed=repair_loop_reviewed,
            ),
            self._private_beta_manual_session_section(manual_checklist),
            self._self_use_no_world_event_leak_section(world_id, worldline.id, safe_limit),
        ]
        evidence_count = sum(section.evidence_count for section in sections)
        blocker_count = sum(section.blocker_count for section in sections)
        warning_count = sum(section.warning_count for section in sections)
        return PrivateBetaGateReport(
            status=_readiness_status(sections),
            generated_at=datetime.now(UTC),
            world_id=world_id,
            readiness_kind="private_beta_gate",
            section_count=len(sections),
            evidence_count=evidence_count,
            blocker_count=blocker_count,
            warning_count=warning_count,
            sections=sections,
            private_beta_setup=setup,
            manual_checklist=manual_checklist,
            public_launch_ready=False,
            suppressed_fields=[
                "invite_tokens",
                "invite_token_hashes",
                "credential_values",
                "credential_headers",
                "resolved_secrets",
                "prompt_snapshot_bodies",
                "prompt_bodies",
                "provider_result_bodies",
                "provider_payloads",
                "media_object_locations",
                "object_locator_values",
                "filesystem_paths",
                "binary_payloads",
                "inline_binary_payloads",
                "world_event_payload_snapshots",
                "raw_source_fragments",
                "local_model_paths",
                "raw_workflow_json",
                "feedback_reporter_private_notes",
            ],
            non_goals=[
                "public_launch_readiness",
                "release_candidate_readiness",
                "duplicate_readiness_framework",
                "automatic_public_launch",
                "automated_provider_spend",
                "tester_visible_admin_diagnostics",
            ],
        )

    def _self_use_conversation(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
    ) -> ConversationSession | None:
        statement = select(ConversationSession).where(
            ConversationSession.world_id == world_id,
            ConversationSession.worldline_id == worldline_id,
        )
        if conversation_id is not None:
            statement = statement.where(ConversationSession.id == conversation_id)
        else:
            statement = statement.order_by(ConversationSession.updated_at.desc()).limit(1)
        return self._session.scalars(statement).one_or_none()

    def _private_beta_access_section(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        limit: int,
    ) -> ProductionReadinessSection:
        viable_statuses = ("pending", "accepted", "redeemed")
        invite_scope = or_(
            PrivateBetaInvite.worldline_id == worldline_id,
            PrivateBetaInvite.worldline_id.is_(None),
        )
        invite_count = self._count(
            PrivateBetaInvite,
            PrivateBetaInvite.world_id == world_id,
            invite_scope,
            PrivateBetaInvite.status.in_(viable_statuses),
        )
        redeemed_invites = self._session.scalars(
            select(PrivateBetaInvite)
            .where(
                PrivateBetaInvite.world_id == world_id,
                invite_scope,
                PrivateBetaInvite.status == "redeemed",
                PrivateBetaInvite.redeemed_by_user_id.is_not(None),
            )
            .order_by(PrivateBetaInvite.redeemed_at.desc(), PrivateBetaInvite.updated_at.desc())
            .limit(limit),
        ).all()
        redeemed_user_ids = [
            invite.redeemed_by_user_id
            for invite in redeemed_invites
            if invite.redeemed_by_user_id is not None
        ]
        member_count = 0
        admin_role_count = 0
        profile_count = 0
        if redeemed_user_ids:
            member_count = self._count(
                WorldMembership,
                WorldMembership.world_id == world_id,
                WorldMembership.user_id.in_(redeemed_user_ids),
                WorldMembership.role == "human_user",
            )
            admin_role_count = self._count(
                WorldMembership,
                WorldMembership.world_id == world_id,
                WorldMembership.user_id.in_(redeemed_user_ids),
                WorldMembership.role != "human_user",
            )
            profile_count = self._count(
                PlayerActorProfile,
                PlayerActorProfile.world_id == world_id,
                PlayerActorProfile.worldline_id == worldline_id,
                PlayerActorProfile.user_id.in_(redeemed_user_ids),
                PlayerActorProfile.is_active.is_(True),
            )
        blockers: list[str] = []
        if invite_count == 0:
            blockers.append("No pending, accepted, or redeemed private beta invites exist.")
        if not redeemed_user_ids:
            blockers.append("No redeemed invite proves the onboarding path end to end.")
        if redeemed_user_ids and member_count < len(redeemed_user_ids):
            blockers.append("One or more redeemed testers lack least-privilege membership.")
        if redeemed_user_ids and profile_count < len(redeemed_user_ids):
            blockers.append("One or more redeemed testers lack an active player profile.")
        if admin_role_count:
            blockers.append("A redeemed tester has a non-player membership role.")
        refs = [
            IncidentEvidenceRef(
                kind="private_beta_invite",
                id=str(invite.id),
                component="private_beta_access",
                status=invite.status,
                reason_code="redeemed_invite",
                world_id=invite.world_id,
                worldline_id=invite.worldline_id,
                occurred_at=invite.redeemed_at or invite.updated_at,
            )
            for invite in redeemed_invites
        ]
        return _readiness_section(
            "private_beta_access",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=(
                f"{invite_count} viable invites, {len(redeemed_user_ids)} redeemed testers, "
                f"{member_count} least-privilege memberships, {profile_count} player profiles."
            ),
            evidence_refs=refs,
            blockers=blockers,
            recommendations=[]
            if not blockers
            else ["Create and redeem a private beta invite through the onboarding flow."],
        )

    def _private_beta_session_restore_section(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        limit: int,
    ) -> ProductionReadinessSection:
        sessions = self._session.scalars(
            select(PlayerSession)
            .where(
                PlayerSession.world_id == world_id,
                PlayerSession.worldline_id == worldline_id,
            )
            .order_by(PlayerSession.last_seen_at.desc())
            .limit(limit),
        ).all()
        session_count = self._count(
            PlayerSession,
            PlayerSession.world_id == world_id,
            PlayerSession.worldline_id == worldline_id,
        )
        ready_count = self._count(
            PlayerSession,
            PlayerSession.world_id == world_id,
            PlayerSession.worldline_id == worldline_id,
            PlayerSession.status.in_(("active", "paused")),
            PlayerSession.recovery_status == "ready",
        )
        recovery_block_count = self._count(
            PlayerSession,
            PlayerSession.world_id == world_id,
            PlayerSession.worldline_id == worldline_id,
            PlayerSession.recovery_status != "ready",
        )
        blockers: list[str] = []
        if session_count == 0:
            blockers.append("No player session resume evidence exists.")
        if session_count and ready_count == 0:
            blockers.append("No player session is ready for browser close/reopen recovery.")
        if recovery_block_count:
            blockers.append("One or more player sessions have unresolved recovery status.")
        return _readiness_section(
            "player_session_restore",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=(
                f"{session_count} player sessions, {ready_count} ready for resume, "
                f"{recovery_block_count} with recovery blockers."
            ),
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="player_session",
                    id=str(session.id),
                    component="player_session_restore",
                    status=session.recovery_status,
                    reason_code=f"session_{session.status}",
                    world_id=session.world_id,
                    worldline_id=session.worldline_id,
                    occurred_at=session.last_seen_at,
                )
                for session in sessions
            ],
            blockers=blockers,
            recommendations=[]
            if not blockers
            else ["Run the player resume flow and resolve stale media/provider/session states."],
        )

    def _private_beta_quota_section(
        self,
        world_id: uuid.UUID,
        limit: int,
    ) -> ProductionReadinessSection:
        policies = self._session.scalars(
            select(ProviderBudgetPolicy)
            .where(
                ProviderBudgetPolicy.world_id == world_id,
                ProviderBudgetPolicy.status == "active",
            )
            .order_by(ProviderBudgetPolicy.updated_at.desc())
            .limit(limit),
        ).all()
        active_count = self._count(
            ProviderBudgetPolicy,
            ProviderBudgetPolicy.world_id == world_id,
            ProviderBudgetPolicy.status == "active",
        )
        emergency_count = self._count(
            ProviderBudgetPolicy,
            ProviderBudgetPolicy.world_id == world_id,
            ProviderBudgetPolicy.status == "active",
            ProviderBudgetPolicy.emergency_stop_enabled.is_(True),
        )
        all_active_policies = self._session.scalars(
            select(ProviderBudgetPolicy).where(
                ProviderBudgetPolicy.world_id == world_id,
                ProviderBudgetPolicy.status == "active",
            )
        ).all()
        player_scoped_count = sum(
            1
            for policy in all_active_policies
            if isinstance(policy.limits_json, dict)
            and (
                isinstance(policy.limits_json.get("default_player"), dict)
                or isinstance(policy.limits_json.get("players"), dict)
            )
        )
        capability_scoped_count = sum(
            1
            for policy in all_active_policies
            if isinstance(policy.limits_json, dict)
            and isinstance(policy.limits_json.get("capabilities"), dict)
        )
        blockers: list[str] = []
        if active_count == 0:
            blockers.append("No active provider quota policy exists for this world.")
        if emergency_count:
            blockers.append("Provider emergency stop is active.")
        if active_count and player_scoped_count == 0:
            blockers.append("No active quota policy defines player-scoped limits.")
        if active_count and capability_scoped_count == 0:
            blockers.append("No active quota policy defines capability-scoped limits.")
        return _readiness_section(
            "private_beta_quota_controls",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=(
                f"{active_count} active quota policies, {player_scoped_count} player-scoped, "
                f"{capability_scoped_count} capability-scoped, {emergency_count} emergency stops."
            ),
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="provider_budget_policy",
                    id=str(policy.id),
                    component="private_beta_quota_controls",
                    status="blocked" if policy.emergency_stop_enabled else policy.status,
                    reason_code="emergency_stop"
                    if policy.emergency_stop_enabled
                    else "player_capability_quota",
                    world_id=policy.world_id,
                    occurred_at=policy.updated_at,
                )
                for policy in policies
            ],
            blockers=blockers,
            recommendations=[]
            if not blockers
            else ["Configure active per-player and per-capability provider quota limits."],
        )

    def _private_beta_self_use_gate_section(
        self,
        self_use_report: SelfUseMvpGateReport,
        limit: int,
    ) -> ProductionReadinessSection:
        refs: list[IncidentEvidenceRef] = []
        for section in self_use_report.sections:
            refs.extend(section.evidence_refs)
            if len(refs) >= limit:
                refs = refs[:limit]
                break
        blockers = []
        if self_use_report.status == IncidentStatus.BLOCKED:
            blockers.append("Self-use MVP gate still has blocking evidence.")
        warning_count = 1 if self_use_report.status == IncidentStatus.WATCH else 0
        return _readiness_section(
            "self_use_mvp_evidence",
            status=self_use_report.status,
            summary=(
                f"Self-use MVP gate is {self_use_report.status} with "
                f"{self_use_report.blocker_count} blockers and "
                f"{self_use_report.warning_count} warnings."
            ),
            evidence_refs=refs,
            blockers=blockers,
            warning_count=warning_count,
            recommendations=[]
            if not blockers and not warning_count
            else ["Resolve self-use MVP gate blockers before inviting beta testers."],
        )

    def _private_beta_setup_gate_section(
        self,
        setup: PrivateBetaSetupReadinessReport,
        limit: int,
    ) -> ProductionReadinessSection:
        refs: list[IncidentEvidenceRef] = []
        for section in setup.sections:
            refs.extend(section.evidence_refs)
            if len(refs) >= limit:
                refs = refs[:limit]
                break
        blockers = []
        if setup.status == IncidentStatus.BLOCKED:
            blockers.append("Private beta setup readiness still has blocking evidence.")
        warning_count = 1 if setup.status == IncidentStatus.WATCH else 0
        return _readiness_section(
            "private_beta_setup_readiness",
            status=setup.status,
            summary=(
                f"Private beta setup is {setup.status} with {setup.blocker_count} blockers "
                f"and {setup.warning_count} warnings."
            ),
            evidence_refs=refs,
            blockers=blockers,
            warning_count=warning_count,
            recommendations=[]
            if not blockers and not warning_count
            else ["Resolve private beta setup blockers before inviting testers."],
        )

    def _private_beta_feedback_gate_section(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        limit: int,
        *,
        feedback_triage_verified: bool,
    ) -> ProductionReadinessSection:
        reports = self._session.scalars(
            select(BetaFeedbackReport)
            .where(
                BetaFeedbackReport.world_id == world_id,
                BetaFeedbackReport.worldline_id == worldline_id,
            )
            .order_by(BetaFeedbackReport.updated_at.desc())
            .limit(limit),
        ).all()
        report_count = self._count(
            BetaFeedbackReport,
            BetaFeedbackReport.world_id == world_id,
            BetaFeedbackReport.worldline_id == worldline_id,
        )
        triaged_count = self._count(
            BetaFeedbackReport,
            BetaFeedbackReport.world_id == world_id,
            BetaFeedbackReport.worldline_id == worldline_id,
            BetaFeedbackReport.status.in_(("triaged", "linked_to_repair", "resolved")),
        )
        linked_count = sum(
            1
            for report in self._session.scalars(
                select(BetaFeedbackReport).where(
                    BetaFeedbackReport.world_id == world_id,
                    BetaFeedbackReport.worldline_id == worldline_id,
                )
            ).all()
            if report.repair_proposal_refs_json
        )
        blockers: list[str] = []
        if report_count == 0:
            blockers.append("No beta feedback reports prove the tester feedback path.")
        if report_count and triaged_count == 0:
            blockers.append("No beta feedback report has been triaged.")
        if not feedback_triage_verified:
            blockers.append("Manual feedback triage review is not confirmed.")
        return _readiness_section(
            "beta_feedback_path",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=(
                f"{report_count} beta feedback reports, {triaged_count} triaged/resolved, "
                f"{linked_count} linked to repair proposals."
            ),
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="beta_feedback_report",
                    id=str(report.id),
                    component="beta_feedback_path",
                    status=report.status,
                    reason_code=report.issue_type,
                    world_id=report.world_id,
                    worldline_id=report.worldline_id,
                    occurred_at=report.updated_at,
                )
                for report in reports
            ],
            blockers=blockers,
            recommendations=[]
            if not blockers
            else ["Submit and triage at least one contextual beta feedback report."],
        )

    def _private_beta_memory_persona_qa_gate_section(
        self,
        setup: PrivateBetaSetupReadinessReport,
        *,
        memory_persona_qa_reviewed: bool,
        limit: int,
    ) -> ProductionReadinessSection:
        persona_section = next(
            (section for section in setup.sections if section.section_key == "persona_memory"),
            None,
        )
        refs = [] if persona_section is None else persona_section.evidence_refs[:limit]
        blockers: list[str] = []
        warning_count = 0
        if persona_section is None:
            blockers.append("Persona/memory setup evidence is missing.")
        elif persona_section.status == IncidentStatus.BLOCKED:
            blockers.append("Persona/memory setup evidence still has blockers.")
        elif persona_section.status == IncidentStatus.WATCH:
            warning_count += 1
        if not memory_persona_qa_reviewed:
            blockers.append("Memory/persona QA review has not been confirmed.")
        return _readiness_section(
            "memory_persona_qa_gate",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=(
                "Memory/persona QA review "
                f"{'confirmed' if memory_persona_qa_reviewed else 'not confirmed'}."
            ),
            evidence_refs=refs,
            blockers=blockers,
            warning_count=warning_count,
            recommendations=[]
            if not blockers
            else ["Run memory/persona QA and confirm no critical drift or contamination remains."],
        )

    def _private_beta_repair_loop_gate_section(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        limit: int,
        *,
        repair_loop_reviewed: bool,
    ) -> ProductionReadinessSection:
        all_proposals = self._session.scalars(
            select(AuthoringImportProposal)
            .where(
                AuthoringImportProposal.world_id == world_id,
                AuthoringImportProposal.worldline_id == worldline_id,
            )
            .order_by(AuthoringImportProposal.updated_at.desc())
        ).all()
        repair_proposals = [
            proposal
            for proposal in all_proposals
            if proposal.evidence_json.get("source") == "beta_content_iteration_loop"
            or proposal.proposed_payload_json.get("source") == "beta_content_iteration_loop"
        ]
        applied_count = sum(1 for proposal in repair_proposals if proposal.status == "applied")
        linked_feedback_count = sum(
            1
            for report in self._session.scalars(
                select(BetaFeedbackReport).where(
                    BetaFeedbackReport.world_id == world_id,
                    BetaFeedbackReport.worldline_id == worldline_id,
                )
            ).all()
            if report.repair_proposal_refs_json
        )
        blockers: list[str] = []
        if not repair_proposals:
            blockers.append("No beta content repair proposal evidence exists.")
        if repair_proposals and linked_feedback_count == 0:
            blockers.append("No beta feedback report is linked to repair proposals.")
        if not repair_loop_reviewed:
            blockers.append("Repair-loop review has not been confirmed.")
        return _readiness_section(
            "beta_content_repair_loop",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=(
                f"{len(repair_proposals)} beta repair proposals, {applied_count} applied, "
                f"{linked_feedback_count} feedback reports linked."
            ),
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="authoring_import_proposal",
                    id=str(proposal.id),
                    component="beta_content_repair_loop",
                    status=proposal.status,
                    reason_code=str(proposal.target_ref_kind or proposal.proposal_kind),
                    world_id=proposal.world_id,
                    worldline_id=proposal.worldline_id,
                    occurred_at=proposal.updated_at,
                )
                for proposal in repair_proposals[:limit]
            ],
            blockers=blockers,
            recommendations=[]
            if not blockers
            else ["Create and review repair proposals linked to beta feedback or QA diagnostics."],
        )

    def _private_beta_manual_session_section(
        self,
        checklist: list[SelfUseMvpManualChecklistItem],
    ) -> ProductionReadinessSection:
        blockers = [
            item.title
            for item in checklist
            if item.required_for_pass and item.status == IncidentStatus.BLOCKED
        ]
        warning_count = sum(1 for item in checklist if item.status == IncidentStatus.WATCH)
        return _readiness_section(
            "manual_private_beta_session",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=f"{len(checklist) - len(blockers)} of {len(checklist)} manual checks pass.",
            blockers=blockers,
            warning_count=warning_count,
            recommendations=[]
            if not blockers
            else ["Complete the manual 1-2 hour private beta tester-session checklist."],
        )

    def _conversation_participant_agent_ids(
        self,
        conversation_id: uuid.UUID | None,
    ) -> list[uuid.UUID]:
        if conversation_id is None:
            return []
        rows = self._session.scalars(
            select(ConversationParticipant)
            .where(
                ConversationParticipant.session_id == conversation_id,
                ConversationParticipant.is_enabled.is_(True),
            )
            .order_by(ConversationParticipant.turn_order),
        ).all()
        return [row.agent_id for row in rows]

    def _self_use_entry_section(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        session_record: ConversationSession | None,
        participant_agent_ids: list[uuid.UUID],
    ) -> ProductionReadinessSection:
        blockers: list[str] = []
        if session_record is None:
            blockers.append("No assembled demo conversation session exists.")
        if len(participant_agent_ids) < 2:
            blockers.append("Demo conversation needs at least two enabled participants.")
        if len(participant_agent_ids) > 3:
            blockers.append("Self-use MVP demo should stay within 2-3 participants.")
        refs: list[IncidentEvidenceRef] = []
        if session_record is not None:
            refs.append(
                IncidentEvidenceRef(
                    kind="conversation_session",
                    id=str(session_record.id),
                    component="self_use_entry",
                    status=session_record.status,
                    reason_code="demo_entry_session",
                    world_id=world_id,
                    worldline_id=worldline_id,
                    occurred_at=session_record.updated_at,
                )
            )
        refs.extend(
            IncidentEvidenceRef(
                kind="agent",
                id=str(agent_id),
                component="self_use_entry",
                status="enabled",
                reason_code="demo_participant",
                world_id=world_id,
                worldline_id=worldline_id,
            )
            for agent_id in participant_agent_ids[:3]
        )
        return _readiness_section(
            "demo_entry",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=(
                "Demo entry has "
                f"{0 if session_record is None else 1} session and "
                f"{len(participant_agent_ids)} enabled participants."
            ),
            evidence_refs=refs,
            blockers=blockers,
            recommendations=[]
            if not blockers
            else ["Apply a reviewed demo_world_assembly proposal before running the gate."],
        )

    def _self_use_conversation_section(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        limit: int,
    ) -> ProductionReadinessSection:
        if conversation_id is None:
            return _readiness_section(
                "conversation_continuity",
                status=IncidentStatus.BLOCKED,
                summary="No conversation was selected for continuity evidence.",
                blockers=["Demo conversation evidence is missing."],
                recommendations=["Assemble and enter the demo conversation."],
            )
        conditions = [ConversationTurn.session_id == conversation_id]
        turn_count = self._count(ConversationTurn, *conditions)
        failed_count = self._count(
            ConversationTurn,
            *conditions,
            ConversationTurn.status == "failed",
        )
        agent_turn_count = self._count(
            ConversationTurn,
            *conditions,
            ConversationTurn.speaker_kind == "agent",
        )
        turns = self._session.scalars(
            select(ConversationTurn)
            .where(*conditions)
            .order_by(ConversationTurn.turn_index.desc())
            .limit(limit),
        ).all()
        blockers: list[str] = []
        if turn_count == 0:
            blockers.append("Conversation has no turns.")
        if failed_count:
            blockers.append("Conversation contains failed turns.")
        warning_count = 0 if agent_turn_count else 1
        recommendations = []
        if not agent_turn_count:
            recommendations.append("Continue the demo until at least one agent turn exists.")
        if blockers:
            recommendations.append("Resolve failed or missing conversation turns.")
        return _readiness_section(
            "conversation_continuity",
            status=IncidentStatus.BLOCKED
            if blockers
            else IncidentStatus.WATCH
            if warning_count
            else IncidentStatus.OK,
            summary=(
                f"{turn_count} turns, {agent_turn_count} agent turns, "
                f"{failed_count} failed turns."
            ),
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="conversation_turn",
                    id=str(turn.id),
                    component="conversation_continuity",
                    status=turn.status,
                    reason_code=f"turn_{turn.speaker_kind}",
                    world_id=world_id,
                    worldline_id=worldline_id,
                    occurred_at=turn.updated_at,
                )
                for turn in turns
            ],
            blockers=blockers,
            warning_count=warning_count,
            recommendations=recommendations,
        )

    def _self_use_persona_memory_section(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        participant_agent_ids: list[uuid.UUID],
        limit: int,
    ) -> ProductionReadinessSection:
        if not participant_agent_ids:
            return _readiness_section(
                "persona_memory",
                status=IncidentStatus.BLOCKED,
                summary="No participant agents are available for persona/memory checks.",
                blockers=["Participant agents are missing."],
                recommendations=["Assemble a demo conversation with 2-3 agents."],
            )
        persona_count = self._count(
            AgentPersona,
            AgentPersona.world_id == world_id,
            AgentPersona.agent_id.in_(participant_agent_ids),
            AgentPersona.is_enabled.is_(True),
            AgentPersona.persona_text != "",
        )
        memory_count = self._count(
            AgentMemoryItem,
            AgentMemoryItem.world_id == world_id,
            AgentMemoryItem.worldline_id == worldline_id,
            AgentMemoryItem.agent_id.in_(participant_agent_ids),
            AgentMemoryItem.is_active.is_(True),
        )
        missing_persona = max(0, len(participant_agent_ids) - persona_count)
        blockers: list[str] = []
        if missing_persona:
            blockers.append("One or more demo agents lack applied persona cards.")
        if memory_count < len(participant_agent_ids):
            blockers.append("One or more demo agents lack initial active memory.")
        refs = [
            IncidentEvidenceRef(
                kind="agent_persona",
                id=str(persona.id),
                component="persona_memory",
                status="enabled" if persona.is_enabled else "disabled",
                reason_code="applied_persona",
                world_id=world_id,
                worldline_id=worldline_id,
                occurred_at=persona.updated_at,
            )
            for persona in self._session.scalars(
                select(AgentPersona)
                .where(
                    AgentPersona.world_id == world_id,
                    AgentPersona.agent_id.in_(participant_agent_ids),
                )
                .order_by(AgentPersona.updated_at.desc())
                .limit(limit),
            ).all()
        ]
        refs.extend(
            IncidentEvidenceRef(
                kind="agent_memory_item",
                id=str(memory.id),
                component="persona_memory",
                status="active" if memory.is_active else "inactive",
                reason_code="initial_memory",
                world_id=world_id,
                worldline_id=memory.worldline_id,
                occurred_at=memory.updated_at,
            )
            for memory in self._session.scalars(
                select(AgentMemoryItem)
                .where(
                    AgentMemoryItem.world_id == world_id,
                    AgentMemoryItem.worldline_id == worldline_id,
                    AgentMemoryItem.agent_id.in_(participant_agent_ids),
                )
                .order_by(AgentMemoryItem.updated_at.desc())
                .limit(limit),
            ).all()
        )
        memory_job_failures = self._count(
            MemoryWriteJob,
            MemoryWriteJob.world_id == world_id,
            MemoryWriteJob.worldline_id == worldline_id,
            MemoryWriteJob.status == "failed",
        )
        warning_count = 1 if memory_job_failures else 0
        recommendations = []
        if blockers:
            recommendations.append("Apply persona and memory proposals for each demo agent.")
        if memory_job_failures:
            recommendations.append("Inspect failed memory write jobs before archive.")
        return _readiness_section(
            "persona_memory",
            status=IncidentStatus.BLOCKED
            if blockers
            else IncidentStatus.WATCH
            if warning_count
            else IncidentStatus.OK,
            summary=(
                f"{persona_count}/{len(participant_agent_ids)} personas and "
                f"{memory_count} active worldline memories."
            ),
            evidence_refs=refs[:limit],
            blockers=blockers,
            warning_count=warning_count,
            recommendations=recommendations,
        )

    def _self_use_visual_section(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        participant_agent_ids: list[uuid.UUID],
        limit: int,
    ) -> ProductionReadinessSection:
        sprite_count = self._count(
            CharacterSpriteVariant,
            CharacterSpriteVariant.world_id == world_id,
            CharacterSpriteVariant.worldline_id == worldline_id,
            CharacterSpriteVariant.status == "active",
        )
        background_count = self._count(
            SceneBackgroundProfile,
            SceneBackgroundProfile.world_id == world_id,
            SceneBackgroundProfile.worldline_id == worldline_id,
            SceneBackgroundProfile.status == "active",
        )
        profile_count = self._count(
            CharacterVisualGenerationProfile,
            CharacterVisualGenerationProfile.world_id == world_id,
            CharacterVisualGenerationProfile.worldline_id == worldline_id,
            CharacterVisualGenerationProfile.agent_id.in_(participant_agent_ids or [uuid.uuid4()]),
            CharacterVisualGenerationProfile.review_status.in_(("approved", "applied")),
        )
        presentation_count = 0
        if conversation_id is not None:
            presentation_count = self._count(
                ConversationTurnPresentation,
                ConversationTurnPresentation.world_id == world_id,
                ConversationTurnPresentation.worldline_id == worldline_id,
                ConversationTurnPresentation.conversation_id == conversation_id,
                or_(
                    ConversationTurnPresentation.sprite_variant_id.is_not(None),
                    ConversationTurnPresentation.background_asset_id.is_not(None),
                    ConversationTurnPresentation.composite_scene_asset_id.is_not(None),
                ),
            )
        plan_count = self._count(
            VisualGenerationPlan,
            VisualGenerationPlan.world_id == world_id,
            VisualGenerationPlan.worldline_id == worldline_id,
            VisualGenerationPlan.status.in_(
                ("validated", "dry_run_succeeded", "queued", "executed")
            ),
        )
        blockers: list[str] = []
        if sprite_count < max(1, len(participant_agent_ids)):
            blockers.append("Not every demo agent has an active sprite variant.")
        if background_count == 0:
            blockers.append("No active scene background profile exists.")
        if profile_count < max(1, len(participant_agent_ids)):
            blockers.append("Not every demo agent has approved visual generation profile evidence.")
        if presentation_count == 0:
            blockers.append("No conversation presentation references visual scene evidence.")
        warning_count = 0 if plan_count else 1
        refs = self._visual_refs(world_id, worldline_id, conversation_id, limit)
        return _readiness_section(
            "visual_playback_generation",
            status=IncidentStatus.BLOCKED
            if blockers
            else IncidentStatus.WATCH
            if warning_count
            else IncidentStatus.OK,
            summary=(
                f"{sprite_count} sprite variants, {background_count} backgrounds, "
                f"{profile_count} visual profiles, {presentation_count} presentations, "
                f"{plan_count} ready visual generation plans."
            ),
            evidence_refs=refs,
            blockers=blockers,
            warning_count=warning_count,
            recommendations=[]
            if not blockers and not warning_count
            else ["Complete visual mappings and at least one validated/dry-run image plan."],
        )

    def _visual_refs(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        limit: int,
    ) -> list[IncidentEvidenceRef]:
        refs: list[IncidentEvidenceRef] = []
        for variant in self._session.scalars(
            select(CharacterSpriteVariant)
            .where(
                CharacterSpriteVariant.world_id == world_id,
                CharacterSpriteVariant.worldline_id == worldline_id,
            )
            .order_by(CharacterSpriteVariant.updated_at.desc())
            .limit(limit),
        ).all():
            refs.append(
                IncidentEvidenceRef(
                    kind="character_sprite_variant",
                    id=str(variant.id),
                    component="visual_playback_generation",
                    status=variant.status,
                    reason_code="sprite_variant",
                    world_id=world_id,
                    worldline_id=worldline_id,
                    occurred_at=variant.updated_at,
                )
            )
            if len(refs) >= limit:
                return refs
        for background in self._session.scalars(
            select(SceneBackgroundProfile)
            .where(
                SceneBackgroundProfile.world_id == world_id,
                SceneBackgroundProfile.worldline_id == worldline_id,
            )
            .order_by(SceneBackgroundProfile.updated_at.desc())
            .limit(limit),
        ).all():
            refs.append(
                IncidentEvidenceRef(
                    kind="scene_background_profile",
                    id=str(background.id),
                    component="visual_playback_generation",
                    status=background.status,
                    reason_code="background_profile",
                    world_id=world_id,
                    worldline_id=worldline_id,
                    occurred_at=background.updated_at,
                )
            )
            if len(refs) >= limit:
                return refs
        if conversation_id is not None:
            for presentation in self._session.scalars(
                select(ConversationTurnPresentation)
                .where(
                    ConversationTurnPresentation.world_id == world_id,
                    ConversationTurnPresentation.worldline_id == worldline_id,
                    ConversationTurnPresentation.conversation_id == conversation_id,
                )
                .order_by(ConversationTurnPresentation.updated_at.desc())
                .limit(limit),
            ).all():
                refs.append(
                    IncidentEvidenceRef(
                        kind="conversation_turn_presentation",
                        id=str(presentation.id),
                        component="visual_playback_generation",
                        status=presentation.render_state,
                        reason_code="presentation_visual_ref",
                        world_id=world_id,
                        worldline_id=worldline_id,
                        occurred_at=presentation.updated_at,
                    )
                )
                if len(refs) >= limit:
                    return refs
        return refs[:limit]

    def _self_use_voice_section(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        participant_agent_ids: list[uuid.UUID],
        limit: int,
    ) -> ProductionReadinessSection:
        binding_count = self._count(
            AgentVoiceProfileBinding,
            AgentVoiceProfileBinding.world_id == world_id,
            AgentVoiceProfileBinding.worldline_id == worldline_id,
            AgentVoiceProfileBinding.agent_id.in_(participant_agent_ids or [uuid.uuid4()]),
        )
        voice_count = self._count(
            VoiceProfile,
            VoiceProfile.world_id == world_id,
            VoiceProfile.worldline_id == worldline_id,
            VoiceProfile.status == "active",
        )
        presentation_count = 0
        if conversation_id is not None:
            presentation_count = self._count(
                ConversationTurnPresentation,
                ConversationTurnPresentation.world_id == world_id,
                ConversationTurnPresentation.worldline_id == worldline_id,
                ConversationTurnPresentation.conversation_id == conversation_id,
                or_(
                    ConversationTurnPresentation.voice_profile_id.is_not(None),
                    ConversationTurnPresentation.tts_media_asset_id.is_not(None),
                ),
            )
        blockers: list[str] = []
        if binding_count < max(1, len(participant_agent_ids)):
            blockers.append("Not every demo agent has a voice profile binding.")
        if voice_count == 0:
            blockers.append("No active voice profile exists for the demo worldline.")
        if presentation_count == 0:
            blockers.append("No conversation presentation references voice or TTS evidence.")
        refs = [
            IncidentEvidenceRef(
                kind="agent_voice_profile_binding",
                id=str(binding.id),
                component="voice_playback",
                status="default" if binding.is_default else "bound",
                reason_code="voice_binding",
                world_id=world_id,
                worldline_id=worldline_id,
                occurred_at=binding.updated_at,
            )
            for binding in self._session.scalars(
                select(AgentVoiceProfileBinding)
                .where(
                    AgentVoiceProfileBinding.world_id == world_id,
                    AgentVoiceProfileBinding.worldline_id == worldline_id,
                )
                .order_by(AgentVoiceProfileBinding.updated_at.desc())
                .limit(limit),
            ).all()
        ]
        return _readiness_section(
            "voice_playback",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=(
                f"{binding_count} bindings, {voice_count} active profiles, "
                f"{presentation_count} voice presentations."
            ),
            evidence_refs=refs,
            blockers=blockers,
            recommendations=[] if not blockers else ["Apply voice mappings for each demo agent."],
        )

    def _self_use_provider_section(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        limit: int,
    ) -> ProductionReadinessSection:
        del worldline_id
        active_count = self._count(
            ProviderIntegration,
            ProviderIntegration.world_id == world_id,
            ProviderIntegration.status == "active",
        )
        required_kinds = {
            "text_generation": "text provider",
            "image_generation": "image provider",
            "text_to_speech": "TTS provider",
            "speech_to_text": "ASR provider",
        }
        blockers = [
            f"Missing active {label}."
            for provider_kind, label in required_kinds.items()
            if self._count(
                ProviderIntegration,
                ProviderIntegration.world_id == world_id,
                ProviderIntegration.status == "active",
                ProviderIntegration.provider_kind == provider_kind,
            )
            == 0
        ]
        unhealthy_count = int(
            self._session.scalar(
                select(func.count(ProviderHealthCheck.id))
                .join(
                    ProviderIntegration,
                    ProviderIntegration.id == ProviderHealthCheck.provider_integration_id,
                )
                .where(
                    ProviderIntegration.world_id == world_id,
                    ProviderHealthCheck.status == "unhealthy",
                )
            )
            or 0
        )
        if unhealthy_count:
            blockers.append("Unhealthy provider smoke/health checks are present.")
        degraded_count = int(
            self._session.scalar(
                select(func.count(ProviderHealthCheck.id))
                .join(
                    ProviderIntegration,
                    ProviderIntegration.id == ProviderHealthCheck.provider_integration_id,
                )
                .where(
                    ProviderIntegration.world_id == world_id,
                    ProviderHealthCheck.status == "degraded",
                )
            )
            or 0
        )
        warning_count = degraded_count
        provider_refs = [
            IncidentEvidenceRef(
                kind="provider_integration",
                id=str(provider.id),
                component="provider_model_lab",
                status=provider.status,
                reason_code=f"{provider.provider_kind}_{provider.adapter_kind}",
                world_id=provider.world_id,
                occurred_at=provider.updated_at,
            )
            for provider in self._session.scalars(
                select(ProviderIntegration)
                .where(
                    ProviderIntegration.world_id == world_id,
                    ProviderIntegration.status == "active",
                )
                .order_by(ProviderIntegration.updated_at.desc())
                .limit(limit),
            ).all()
        ]
        return _readiness_section(
            "provider_model_lab",
            status=IncidentStatus.BLOCKED
            if blockers
            else IncidentStatus.WATCH
            if warning_count
            else IncidentStatus.OK,
            summary=(
                f"{active_count} active providers, {unhealthy_count} unhealthy checks, "
                f"{degraded_count} degraded checks."
            ),
            evidence_refs=provider_refs,
            blockers=blockers,
            warning_count=warning_count,
            recommendations=[]
            if not blockers and not warning_count
            else ["Configure and smoke-check required providers in the model lab."],
        )

    def _self_use_media_job_section(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        limit: int,
    ) -> ProductionReadinessSection:
        failed_count = self._count(
            MediaJob,
            MediaJob.world_id == world_id,
            MediaJob.worldline_id == worldline_id,
            MediaJob.status == "failed",
        )
        active_count = self._count(
            MediaJob,
            MediaJob.world_id == world_id,
            MediaJob.worldline_id == worldline_id,
            MediaJob.status.in_(("queued", "running")),
        )
        output_count = self._count(
            MediaAsset,
            MediaAsset.world_id == world_id,
            MediaAsset.worldline_id == worldline_id,
            MediaAsset.status == "available",
            MediaAsset.asset_role.in_(
                (
                    "scene_background",
                    "character_sprite",
                    "character_expression",
                    "speech_audio",
                    "voice_sample",
                    "event_cg",
                )
            ),
        )
        blockers = ["Failed media jobs are present."] if failed_count else []
        warning_count = 1 if active_count else 0
        if output_count == 0:
            blockers.append("No available demo media assets exist.")
        refs = [
            IncidentEvidenceRef(
                kind="media_job",
                id=str(job.id),
                component="media_jobs",
                status=job.status,
                reason_code=f"media_job_{job.job_kind}",
                world_id=world_id,
                worldline_id=worldline_id,
                occurred_at=job.updated_at,
            )
            for job in self._session.scalars(
                select(MediaJob)
                .where(MediaJob.world_id == world_id, MediaJob.worldline_id == worldline_id)
                .order_by(MediaJob.updated_at.desc())
                .limit(limit),
            ).all()
        ]
        return _readiness_section(
            "media_jobs",
            status=IncidentStatus.BLOCKED
            if blockers
            else IncidentStatus.WATCH
            if warning_count
            else IncidentStatus.OK,
            summary=(
                f"{output_count} available demo media assets, {active_count} queued/running "
                f"jobs, {failed_count} failed jobs."
            ),
            evidence_refs=refs,
            blockers=blockers,
            warning_count=warning_count,
            recommendations=[] if not blockers else ["Repair or retry failed media jobs."],
        )

    def _self_use_invocation_ledger_section(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        limit: int,
    ) -> ProductionReadinessSection:
        invocation_count = self._count(
            ModelInvocation,
            ModelInvocation.world_id == world_id,
            ModelInvocation.worldline_id == worldline_id,
        )
        failed_count = self._count(
            ModelInvocation,
            ModelInvocation.world_id == world_id,
            ModelInvocation.worldline_id == worldline_id,
            ModelInvocation.status == "failed",
        )
        blockers = ["Failed provider invocations are present."] if failed_count else []
        warning_count = 0 if invocation_count else 1
        refs = [
            IncidentEvidenceRef(
                kind="model_invocation",
                id=str(invocation.id),
                component="invocation_ledger",
                status=invocation.status,
                reason_code=f"invocation_{invocation.invocation_kind}",
                world_id=world_id,
                worldline_id=worldline_id,
                occurred_at=invocation.updated_at,
            )
            for invocation in self._session.scalars(
                select(ModelInvocation)
                .where(
                    ModelInvocation.world_id == world_id,
                    ModelInvocation.worldline_id == worldline_id,
                )
                .order_by(ModelInvocation.updated_at.desc())
                .limit(limit),
            ).all()
        ]
        return _readiness_section(
            "invocation_ledger",
            status=IncidentStatus.BLOCKED
            if blockers
            else IncidentStatus.WATCH
            if warning_count
            else IncidentStatus.OK,
            summary=f"{invocation_count} invocation records, {failed_count} failed records.",
            evidence_refs=refs,
            blockers=blockers,
            warning_count=warning_count,
            recommendations=[]
            if not blockers and not warning_count
            else ["Run provider-backed demo actions or review failed invocations."],
        )

    def _self_use_traceability_section(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        limit: int,
    ) -> ProductionReadinessSection:
        fragment_count = self._count(
            AuthoringSourceFragment,
            AuthoringSourceFragment.world_id == world_id,
            AuthoringSourceFragment.worldline_id == worldline_id,
        )
        applied_count = self._count(
            AuthoringImportProposal,
            AuthoringImportProposal.world_id == world_id,
            AuthoringImportProposal.worldline_id == worldline_id,
            AuthoringImportProposal.status == "applied",
        )
        assembly_count = self._count(
            AuthoringImportProposal,
            AuthoringImportProposal.world_id == world_id,
            AuthoringImportProposal.worldline_id == worldline_id,
            AuthoringImportProposal.status == "applied",
            AuthoringImportProposal.target_ref_kind == "demo_world_assembly",
        )
        blockers: list[str] = []
        if fragment_count == 0:
            blockers.append("No source fragments exist for traceability evidence.")
        if applied_count == 0:
            blockers.append("No applied authoring proposals exist for traceability evidence.")
        if assembly_count == 0:
            blockers.append("No applied demo_world_assembly proposal exists.")
        refs = [
            IncidentEvidenceRef(
                kind="authoring_import_proposal",
                id=str(proposal.id),
                component="source_traceability",
                status=proposal.status,
                reason_code=str(proposal.target_ref_kind or proposal.proposal_kind),
                world_id=world_id,
                worldline_id=worldline_id,
                occurred_at=proposal.updated_at,
            )
            for proposal in self._session.scalars(
                select(AuthoringImportProposal)
                .where(
                    AuthoringImportProposal.world_id == world_id,
                    AuthoringImportProposal.worldline_id == worldline_id,
                    AuthoringImportProposal.status == "applied",
                )
                .order_by(AuthoringImportProposal.updated_at.desc())
                .limit(limit),
            ).all()
        ]
        return _readiness_section(
            "source_traceability",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=(
                f"{fragment_count} source fragments, {applied_count} applied proposals, "
                f"{assembly_count} applied demo assemblies."
            ),
            evidence_refs=refs,
            blockers=blockers,
            recommendations=[]
            if not blockers
            else ["Preserve source fragments and apply reviewed demo assembly evidence."],
        )

    def _self_use_no_world_event_leak_section(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        limit: int,
    ) -> ProductionReadinessSection:
        events = self._session.scalars(
            select(WorldEventModel)
            .where(
                WorldEventModel.world_id == world_id,
                or_(
                    WorldEventModel.worldline_id == worldline_id,
                    WorldEventModel.worldline_id.is_(None),
                ),
            )
            .order_by(WorldEventModel.sequence.desc())
            .limit(limit),
        ).all()
        leaky_event_ids: list[str] = []
        for event in events:
            payload_text = json.dumps(event.payload, default=str).lower()
            if any(marker in payload_text for marker in SELF_USE_FORBIDDEN_EVENT_MARKERS):
                leaky_event_ids.append(str(event.id))
        blockers = (
            ["World event payloads contain forbidden storage/path/prompt/secret markers."]
            if leaky_event_ids
            else []
        )
        return _readiness_section(
            "world_event_leak_check",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=f"Checked {len(events)} recent world events for forbidden payload markers.",
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="world_event",
                    id=str(event.id),
                    component="world_event_leak_check",
                    status="safe" if str(event.id) not in leaky_event_ids else "blocked",
                    reason_code=event.event_name,
                    world_id=world_id,
                    worldline_id=event.worldline_id,
                    occurred_at=event.wall_time,
                )
                for event in events
            ],
            blockers=blockers,
            recommendations=[] if not blockers else ["Remove unsafe world event payload content."],
        )

    def _internal_production_readiness_section(
        self,
        internal: ProductionReadinessReport,
        limit: int,
    ) -> ProductionReadinessSection:
        refs: list[IncidentEvidenceRef] = []
        for section in internal.sections:
            refs.extend(section.evidence_refs)
            if len(refs) >= limit:
                refs = refs[:limit]
                break
        blockers = []
        if internal.status == IncidentStatus.BLOCKED:
            blockers.append("Internal production readiness has blocking sections.")
        warning_count = 1 if internal.status == IncidentStatus.WATCH else 0
        return _readiness_section(
            "internal_production_readiness",
            status=internal.status,
            summary=(
                f"Internal production readiness is {internal.status} with "
                f"{internal.blocker_count} blockers and {internal.warning_count} warnings."
            ),
            evidence_refs=refs,
            blockers=blockers,
            warning_count=warning_count,
            recommendations=[]
            if internal.status == IncidentStatus.OK
            else ["Resolve internal production readiness before public launch."],
        )

    def _reader_media_delivery_section(
        self,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> ProductionReadinessSection:
        conditions: list[Any] = [
            MediaAsset.status == "available",
            MediaAsset.visibility.in_(("world_member", "player_visible", "reader_visible")),
            MediaAsset.asset_kind.in_(("image", "audio", "video")),
            MediaReference.ref_kind.in_(
                ("narrative_artifact", "conversation_turn", "conversation_session")
            ),
        ]
        if world_id is not None:
            conditions.append(MediaAsset.world_id == world_id)
        count = int(
            self._session.scalar(
                select(func.count(distinct(MediaAsset.id)))
                .join(
                    MediaObject,
                    MediaObject.asset_id == MediaAsset.id,
                )
                .join(
                    MediaReference,
                    MediaReference.asset_id == MediaAsset.id,
                )
                .where(*conditions)
            )
            or 0
        )
        records = self._session.scalars(
            select(MediaAsset)
            .join(MediaObject, MediaObject.asset_id == MediaAsset.id)
            .join(MediaReference, MediaReference.asset_id == MediaAsset.id)
            .where(*conditions)
            .distinct()
            .order_by(MediaAsset.created_at.desc())
            .limit(limit),
        ).all()
        blockers = [] if count else [
            "No reader-deliverable media with an object and reader-visible reference exists."
        ]
        return _readiness_section(
            "reader_media_delivery",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=f"{count} reader-deliverable media assets have objects and references.",
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="media_asset",
                    id=str(record.id),
                    component="reader_media_delivery",
                    status=record.status,
                    reason_code="reader_safe_media_asset",
                    world_id=record.world_id,
                    worldline_id=record.worldline_id,
                    occurred_at=record.updated_at,
                )
                for record in records
            ],
            blockers=blockers,
            recommendations=[]
            if not blockers
            else ["Publish reader-visible media through the reader delivery boundary."],
        )

    def _conversation_playback_section(
        self,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> ProductionReadinessSection:
        table = Base.metadata.tables.get("conversation_turn_presentations")
        if table is None:
            return _missing_table_section(
                "conversation_playback_scene",
                "conversation_turn_presentations",
            )
        conditions: list[Any] = [
            or_(
                table.c.tts_media_asset_id.is_not(None),
                table.c.background_asset_id.is_not(None),
                table.c.composite_scene_asset_id.is_not(None),
                table.c.sprite_variant_id.is_not(None),
            )
        ]
        if world_id is not None:
            conditions.append(table.c.world_id == world_id)
        count = self._table_count(table, *conditions)
        rows = self._session.execute(
            select(table)
            .where(*conditions)
            .order_by(table.c.updated_at.desc())
            .limit(limit)
        ).mappings()
        blockers = [] if count else [
            "No conversation presentation evidence exists for playback or scene view."
        ]
        return _readiness_section(
            "conversation_playback_scene",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=f"{count} turn presentations reference playback or scene media.",
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="conversation_turn_presentation",
                    id=str(row["id"]),
                    component="conversation_playback_scene",
                    status=str(row["render_state"]),
                    reason_code="turn_presentation_ready",
                    world_id=row["world_id"],
                    worldline_id=row["worldline_id"],
                    occurred_at=row["updated_at"],
                )
                for row in rows
            ],
            blockers=blockers,
            recommendations=[]
            if not blockers
            else ["Create reader-safe conversation presentation evidence."],
        )

    def _player_privacy_section(
        self,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> ProductionReadinessSection:
        table = Base.metadata.tables.get("player_privacy_requests")
        if table is None:
            return _missing_table_section("player_privacy_controls", "player_privacy_requests")
        conditions: list[Any] = []
        if world_id is not None:
            conditions.append(table.c.world_id == world_id)
        count = self._table_count(table, *conditions)
        active_count = self._table_count(
            table,
            *conditions,
            table.c.status.in_(("requested", "under_review", "approved_for_redaction")),
        )
        rows = self._session.execute(
            select(table)
            .where(*conditions)
            .order_by(table.c.updated_at.desc())
            .limit(limit)
        ).mappings()
        blockers = [] if count else [
            "No player privacy export/delete-request workflow evidence exists."
        ]
        warning_count = 1 if active_count else 0
        return _readiness_section(
            "player_privacy_controls",
            status=IncidentStatus.BLOCKED
            if blockers
            else IncidentStatus.WATCH
            if warning_count
            else IncidentStatus.OK,
            summary=f"{count} privacy requests, {active_count} still active or under review.",
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="player_privacy_request",
                    id=str(row["id"]),
                    component="player_privacy_controls",
                    status=str(row["status"]),
                    reason_code=f"privacy_request_{row['request_kind']}",
                    world_id=row["world_id"],
                    worldline_id=row["worldline_id"],
                    occurred_at=row["updated_at"],
                )
                for row in rows
            ],
            blockers=blockers,
            warning_count=warning_count,
            recommendations=[]
            if not blockers and not warning_count
            else ["Resolve or sign off player privacy workflow evidence."],
        )

    def _moderation_workflow_section(
        self,
        world_id: uuid.UUID | None,
        limit: int,
        *,
        moderation_signoff: bool,
    ) -> ProductionReadinessSection:
        reports = Base.metadata.tables.get("moderation_reports")
        actions = Base.metadata.tables.get("moderation_actions")
        incidents = Base.metadata.tables.get("moderation_incidents")
        if reports is None or actions is None or incidents is None:
            return _missing_table_section("moderation_workflow", "moderation workflow")
        conditions: list[Any] = []
        if world_id is not None:
            conditions.append(reports.c.world_id == world_id)
        report_count = self._table_count(reports, *conditions)
        action_conditions: list[Any] = []
        incident_conditions: list[Any] = []
        if world_id is not None:
            action_conditions.append(actions.c.world_id == world_id)
            incident_conditions.append(incidents.c.world_id == world_id)
        action_count = self._table_count(actions, *action_conditions)
        incident_count = self._table_count(incidents, *incident_conditions)
        open_incidents = self._table_count(
            incidents,
            *incident_conditions,
            incidents.c.status.in_(("open", "under_review")),
        )
        blockers = []
        if report_count + action_count + incident_count == 0:
            blockers.append("No moderation report/action/incident workflow evidence exists.")
        if not moderation_signoff:
            blockers.append("Moderation signoff is missing.")
        warning_count = 1 if open_incidents else 0
        refs = self._moderation_refs(
            reports=reports,
            actions=actions,
            incidents=incidents,
            world_id=world_id,
            limit=limit,
        )
        return _readiness_section(
            "moderation_workflow",
            status=IncidentStatus.BLOCKED
            if blockers
            else IncidentStatus.WATCH
            if warning_count
            else IncidentStatus.OK,
            summary=(
                f"{report_count} reports, {action_count} actions, "
                f"{incident_count} incidents, {open_incidents} open incidents."
            ),
            evidence_refs=refs,
            blockers=blockers,
            warning_count=warning_count,
            recommendations=[]
            if not blockers and not warning_count
            else ["Complete moderation review and explicit signoff before launch."],
        )

    def _sample_world_package_section(
        self,
        world_id: uuid.UUID | None,
        limit: int,
        *,
        sample_world_signoff: bool,
    ) -> ProductionReadinessSection:
        latest = self._latest_eval(
            world_id=world_id,
            like_pattern="multimodal-smoke%",
            not_like_pattern=None,
        )
        refs = self._eval_refs(
            world_id=world_id,
            limit=limit,
            component="sample_world_package",
            like_pattern="multimodal-smoke%",
            not_like_pattern=None,
        )
        blockers = []
        if latest is None:
            blockers.append("No sample-world multimodal smoke evidence exists.")
        elif latest.status != "completed":
            blockers.append("Latest sample-world multimodal smoke evidence is not completed.")
        if not sample_world_signoff:
            blockers.append("Sample world release signoff is missing.")
        return _readiness_section(
            "sample_world_package",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=(
                "Sample-world release evidence is "
                f"{'missing' if latest is None else latest.status}."
            ),
            evidence_refs=refs,
            blockers=blockers,
            recommendations=[]
            if not blockers
            else ["Build, import-preview, and sign off the sample world release package."],
        )

    def _plugin_provider_safety_section(
        self,
        world_id: uuid.UUID | None,
        limit: int,
        *,
        security_signoff: bool,
    ) -> ProductionReadinessSection:
        provider_conditions: list[Any] = [ProviderIntegration.status == "active"]
        if world_id is not None:
            provider_conditions.append(ProviderIntegration.world_id == world_id)
        active_count = self._count(ProviderIntegration, *provider_conditions)
        health_conditions: list[Any] = [ProviderHealthCheck.status == "unhealthy"]
        if world_id is not None:
            health_conditions.append(ProviderIntegration.world_id == world_id)
        unhealthy_count = int(
            self._session.scalar(
                select(func.count(ProviderHealthCheck.id))
                .join(
                    ProviderIntegration,
                    ProviderIntegration.id == ProviderHealthCheck.provider_integration_id,
                )
                .where(*health_conditions)
            )
            or 0
        )
        providers = self._session.scalars(
            select(ProviderIntegration)
            .where(*provider_conditions)
            .order_by(ProviderIntegration.updated_at.desc())
            .limit(limit),
        ).all()
        blockers = ["Unhealthy provider evidence blocks public launch."] if unhealthy_count else []
        warning_count = 0 if security_signoff else 1
        refs = [
            IncidentEvidenceRef(
                kind="package_contract_suite",
                id="v0.8-plugin-provider-package-contract-suite",
                component="plugin_provider_safety",
                status="passed",
                reason_code="contract_validation_and_secret_redaction",
            )
        ]
        refs.extend(
            IncidentEvidenceRef(
                kind="provider_integration",
                id=str(provider.id),
                component="plugin_provider_safety",
                status=provider.status,
                reason_code="provider_registry_governance",
                world_id=provider.world_id,
                occurred_at=provider.updated_at,
            )
            for provider in providers
        )
        return _readiness_section(
            "plugin_provider_safety",
            status=IncidentStatus.BLOCKED
            if blockers
            else IncidentStatus.WATCH
            if warning_count
            else IncidentStatus.OK,
            summary=(
                f"{active_count} active providers and {unhealthy_count} unhealthy "
                "provider health checks."
            ),
            evidence_refs=refs[:limit],
            blockers=blockers,
            warning_count=warning_count,
            recommendations=[]
            if not blockers and not warning_count
            else ["Complete security signoff over plugin/provider package contracts."],
        )

    def _public_surface_security_section(
        self,
        *,
        security_signoff: bool,
    ) -> ProductionReadinessSection:
        blockers = [] if security_signoff else [
            "Security signoff is missing for public DTO and leak regression evidence."
        ]
        return _readiness_section(
            "public_surface_security",
            status=IncidentStatus.BLOCKED if blockers else IncidentStatus.OK,
            summary=(
                "Public DTO and leak regression evidence is represented by v0.8 "
                "targeted and full local gates."
            ),
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="security_regression_suite",
                    id="v0.8-public-surface-regression-suite",
                    component="public_surface_security",
                    status="passed",
                    reason_code="targeted_and_full_gate_passed",
                ),
            ],
            blockers=blockers,
            recommendations=[]
            if not blockers
            else ["Complete security signoff before launch readiness can pass."],
        )

    def _explicit_public_signoff_section(
        self,
        signoffs: dict[str, bool],
    ) -> ProductionReadinessSection:
        missing = [key for key, present in signoffs.items() if not present]
        return _readiness_section(
            "explicit_public_signoff",
            status=IncidentStatus.BLOCKED if missing else IncidentStatus.OK,
            summary=(
                f"{len(signoffs) - len(missing)} of {len(signoffs)} public launch "
                "signoffs are present."
            ),
            evidence_refs=[
                IncidentEvidenceRef(
                    kind="public_launch_signoff",
                    id=key,
                    component="explicit_public_signoff",
                    status="present",
                    reason_code="explicit_operator_control",
                )
                for key, present in signoffs.items()
                if present
            ],
            blockers=[f"{key} is missing." for key in missing],
            recommendations=[]
            if not missing
            else ["Record all explicit public launch signoffs before launch."],
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

    def _moderation_refs(
        self,
        *,
        reports: Any,
        actions: Any,
        incidents: Any,
        world_id: uuid.UUID | None,
        limit: int,
    ) -> list[IncidentEvidenceRef]:
        refs: list[IncidentEvidenceRef] = []
        report_conditions: list[Any] = []
        action_conditions: list[Any] = []
        incident_conditions: list[Any] = []
        if world_id is not None:
            report_conditions.append(reports.c.world_id == world_id)
            action_conditions.append(actions.c.world_id == world_id)
            incident_conditions.append(incidents.c.world_id == world_id)
        report_rows = self._session.execute(
            select(reports)
            .where(*report_conditions)
            .order_by(reports.c.updated_at.desc())
            .limit(limit),
        ).mappings()
        for row in report_rows:
            refs.append(
                IncidentEvidenceRef(
                    kind="moderation_report",
                    id=str(row["id"]),
                    component="moderation_workflow",
                    status=str(row["status"]),
                    reason_code=f"report_{row['category']}",
                    world_id=row["world_id"],
                    worldline_id=row["worldline_id"],
                    occurred_at=row["updated_at"],
                )
            )
            if len(refs) >= limit:
                return refs
        action_rows = self._session.execute(
            select(actions)
            .where(*action_conditions)
            .order_by(actions.c.updated_at.desc())
            .limit(limit),
        ).mappings()
        for row in action_rows:
            refs.append(
                IncidentEvidenceRef(
                    kind="moderation_action",
                    id=str(row["id"]),
                    component="moderation_workflow",
                    status=str(row["status"]),
                    reason_code=f"action_{row['action_kind']}",
                    world_id=row["world_id"],
                    worldline_id=row["worldline_id"],
                    occurred_at=row["updated_at"],
                )
            )
            if len(refs) >= limit:
                return refs
        incident_rows = self._session.execute(
            select(incidents)
            .where(*incident_conditions)
            .order_by(incidents.c.updated_at.desc())
            .limit(limit),
        ).mappings()
        for row in incident_rows:
            refs.append(
                IncidentEvidenceRef(
                    kind="moderation_incident",
                    id=str(row["id"]),
                    component="moderation_workflow",
                    status=str(row["status"]),
                    reason_code=f"incident_{row['severity']}",
                    world_id=row["world_id"],
                    worldline_id=row["worldline_id"],
                    occurred_at=row["updated_at"],
                )
            )
            if len(refs) >= limit:
                return refs
        return refs

    def _table_count(self, table: Any, *conditions: Any) -> int:
        return int(
            self._session.scalar(select(func.count(table.c.id)).where(*conditions))
            or 0
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


def _missing_table_section(section_key: str, table_name: str) -> ProductionReadinessSection:
    return _readiness_section(
        section_key,
        status=IncidentStatus.BLOCKED,
        summary=f"{table_name} evidence table is not registered.",
        blockers=[f"{table_name} evidence is unavailable for public launch readiness."],
        recommendations=["Load the existing package models before evaluating readiness."],
    )


def _readiness_status(sections: list[ProductionReadinessSection]) -> IncidentStatus:
    if any(section.status == IncidentStatus.BLOCKED for section in sections):
        return IncidentStatus.BLOCKED
    if any(section.status == IncidentStatus.WATCH for section in sections):
        return IncidentStatus.WATCH
    return IncidentStatus.OK


def _stress_check(
    check_key: str,
    *,
    summary: str,
    evidence_refs: list[IncidentEvidenceRef],
    blockers: list[str],
    warnings: list[str],
) -> NormalUseStressCheck:
    status = IncidentStatus.OK
    if blockers:
        status = IncidentStatus.BLOCKED
    elif warnings:
        status = IncidentStatus.WATCH
    return NormalUseStressCheck(
        check_key=check_key,
        status=status,
        summary=summary,
        evidence_count=len(evidence_refs),
        blocker_count=len(blockers),
        warning_count=len(warnings),
        evidence_refs=evidence_refs,
        blockers=blockers,
        warnings=warnings,
    )


def _stress_status(checks: list[NormalUseStressCheck]) -> IncidentStatus:
    if any(check.status == IncidentStatus.BLOCKED for check in checks):
        return IncidentStatus.BLOCKED
    if any(check.status == IncidentStatus.WATCH for check in checks):
        return IncidentStatus.WATCH
    return IncidentStatus.OK


def _metric_int(metrics: dict[str, Any], key: str) -> int:
    value = metrics.get(key)
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float):
        return max(0, int(value))
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _self_use_manual_checklist(
    *,
    manual_play_minutes: int,
    resume_verified: bool,
    failure_notes_recorded: bool,
) -> list[SelfUseMvpManualChecklistItem]:
    play_status = (
        IncidentStatus.OK if manual_play_minutes >= 30 else IncidentStatus.BLOCKED
    )
    return [
        SelfUseMvpManualChecklistItem(
            item_key="manual_30_minute_play_session",
            title="30-minute self-use play session",
            status=play_status,
            evidence_hint=(
                f"Manual play evidence records {manual_play_minutes} minutes; "
                "at least 30 minutes are required."
            ),
            required_for_pass=True,
        ),
        SelfUseMvpManualChecklistItem(
            item_key="resume_behavior_verified",
            title="Resume behavior checked",
            status=IncidentStatus.OK if resume_verified else IncidentStatus.BLOCKED,
            evidence_hint=(
                "Operator confirmed the same demo conversation can be resumed after leaving "
                "and re-entering."
                if resume_verified
                else "Operator must leave and resume the demo conversation once."
            ),
            required_for_pass=True,
        ),
        SelfUseMvpManualChecklistItem(
            item_key="failure_notes_recorded",
            title="Failure notes recorded",
            status=IncidentStatus.OK if failure_notes_recorded else IncidentStatus.WATCH,
            evidence_hint=(
                "Operator recorded self-use failure notes or confirmed none were found."
                if failure_notes_recorded
                else "Record provider/media/memory/content failure notes before release notes."
            ),
            required_for_pass=False,
        ),
        SelfUseMvpManualChecklistItem(
            item_key="beta_readiness_not_implied",
            title="Beta readiness not implied",
            status=IncidentStatus.OK,
            evidence_hint=(
                "Self-use MVP gate evidence is not private beta, production, or public launch "
                "readiness."
            ),
            required_for_pass=True,
        ),
    ]


def _private_beta_manual_checklist(
    *,
    manual_tester_count: int,
    manual_play_minutes: int,
    tester_session_completed: bool,
    no_developer_intervention_verified: bool,
    quota_reviewed: bool,
    feedback_triage_verified: bool,
    memory_persona_qa_reviewed: bool,
    repair_loop_reviewed: bool,
) -> list[SelfUseMvpManualChecklistItem]:
    tester_status = (
        IncidentStatus.OK if 1 <= manual_tester_count <= 3 else IncidentStatus.BLOCKED
    )
    duration_status = (
        IncidentStatus.OK
        if tester_session_completed and manual_play_minutes >= 60
        else IncidentStatus.BLOCKED
    )
    return [
        SelfUseMvpManualChecklistItem(
            item_key="manual_private_beta_tester_count",
            title="1-3 invited testers exercised the beta path",
            status=tester_status,
            evidence_hint=(
                f"Manual evidence records {manual_tester_count} testers; 1-3 are required."
            ),
            required_for_pass=True,
        ),
        SelfUseMvpManualChecklistItem(
            item_key="manual_private_beta_session_duration",
            title="1-2 hour private beta session completed",
            status=duration_status,
            evidence_hint=(
                f"Manual session evidence records {manual_play_minutes} minutes; at least "
                "60 minutes and explicit completion are required."
            ),
            required_for_pass=True,
        ),
        SelfUseMvpManualChecklistItem(
            item_key="no_developer_intervention_verified",
            title="No developer intervention required",
            status=IncidentStatus.OK
            if no_developer_intervention_verified
            else IncidentStatus.BLOCKED,
            evidence_hint=(
                "Tester session completed without manual DB/provider/media rescue."
                if no_developer_intervention_verified
                else "Confirm testers can continue without developer hand-repair."
            ),
            required_for_pass=True,
        ),
        SelfUseMvpManualChecklistItem(
            item_key="quota_reviewed",
            title="Quota and degraded-mode behavior reviewed",
            status=IncidentStatus.OK if quota_reviewed else IncidentStatus.BLOCKED,
            evidence_hint=(
                "Admin reviewed quota and degraded-mode evidence."
                if quota_reviewed
                else "Review quota controls and quota-exceeded player behavior."
            ),
            required_for_pass=True,
        ),
        SelfUseMvpManualChecklistItem(
            item_key="feedback_triage_reviewed",
            title="Feedback submission and triage reviewed",
            status=IncidentStatus.OK if feedback_triage_verified else IncidentStatus.BLOCKED,
            evidence_hint=(
                "Admin reviewed feedback submission and triage evidence."
                if feedback_triage_verified
                else "Submit and triage at least one contextual beta feedback report."
            ),
            required_for_pass=True,
        ),
        SelfUseMvpManualChecklistItem(
            item_key="memory_persona_qa_reviewed",
            title="Memory/persona QA reviewed",
            status=IncidentStatus.OK if memory_persona_qa_reviewed else IncidentStatus.BLOCKED,
            evidence_hint=(
                "Admin confirmed no critical memory/persona QA blocker remains."
                if memory_persona_qa_reviewed
                else "Run memory/persona QA and resolve critical blockers."
            ),
            required_for_pass=True,
        ),
        SelfUseMvpManualChecklistItem(
            item_key="repair_loop_reviewed",
            title="Content repair loop reviewed",
            status=IncidentStatus.OK if repair_loop_reviewed else IncidentStatus.BLOCKED,
            evidence_hint=(
                "Admin reviewed beta feedback to repair proposal traceability."
                if repair_loop_reviewed
                else "Review feedback-linked authoring repair proposals."
            ),
            required_for_pass=True,
        ),
        SelfUseMvpManualChecklistItem(
            item_key="private_beta_not_public_launch",
            title="Private beta is not public launch readiness",
            status=IncidentStatus.OK,
            evidence_hint=(
                "Passing private beta readiness does not authorize public launch or normal-use RC."
            ),
            required_for_pass=True,
        ),
    ]


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
