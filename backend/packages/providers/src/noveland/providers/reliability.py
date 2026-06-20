from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from noveland.invocations.models import ModelInvocation
from noveland.media.contracts import MediaJobStatus
from noveland.media.models import MediaJob
from noveland.media.service import MediaJobService
from noveland.providers.budget import ProviderBudgetExceededError, ProviderBudgetService
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderFallbackMode,
    ProviderFallbackPlanRead,
    ProviderFallbackPlanRequest,
    ProviderHealthStatus,
    ProviderIntegrationStatus,
    ProviderKind,
    ProviderMediaJobRequeueResult,
    ProviderReliabilityEvidenceRef,
    ProviderReliabilityMode,
    ProviderReliabilityProviderRef,
    ProviderReliabilityReportRead,
)
from noveland.providers.models import ProviderCapability, ProviderHealthCheck, ProviderIntegration
from noveland.providers.registry import ProviderNotFoundError, ProviderRegistryService
from noveland.providers.routing import capability_key_for_provider, equivalent_capability_keys
from noveland.providers.secrets import (
    ProviderSecretMissingError,
    ProviderSecretResolver,
    adapter_requires_auth,
    reject_sensitive_config,
    sanitize_for_persistence,
)
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import select
from sqlalchemy.orm import Session


class ProviderReliabilityError(ValueError):
    pass


class ProviderReliabilityService:
    def __init__(
        self,
        session: Session,
        secret_resolver: ProviderSecretResolver | None = None,
    ) -> None:
        self._session = session
        self._secret_resolver = secret_resolver or ProviderSecretResolver()

    def reliability_report(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
        *,
        platform_admin: bool = False,
        window_hours: int = 24,
        limit: int = 20,
    ) -> ProviderReliabilityReportRead:
        provider = self._provider_model(world_id, provider_id, platform_admin=platform_admin)
        health_checks = self._recent_health_checks(provider.id, window_hours, limit)
        failed_invocations = self._recent_failed_invocations(
            world_id,
            provider.id,
            window_hours,
            limit,
        )
        unhealthy_count = sum(
            1 for check in health_checks if check.status == ProviderHealthStatus.UNHEALTHY.value
        )
        degraded_count = sum(
            1 for check in health_checks if check.status == ProviderHealthStatus.DEGRADED.value
        )
        blocked_reasons: list[str] = []
        if provider.status != ProviderIntegrationStatus.ACTIVE.value:
            blocked_reasons.append("provider_not_active")
        if unhealthy_count >= 3 or len(failed_invocations) >= 3:
            reliability_mode = ProviderReliabilityMode.DEGRADED
        elif provider.status != ProviderIntegrationStatus.ACTIVE.value:
            reliability_mode = ProviderReliabilityMode.UNAVAILABLE
        elif unhealthy_count > 0 or degraded_count > 0 or failed_invocations:
            reliability_mode = ProviderReliabilityMode.AT_RISK
        else:
            reliability_mode = ProviderReliabilityMode.NORMAL

        policy = _reliability_policy(provider.config_json)
        return ProviderReliabilityReportRead(
            provider=_provider_ref(provider),
            reliability_mode=reliability_mode,
            degraded_mode_active=reliability_mode
            in {ProviderReliabilityMode.DEGRADED, ProviderReliabilityMode.UNAVAILABLE},
            recent_health_count=len(health_checks),
            recent_unhealthy_count=unhealthy_count,
            recent_degraded_count=degraded_count,
            recent_failed_invocation_count=len(failed_invocations),
            manual_fallback_enabled=policy.manual_fallback_enabled,
            automatic_fallback_enabled=False,
            fallback_provider_ids=tuple(policy.fallback_provider_ids),
            evidence_refs=tuple(
                [
                    *(
                        ProviderReliabilityEvidenceRef(
                            evidence_kind="provider_health_check",
                            ref_id=check.id,
                            status=check.status,
                            metadata_json=_safe_metadata(
                                {
                                    "latency_ms": check.latency_ms,
                                    "checked_at": check.checked_at.isoformat(),
                                }
                            ),
                        )
                        for check in health_checks
                    ),
                    *(
                        ProviderReliabilityEvidenceRef(
                            evidence_kind="model_invocation",
                            ref_id=invocation.id,
                            status=invocation.status,
                            metadata_json=_safe_metadata(
                                {"created_at": invocation.created_at.isoformat()}
                            ),
                        )
                        for invocation in failed_invocations
                    ),
                ]
            ),
            blocked_reasons=tuple(blocked_reasons),
        )

    def fallback_plan(
        self,
        world_id: uuid.UUID,
        primary_provider_id: uuid.UUID,
        request: ProviderFallbackPlanRequest,
        *,
        platform_admin: bool = False,
    ) -> ProviderFallbackPlanRead:
        primary = self._provider_model(
            world_id,
            primary_provider_id,
            platform_admin=platform_admin,
        )
        capability_key = request.capability_key or capability_key_for_provider(
            ProviderKind(primary.provider_kind)
        )
        report = self.reliability_report(
            world_id,
            primary_provider_id,
            platform_admin=platform_admin,
        )
        blocked: list[str] = []
        fallback: ProviderIntegration | None = None
        if request.fallback_mode != ProviderFallbackMode.MANUAL:
            blocked.append("automatic_fallback_disabled")
        policy = _reliability_policy(primary.config_json)
        if not policy.manual_fallback_enabled:
            blocked.append("manual_fallback_not_enabled")
        if request.fallback_provider_id not in policy.fallback_provider_ids:
            blocked.append("fallback_provider_not_allowed")
        if not report.degraded_mode_active:
            blocked.append("primary_not_degraded")
        if request.fallback_provider_id == primary_provider_id:
            blocked.append("fallback_same_as_primary")

        try:
            fallback = self._provider_model(
                world_id,
                request.fallback_provider_id,
                platform_admin=platform_admin,
            )
        except ProviderNotFoundError:
            blocked.append("fallback_provider_not_found")

        quota_checked = False
        auth_checked = False
        if fallback is not None:
            if fallback.status != ProviderIntegrationStatus.ACTIVE.value:
                blocked.append("fallback_provider_not_active")
            if fallback.provider_kind != primary.provider_kind:
                blocked.append("fallback_provider_kind_mismatch")
            if not self._provider_supports_capability(fallback.id, capability_key):
                blocked.append("fallback_capability_missing")
            try:
                ProviderBudgetService(self._session).check_provider_execution(
                    world_id,
                    fallback.id,
                    player_actor_id=request.player_actor_id,
                    capability_key=capability_key,
                )
                quota_checked = True
            except ProviderBudgetExceededError:
                quota_checked = True
                blocked.append("fallback_quota_blocked")
            auth_checked = True
            if adapter_requires_auth(
                ProviderAdapterKind(fallback.adapter_kind),
                fallback.config_json,
            ):
                try:
                    self._secret_resolver.resolve_auth_ref(fallback.auth_ref)
                except ProviderSecretMissingError:
                    blocked.append("fallback_auth_missing")
        worldline_id = (
            worldline_or_404(self._session, world_id, request.worldline_id).id
            if request.worldline_id is not None
            else None
        )
        audit_metadata = _safe_metadata(
            {
                "provider_reliability": True,
                "fallback_selected": not blocked,
                "fallback_mode": request.fallback_mode.value,
                "primary_provider_id": str(primary_provider_id),
                "fallback_provider_id": str(request.fallback_provider_id),
                "capability_key": capability_key,
                "reason": request.reason,
                **({} if worldline_id is None else {"worldline_id": str(worldline_id)}),
            }
        )
        return ProviderFallbackPlanRead(
            allowed=not blocked,
            primary_provider=_provider_ref(primary),
            fallback_provider=None if fallback is None else _provider_ref(fallback),
            fallback_mode=request.fallback_mode,
            capability_key=capability_key,
            degraded_mode_active=report.degraded_mode_active,
            quota_checked=quota_checked,
            auth_checked=auth_checked,
            audit_required=True,
            automatic_fallback_enabled=False,
            blocked_reasons=tuple(blocked),
            evidence_refs=report.evidence_refs,
            audit_metadata=audit_metadata,
        )

    def require_fallback_provider(
        self,
        world_id: uuid.UUID,
        primary_provider_id: uuid.UUID,
        request: ProviderFallbackPlanRequest,
        *,
        platform_admin: bool = True,
    ) -> tuple[ProviderIntegration, dict[str, Any]]:
        plan = self.fallback_plan(
            world_id,
            primary_provider_id,
            request,
            platform_admin=platform_admin,
        )
        if not plan.allowed or plan.fallback_provider is None:
            reasons = ",".join(plan.blocked_reasons) or "fallback_not_allowed"
            raise ProviderReliabilityError(f"provider fallback blocked: {reasons}")
        provider = self._provider_model(
            world_id,
            plan.fallback_provider.id,
            platform_admin=platform_admin,
        )
        return provider, dict(plan.audit_metadata)

    def requeue_media_job(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
        job_id: uuid.UUID,
        *,
        actor_ref: str,
        reason: str | None = None,
        platform_admin: bool = False,
    ) -> ProviderMediaJobRequeueResult:
        provider = self._provider_model(world_id, provider_id, platform_admin=platform_admin)
        original_model = self._session.get(MediaJob, job_id)
        if original_model is None or original_model.world_id != world_id:
            raise ProviderNotFoundError("media job not found")
        if _provider_id_from_job(original_model) != provider.id:
            raise ProviderReliabilityError("media job is not linked to the provider")
        original = MediaJobService(self._session).get_job(
            world_id,
            job_id,
            worldline_id=original_model.worldline_id,
        )
        if original is None:
            raise ProviderNotFoundError("media job not found")
        if original.status not in {MediaJobStatus.FAILED, MediaJobStatus.CANCELLED}:
            raise ProviderReliabilityError("only failed or cancelled media jobs can be requeued")
        requeued = MediaJobService(self._session).retry_job(
            world_id,
            job_id,
            actor_ref=actor_ref,
        )
        audit_metadata = _safe_metadata(
            {
                "provider_reliability_requeue": True,
                "manual_requeue": True,
                "original_job_id": str(original.id),
                "requeued_job_id": str(requeued.id),
                "provider_id": str(provider.id),
                "provider_key": provider.provider_key,
                "reason": reason,
                "requeued_by_actor_ref": actor_ref,
                "requeued_at": datetime.now(UTC).isoformat(),
            }
        )
        requeued_model = self._session.get(MediaJob, requeued.id)
        if requeued_model is not None:
            requeued_model.provider_config_json = {
                **dict(requeued_model.provider_config_json),
                **audit_metadata,
            }
            self._session.flush()
            self._session.refresh(requeued_model)
            requeued = MediaJobService(self._session).get_job(
                world_id,
                requeued_model.id,
                worldline_id=requeued_model.worldline_id,
            ) or requeued
        return ProviderMediaJobRequeueResult(
            original_job=original,
            requeued_job=requeued,
            audit_metadata=audit_metadata,
            provider_execution=False,
        )

    def _provider_model(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
        *,
        platform_admin: bool,
    ) -> ProviderIntegration:
        provider = ProviderRegistryService(self._session).get_provider(
            world_id,
            provider_id,
            platform_admin=platform_admin,
            include_hidden=platform_admin,
        )
        if provider is None:
            raise ProviderNotFoundError("provider integration not found")
        return ProviderRegistryService(self._session).internal_model(provider_id)

    def _recent_health_checks(
        self,
        provider_id: uuid.UUID,
        window_hours: int,
        limit: int,
    ) -> list[ProviderHealthCheck]:
        window_start = datetime.now(UTC) - timedelta(hours=window_hours)
        return list(
            self._session.scalars(
                select(ProviderHealthCheck)
                .where(
                    ProviderHealthCheck.provider_integration_id == provider_id,
                    ProviderHealthCheck.checked_at >= window_start,
                )
                .order_by(ProviderHealthCheck.checked_at.desc())
                .limit(limit)
            ).all()
        )

    def _recent_failed_invocations(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
        window_hours: int,
        limit: int,
    ) -> list[ModelInvocation]:
        window_start = datetime.now(UTC) - timedelta(hours=window_hours)
        return [
            invocation
            for invocation in self._session.scalars(
                select(ModelInvocation)
                .where(
                    ModelInvocation.world_id == world_id,
                    ModelInvocation.status == "failed",
                    ModelInvocation.created_at >= window_start,
                )
                .order_by(ModelInvocation.created_at.desc())
                .limit(limit * 2)
            ).all()
            if isinstance(invocation.request_params_json, dict)
            and invocation.request_params_json.get("provider_id") == str(provider_id)
        ][:limit]

    def _provider_supports_capability(
        self,
        provider_id: uuid.UUID,
        capability_key: str,
    ) -> bool:
        capability = self._session.scalar(
            select(ProviderCapability.id).where(
                ProviderCapability.provider_integration_id == provider_id,
                ProviderCapability.capability_key.in_(equivalent_capability_keys(capability_key)),
            )
        )
        if capability is not None:
            return True
        provider = self._session.get(ProviderIntegration, provider_id)
        if provider is None:
            return False
        return capability_key == capability_key_for_provider(ProviderKind(provider.provider_kind))


class _ReliabilityPolicy:
    def __init__(
        self,
        *,
        manual_fallback_enabled: bool,
        fallback_provider_ids: tuple[uuid.UUID, ...],
    ) -> None:
        self.manual_fallback_enabled = manual_fallback_enabled
        self.fallback_provider_ids = fallback_provider_ids


def _reliability_policy(config_json: dict[str, Any]) -> _ReliabilityPolicy:
    raw = config_json.get("reliability")
    if not isinstance(raw, dict):
        return _ReliabilityPolicy(
            manual_fallback_enabled=False,
            fallback_provider_ids=(),
        )
    raw_ids = raw.get("fallback_provider_ids")
    ids: list[uuid.UUID] = []
    if isinstance(raw_ids, list):
        for item in raw_ids:
            try:
                ids.append(uuid.UUID(str(item)))
            except ValueError:
                continue
    return _ReliabilityPolicy(
        manual_fallback_enabled=raw.get("manual_fallback_enabled") is True,
        fallback_provider_ids=tuple(ids),
    )


def _provider_ref(provider: ProviderIntegration) -> ProviderReliabilityProviderRef:
    return ProviderReliabilityProviderRef(
        id=provider.id,
        provider_key=provider.provider_key,
        provider_kind=ProviderKind(provider.provider_kind),
        adapter_kind=ProviderAdapterKind(provider.adapter_kind),
        status=ProviderIntegrationStatus(provider.status),
        auth_ref_configured=provider.auth_ref is not None,
    )


def _provider_id_from_job(job: MediaJob) -> uuid.UUID | None:
    if isinstance(job.provider_config_json, dict):
        raw = job.provider_config_json.get("provider_id")
        if raw is not None:
            try:
                return uuid.UUID(str(raw))
            except ValueError:
                return None
    return None


def _safe_metadata(value: dict[str, Any]) -> dict[str, Any]:
    safe = sanitize_for_persistence(value)
    reject_sensitive_config(safe, field_name="provider reliability metadata")
    return cast(dict[str, Any], safe)
