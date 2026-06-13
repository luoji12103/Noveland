from __future__ import annotations

import uuid
from datetime import UTC, datetime

from noveland.providers.contracts import (
    ProviderHealthCheckRead,
    ProviderHealthStatus,
    ProviderIntegrationStatus,
)
from noveland.providers.models import ProviderHealthCheck, ProviderIntegration
from noveland.providers.registry import ProviderNotFoundError, ProviderRegistryService
from noveland.providers.secrets import (
    ProviderSecretMissingError,
    ProviderSecretResolver,
    adapter_requires_auth,
    reject_sensitive_config,
    sanitize_for_persistence,
    sanitize_provider_diagnostic_text,
)
from sqlalchemy import select
from sqlalchemy.orm import Session


class ProviderHealthService:
    def __init__(
        self,
        session: Session,
        secret_resolver: ProviderSecretResolver | None = None,
    ) -> None:
        self._session = session
        self._secret_resolver = secret_resolver or ProviderSecretResolver()

    def run_health_check(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
        *,
        platform_admin: bool = False,
    ) -> ProviderHealthCheckRead:
        provider = ProviderRegistryService(self._session).get_provider(
            world_id,
            provider_id,
            platform_admin=platform_admin,
        )
        if provider is None:
            raise ProviderNotFoundError("provider integration not found")
        model = ProviderRegistryService(self._session).internal_model(provider_id)
        status = ProviderHealthStatus.HEALTHY
        metadata: dict[str, object] = {
            "adapter_kind": provider.adapter_kind.value,
            "provider_kind": provider.provider_kind.value,
            "provider_key": provider.provider_key,
            "provider_status": model.status,
            "auth_ref_present": model.auth_ref is not None,
            "auth_resolved": False,
            "auth_missing": False,
        }
        if provider.status != ProviderIntegrationStatus.ACTIVE:
            status = ProviderHealthStatus.UNHEALTHY
            metadata["execution_blocked"] = True
            metadata["reason"] = "provider_not_active"
            return self.record_health_check(
                provider_id,
                status=status,
                latency_ms=0,
                error_text=None,
                metadata_json=metadata,
            )
        if adapter_requires_auth(provider.adapter_kind, model.config_json):
            try:
                resolved = self._secret_resolver.resolve_auth_ref(model.auth_ref)
                metadata["auth_resolved"] = resolved is not None
            except ProviderSecretMissingError:
                status = ProviderHealthStatus.UNHEALTHY
                metadata["auth_missing"] = True
                metadata["auth_resolved"] = False
        return self.record_health_check(
            provider_id,
            status=status,
            latency_ms=0,
            error_text=None,
            metadata_json=metadata,
        )

    def record_health_check(
        self,
        provider_id: uuid.UUID,
        *,
        status: ProviderHealthStatus,
        latency_ms: int | None = None,
        error_text: str | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> ProviderHealthCheckRead:
        if self._session.get(ProviderIntegration, provider_id) is None:
            raise ProviderNotFoundError("provider integration not found")
        safe_metadata = {} if metadata_json is None else sanitize_for_persistence(metadata_json)
        reject_sensitive_config(safe_metadata, field_name="metadata_json")
        model = ProviderHealthCheck(
            id=uuid.uuid4(),
            provider_integration_id=provider_id,
            status=status.value,
            latency_ms=latency_ms,
            checked_at=datetime.now(UTC),
            error_text=(
                None
                if error_text is None
                else sanitize_provider_diagnostic_text(error_text)
            ),
            metadata_json=safe_metadata,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _health_record(model)

    def list_health_checks(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
        *,
        platform_admin: bool = False,
        limit: int = 50,
    ) -> list[ProviderHealthCheckRead]:
        provider = ProviderRegistryService(self._session).get_provider(
            world_id,
            provider_id,
            platform_admin=platform_admin,
        )
        if provider is None:
            raise ProviderNotFoundError("provider integration not found")
        statement = (
            select(ProviderHealthCheck)
            .where(ProviderHealthCheck.provider_integration_id == provider_id)
            .order_by(ProviderHealthCheck.checked_at.desc())
            .limit(limit)
        )
        return [_health_record(model) for model in self._session.scalars(statement).all()]


def _health_record(model: ProviderHealthCheck) -> ProviderHealthCheckRead:
    return ProviderHealthCheckRead(
        id=model.id,
        provider_integration_id=model.provider_integration_id,
        status=ProviderHealthStatus(model.status),
        latency_ms=model.latency_ms,
        checked_at=model.checked_at,
        error_text=model.error_text,
        metadata_json=model.metadata_json,
    )
