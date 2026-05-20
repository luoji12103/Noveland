from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Any

from noveland.invocations.models import ModelInvocation
from noveland.media.models import MediaJob
from noveland.providers.contracts import (
    ProviderBudgetPolicyCreate,
    ProviderBudgetPolicyRead,
    ProviderBudgetPolicyStatus,
    ProviderBudgetPolicyUpdate,
    ProviderQuotaStatusRead,
)
from noveland.providers.models import ProviderBudgetPolicy, ProviderIntegration
from noveland.providers.registry import ProviderNotFoundError, ProviderValidationError
from noveland.providers.secrets import reject_sensitive_config, sanitize_for_persistence
from noveland.worlds.models import World
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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


class ProviderBudgetError(RuntimeError):
    pass


class ProviderBudgetExceededError(ProviderBudgetError):
    pass


@dataclass(frozen=True, slots=True)
class ProviderBudgetCheckResult:
    allowed: bool
    reason: str | None
    quota_status: ProviderQuotaStatusRead


class ProviderBudgetService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_policy(self, create: ProviderBudgetPolicyCreate) -> ProviderBudgetPolicyRead:
        self._validate_world(create.world_id)
        self._validate_provider(create.world_id, create.provider_id)
        self._validate_safe_json(create.limits_json, "limits_json")
        self._validate_safe_json(create.metadata_json, "metadata_json")
        model = ProviderBudgetPolicy(
            id=uuid.uuid4(),
            world_id=create.world_id,
            provider_id=create.provider_id,
            policy_key=create.policy_key,
            status=create.status.value,
            emergency_stop_enabled=create.emergency_stop_enabled,
            limits_json=create.limits_json,
            metadata_json=create.metadata_json,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise ProviderValidationError("provider budget policy already exists") from exc
        self._session.refresh(model)
        return _policy_record(model)

    def update_policy(
        self,
        world_id: uuid.UUID,
        policy_id: uuid.UUID,
        update: ProviderBudgetPolicyUpdate,
    ) -> ProviderBudgetPolicyRead:
        model = self._required_policy(world_id, policy_id)
        if update.status is not None:
            model.status = update.status.value
        if update.emergency_stop_enabled is not None:
            model.emergency_stop_enabled = update.emergency_stop_enabled
        if update.limits_json is not None:
            self._validate_safe_json(update.limits_json, "limits_json")
            model.limits_json = update.limits_json
        if update.metadata_json is not None:
            self._validate_safe_json(update.metadata_json, "metadata_json")
            model.metadata_json = update.metadata_json
        self._session.flush()
        self._session.refresh(model)
        return _policy_record(model)

    def list_policies(
        self,
        world_id: uuid.UUID,
        *,
        provider_id: uuid.UUID | None = None,
        include_inactive: bool = False,
    ) -> list[ProviderBudgetPolicyRead]:
        statement = select(ProviderBudgetPolicy).where(ProviderBudgetPolicy.world_id == world_id)
        if provider_id is not None:
            statement = statement.where(ProviderBudgetPolicy.provider_id == provider_id)
        if not include_inactive:
            statement = statement.where(
                ProviderBudgetPolicy.status == ProviderBudgetPolicyStatus.ACTIVE.value
            )
        statement = statement.order_by(
            ProviderBudgetPolicy.provider_id.is_not(None),
            ProviderBudgetPolicy.policy_key,
        )
        return [_policy_record(model) for model in self._session.scalars(statement).all()]

    def quota_status(
        self,
        world_id: uuid.UUID,
        *,
        provider_id: uuid.UUID | None = None,
        player_actor_id: uuid.UUID | None = None,
        capability_key: str | None = None,
    ) -> ProviderQuotaStatusRead:
        policies = self._matching_policies(world_id, provider_id=provider_id)
        normalized_capability = _normalize_key(capability_key)
        usage = self._usage(
            world_id,
            provider_id=provider_id,
            player_actor_id=player_actor_id,
            capability_key=normalized_capability,
        )
        limits = _merged_limits(
            policies,
            player_actor_id=player_actor_id,
            capability_key=normalized_capability,
        )
        blocked_reasons = _blocked_reasons(
            policies,
            usage.daily_invocation_count,
            usage.daily_estimated_cost,
            usage.daily_media_job_count,
            player_actor_id=player_actor_id,
            capability_key=normalized_capability,
        )
        return ProviderQuotaStatusRead(
            world_id=world_id,
            provider_id=provider_id,
            player_actor_id=player_actor_id,
            capability_key=normalized_capability,
            emergency_stop_active=any(policy.emergency_stop_enabled for policy in policies),
            blocked_reasons=blocked_reasons,
            active_policy_ids=[policy.id for policy in policies],
            daily_invocation_count=usage.daily_invocation_count,
            daily_media_job_count=usage.daily_media_job_count,
            daily_estimated_cost=usage.daily_estimated_cost,
            limits_json=limits,
        )

    def check_provider_execution(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
        *,
        player_actor_id: uuid.UUID | None = None,
        capability_key: str | None = None,
    ) -> ProviderBudgetCheckResult:
        quota = self.quota_status(
            world_id,
            provider_id=provider_id,
            player_actor_id=player_actor_id,
            capability_key=capability_key,
        )
        if quota.blocked_reasons:
            reason = quota.blocked_reasons[0]
            raise ProviderBudgetExceededError(f"provider budget blocked: {reason}")
        return ProviderBudgetCheckResult(allowed=True, reason=None, quota_status=quota)

    def _matching_policies(
        self,
        world_id: uuid.UUID,
        *,
        provider_id: uuid.UUID | None,
    ) -> list[ProviderBudgetPolicy]:
        statement = select(ProviderBudgetPolicy).where(
            ProviderBudgetPolicy.world_id == world_id,
            ProviderBudgetPolicy.status == ProviderBudgetPolicyStatus.ACTIVE.value,
            or_(
                ProviderBudgetPolicy.provider_id.is_(None),
                ProviderBudgetPolicy.provider_id == provider_id,
            ),
        )
        return list(self._session.scalars(statement).all())

    def _usage(
        self,
        world_id: uuid.UUID,
        *,
        provider_id: uuid.UUID | None,
        player_actor_id: uuid.UUID | None,
        capability_key: str | None,
    ) -> _Usage:
        day_start = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)
        invocations = self._session.scalars(
            select(ModelInvocation).where(
                ModelInvocation.world_id == world_id,
                ModelInvocation.created_at >= day_start,
            )
        ).all()
        media_jobs = self._session.scalars(
            select(MediaJob).where(
                MediaJob.world_id == world_id,
                MediaJob.created_at >= day_start,
            )
        ).all()
        filtered_invocations = [
            item
            for item in invocations
            if _matches_provider(item.request_params_json, provider_id)
            and _matches_player(item.request_params_json, player_actor_id)
            and _matches_capability(item.request_params_json, capability_key)
        ]
        filtered_jobs = [
            item
            for item in media_jobs
            if _matches_provider(item.provider_config_json, provider_id)
            and _matches_player(item.provider_config_json, player_actor_id)
            and _matches_capability(item.provider_config_json, capability_key)
        ]
        estimated_cost = sum(
            float(item.estimated_cost or Decimal("0")) for item in filtered_invocations
        )
        return _Usage(
            daily_invocation_count=len(filtered_invocations),
            daily_media_job_count=len(filtered_jobs),
            daily_estimated_cost=round(estimated_cost, 8),
        )

    def _validate_world(self, world_id: uuid.UUID) -> None:
        if self._session.get(World, world_id) is None:
            raise ProviderValidationError("provider budget world not found")

    def _validate_provider(self, world_id: uuid.UUID, provider_id: uuid.UUID | None) -> None:
        if provider_id is None:
            return
        provider = self._session.get(ProviderIntegration, provider_id)
        if provider is None or (
            provider.world_id is not None and provider.world_id != world_id
        ):
            raise ProviderValidationError("provider budget provider not found")

    def _required_policy(self, world_id: uuid.UUID, policy_id: uuid.UUID) -> ProviderBudgetPolicy:
        model = self._session.get(ProviderBudgetPolicy, policy_id)
        if model is None or model.world_id != world_id:
            raise ProviderNotFoundError("provider budget policy not found")
        return model

    def _validate_safe_json(self, value: dict[str, Any], field_name: str) -> None:
        reject_sensitive_config(value, field_name=field_name)
        leaky_path = _first_leaky_path(value)
        if leaky_path is not None:
            raise ProviderValidationError(f"{field_name} contains unsafe key: {leaky_path}")


@dataclass(frozen=True, slots=True)
class _Usage:
    daily_invocation_count: int
    daily_media_job_count: int
    daily_estimated_cost: float


def _policy_record(model: ProviderBudgetPolicy) -> ProviderBudgetPolicyRead:
    return ProviderBudgetPolicyRead(
        id=model.id,
        world_id=model.world_id,
        provider_id=model.provider_id,
        policy_key=model.policy_key,
        status=ProviderBudgetPolicyStatus(model.status),
        emergency_stop_enabled=model.emergency_stop_enabled,
        limits_json=sanitize_for_persistence(model.limits_json),
        metadata_json=sanitize_for_persistence(model.metadata_json),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _matches_provider(payload: dict[str, Any] | None, provider_id: uuid.UUID | None) -> bool:
    if provider_id is None:
        return True
    if not isinstance(payload, dict):
        return False
    return str(payload.get("provider_id")) == str(provider_id)


def _matches_player(
    payload: dict[str, Any] | None,
    player_actor_id: uuid.UUID | None,
) -> bool:
    if player_actor_id is None:
        return True
    if not isinstance(payload, dict):
        return False
    return str(payload.get("player_actor_id")) == str(player_actor_id)


def _matches_capability(payload: dict[str, Any] | None, capability_key: str | None) -> bool:
    if capability_key is None:
        return True
    if not isinstance(payload, dict):
        return False
    return _normalize_key(payload.get("capability_key")) == capability_key


def _merged_limits(
    policies: list[ProviderBudgetPolicy],
    *,
    player_actor_id: uuid.UUID | None,
    capability_key: str | None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key in ("max_daily_invocations", "max_daily_estimated_cost", "max_daily_media_jobs"):
        values = [
            _numeric_limit(limit_value)
            for policy in policies
            for limit_value in _candidate_limit_values(
                policy.limits_json,
                key,
                player_actor_id=player_actor_id,
                capability_key=capability_key,
            )
        ]
        concrete = [value for value in values if value is not None]
        if concrete:
            merged[key] = min(concrete)
    return merged


def _blocked_reasons(
    policies: list[ProviderBudgetPolicy],
    daily_invocation_count: int,
    daily_estimated_cost: float,
    daily_media_job_count: int,
    *,
    player_actor_id: uuid.UUID | None,
    capability_key: str | None,
) -> list[str]:
    reasons: list[str] = []
    if any(policy.emergency_stop_enabled for policy in policies):
        reasons.append("emergency_stop")
    limits = _merged_limits(
        policies,
        player_actor_id=player_actor_id,
        capability_key=capability_key,
    )
    max_invocations = _numeric_limit(limits.get("max_daily_invocations"))
    if max_invocations is not None and daily_invocation_count >= max_invocations:
        reasons.append("daily_invocation_limit")
    max_cost = _numeric_limit(limits.get("max_daily_estimated_cost"))
    if max_cost is not None and daily_estimated_cost >= max_cost:
        reasons.append("daily_estimated_cost_limit")
    max_media_jobs = _numeric_limit(limits.get("max_daily_media_jobs"))
    if max_media_jobs is not None and daily_media_job_count >= max_media_jobs:
        reasons.append("daily_media_job_limit")
    return reasons


def _candidate_limit_values(
    limits_json: dict[str, Any],
    key: str,
    *,
    player_actor_id: uuid.UUID | None,
    capability_key: str | None,
) -> list[object]:
    values: list[object] = [limits_json.get(key)]
    if capability_key is not None:
        capability_limits = _nested_limits(limits_json.get("capabilities"), capability_key)
        if capability_limits is not None:
            values.append(capability_limits.get(key))
    if player_actor_id is not None:
        default_player_limits = _mapping(limits_json.get("default_player"))
        if default_player_limits is not None:
            values.append(default_player_limits.get(key))
        player_limits = _nested_limits(limits_json.get("players"), str(player_actor_id))
        if player_limits is not None:
            values.append(player_limits.get(key))
    return values


def _nested_limits(value: object, key: str) -> dict[str, Any] | None:
    mapping = _mapping(value)
    if mapping is None:
        return None
    nested = mapping.get(key)
    if nested is None:
        nested = mapping.get(key.lower())
    return _mapping(nested)


def _mapping(value: object) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _numeric_limit(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _normalize_key(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def _first_leaky_path(value: Any, *, prefix: str = "") -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            path = key_text if prefix == "" else f"{prefix}.{key_text}"
            if key_text.strip().lower() in LEAKY_KEYS:
                return path
            nested = _first_leaky_path(item, prefix=path)
            if nested is not None:
                return nested
    elif isinstance(value, list):
        for index, item in enumerate(value):
            nested = _first_leaky_path(item, prefix=f"{prefix}[{index}]")
            if nested is not None:
                return nested
    return None
