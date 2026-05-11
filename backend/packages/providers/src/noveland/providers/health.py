from __future__ import annotations

import uuid
from datetime import UTC, datetime

from noveland.providers.contracts import ProviderHealthCheckRead, ProviderHealthStatus
from noveland.providers.models import ProviderHealthCheck, ProviderIntegration
from noveland.providers.registry import ProviderNotFoundError, ProviderRegistryService
from sqlalchemy.orm import Session


class ProviderHealthService:
    def __init__(self, session: Session) -> None:
        self._session = session

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
        status = ProviderHealthStatus.HEALTHY
        metadata: dict[str, object] = {
            "adapter_kind": provider.adapter_kind.value,
            "provider_kind": provider.provider_kind.value,
            "provider_key": provider.provider_key,
        }
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
        model = ProviderHealthCheck(
            id=uuid.uuid4(),
            provider_integration_id=provider_id,
            status=status.value,
            latency_ms=latency_ms,
            checked_at=datetime.now(UTC),
            error_text=error_text,
            metadata_json={} if metadata_json is None else dict(metadata_json),
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _health_record(model)


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
