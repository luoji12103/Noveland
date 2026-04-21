from __future__ import annotations

import builtins
import uuid
from datetime import UTC, datetime
from typing import Any

from noveland.observability.contracts import (
    DiagnosticComponent,
    DiagnosticSeverity,
    RuntimeDiagnosticCreate,
    RuntimeDiagnosticRecord,
)
from noveland.observability.models import RuntimeDiagnosticEvent
from sqlalchemy import Select, select
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

    def _records(
        self,
        statement: Select[tuple[RuntimeDiagnosticEvent]],
    ) -> builtins.list[RuntimeDiagnosticRecord]:
        return [_record(model) for model in self._session.scalars(statement).all()]


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
