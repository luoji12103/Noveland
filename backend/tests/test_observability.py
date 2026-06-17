from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from noveland.adapters.models import ProviderProfile
from noveland.agents.models import Agent, AgentRuntimeRun
from noveland.auth.models import User
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.events.models import WorldEventModel
from noveland.observability import (
    DiagnosticComponent,
    DiagnosticSeverity,
    RuntimeDiagnosticCreate,
    RuntimeDiagnosticsService,
    redact_diagnostic_details,
)
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.worlds.models import Scene, World, Worldline
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_runtime_diagnostic_contract_rejects_naive_occurred_at() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        RuntimeDiagnosticCreate(
            severity=DiagnosticSeverity.INFO,
            component=DiagnosticComponent.RUNTIME,
            event_type="runtime.test",
            message="Runtime test",
            occurred_at=datetime(2026, 4, 17, 12),
        )


def test_diagnostic_details_are_redacted_recursively() -> None:
    details = redact_diagnostic_details(
        {
            "api_key_ref": "safe-ref",
            "authorization": "Bearer secret",
            "nested": {
                "session_token": "token",
                "message": "short",
                "safe_key": (
                    "failed with sk-live-secret media://hidden /tmp/private raw_prompt "
                    "base64,AAAA"
                ),
            },
            "items": [{"cookie": "secret-cookie"}],
        },
    )

    assert details == {
        "api_key_ref": "[redacted]",
        "authorization": "[redacted]",
        "nested": {
            "session_token": "[redacted]",
            "message": "short",
            "safe_key": (
                "failed with [redacted] [redacted] [redacted] [redacted] [redacted]"
            ),
        },
        "items": [{"cookie": "[redacted]"}],
    }


def test_diagnostics_service_records_and_lists_recent_events() -> None:
    engine = _engine()
    world_id = _seed_world(engine)
    old_time = datetime(2026, 4, 17, 11, tzinfo=UTC)
    new_time = old_time + timedelta(minutes=5)

    with Session(engine) as session:
        service = RuntimeDiagnosticsService(session)
        service.record(
            RuntimeDiagnosticCreate(
                severity=DiagnosticSeverity.INFO,
                component=DiagnosticComponent.RUNTIME,
                event_type="runtime.old",
                message="Old event",
                occurred_at=old_time,
                world_id=world_id,
            ),
        )
        new_record = service.record(
            RuntimeDiagnosticCreate(
                severity=DiagnosticSeverity.ERROR,
                component=DiagnosticComponent.PROVIDER,
                event_type="provider.failed.sk-live-secret",
                message="Provider failed with sk-live-secret and /tmp/private-file",
                details={
                    "token": "secret",
                    "error": "timeout from media://hidden raw_output",
                },
                occurred_at=new_time,
                world_id=world_id,
            ),
        )
        session.commit()

    with Session(engine) as session:
        all_records = RuntimeDiagnosticsService(session).list(limit=10)
        provider_records = RuntimeDiagnosticsService(session).list(
            severity=DiagnosticSeverity.ERROR,
            component=DiagnosticComponent.PROVIDER,
        )
        world_records = RuntimeDiagnosticsService(session).list_for_world(world_id)

    assert all_records[0].id == new_record.id
    assert provider_records == [new_record]
    assert world_records[0].event_type == "provider.failed.[redacted]"
    assert world_records[0].message == "Provider failed with [redacted] and [redacted]"
    assert world_records[0].details == {
        "token": "[redacted]",
        "error": "timeout from [redacted] [redacted]",
    }


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        cast(Table, User.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, Scene.__table__),
        cast(Table, ProviderProfile.__table__),
        cast(Table, Agent.__table__),
        cast(Table, WorldScheduleRule.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, AgentCalendarEntry.__table__),
        cast(Table, AgentRuntimeRun.__table__),
        cast(Table, RuntimeDiagnosticEvent.__table__),
    ):
        table.create(engine)
    return engine


def _seed_world(engine: Engine) -> uuid.UUID:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(User(id=user_id, email="diagnostics@example.test", display_name="Diagnostics"))
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug="diagnostics-world",
                name="Diagnostics World",
                rules_config={},
            ),
        )
        session.commit()
    return world_id
