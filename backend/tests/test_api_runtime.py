from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi.testclient import TestClient
from noveland.adapters.models import ProviderProfile
from noveland.agents.models import Agent, AgentRuntimeRun
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.core.models import RuntimeControlState
from noveland.events.models import WorldEventModel
from noveland.observability import (
    DiagnosticComponent,
    DiagnosticSeverity,
    RuntimeDiagnosticCreate,
    RuntimeDiagnosticsService,
)
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import Scene, World
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_platform_admin_controls_runtime_and_provider_profiles() -> None:
    client, engine = _client_with_database()
    _user_id, token = _seed_user(engine, "platform@example.test", platform_admin=True)
    _authenticate(client, token)

    control = client.get("/runtime/control")
    status = client.get("/runtime/status")
    _seed_runtime_diagnostic(engine)
    diagnostics = client.get("/runtime/diagnostics")
    start_runtime = client.patch("/runtime/control", json={"desired_state": "running"})
    create_profile = client.post(
        "/provider-profiles",
        json={
            "profile_key": "openai-local",
            "name": "OpenAI Local",
            "provider_type": "openai_compatible",
            "base_url": "https://api.example.test/v1",
            "model_name": "gpt-test",
            "capabilities": {},
            "api_key_ref": "openai-local",
        },
    )
    list_profiles = client.get("/provider-profiles")
    test_profile = client.post(
        f"/provider-profiles/{create_profile.json()['id']}/test-call",
        json={"prompt": "Reply with OK."},
    )
    update_profile = client.patch(
        f"/provider-profiles/{create_profile.json()['id']}",
        json={
            "name": "OpenAI Updated",
            "timeout_seconds": 15,
            "retry_attempts": 2,
            "rate_limit_per_minute": 30,
            "is_enabled": False,
        },
    )
    disable_profile = client.delete(f"/provider-profiles/{create_profile.json()['id']}")

    assert control.status_code == 200
    assert control.json()["desired_state"] == "stopped"
    assert status.status_code == 200
    assert status.json()["runtime_loop_interval_seconds"] == 5
    assert diagnostics.status_code == 200
    assert diagnostics.json()[0]["event_type"] == "runtime.test"
    assert diagnostics.json()[0]["details"]["token"] == "[redacted]"
    assert start_runtime.status_code == 200
    assert start_runtime.json()["desired_state"] == "running"
    assert create_profile.status_code == 201
    assert create_profile.json()["timeout_seconds"] == 20
    assert list_profiles.status_code == 200
    assert list_profiles.json()[0]["profile_key"] == "openai-local"
    assert test_profile.status_code == 200
    assert test_profile.json()["status"] == "failed"
    assert test_profile.json()["error_code"] == "configuration"
    assert update_profile.status_code == 200
    assert update_profile.json()["name"] == "OpenAI Updated"
    assert update_profile.json()["timeout_seconds"] == 15
    assert update_profile.json()["retry_attempts"] == 2
    assert update_profile.json()["rate_limit_per_minute"] == 30
    assert update_profile.json()["is_enabled"] is False
    assert disable_profile.status_code == 204


def test_non_platform_admin_cannot_access_runtime_surface() -> None:
    client, engine = _client_with_database()
    _user_id, token = _seed_user(engine, "member@example.test", platform_admin=False)
    _authenticate(client, token)

    control = client.get("/runtime/control")
    diagnostics = client.get("/runtime/diagnostics")
    profiles = client.get("/provider-profiles")

    assert control.status_code == 403
    assert diagnostics.status_code == 403
    assert profiles.status_code == 403


def _client_with_database() -> tuple[TestClient, Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _create_tables(engine)
    app = create_app()

    def override_get_db_session() -> Iterator[Session]:
        with Session(engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app), engine


def _create_tables(engine: Engine) -> None:
    for table in (
        User.__table__,
        AuthSession.__table__,
        PlatformRoleAssignment.__table__,
        World.__table__,
        Scene.__table__,
        RuntimeControlState.__table__,
        ProviderProfile.__table__,
        Agent.__table__,
        WorldScheduleRule.__table__,
        WorldEventModel.__table__,
        AgentCalendarEntry.__table__,
        AgentRuntimeRun.__table__,
        RuntimeDiagnosticEvent.__table__,
    ):
        table = cast(Table, table)
        table.create(engine)


def _seed_user(engine: Engine, email: str, platform_admin: bool) -> tuple[uuid.UUID, str]:
    user_id = uuid.uuid4()
    token = f"token-{user_id}"
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(User(id=user_id, email=email, display_name=email, is_active=True))
        session.add(
            AuthSession(
                id=uuid.uuid4(),
                user_id=user_id,
                token_hash=hash_session_token(token),
                status=AuthSessionStatus.ACTIVE.value,
                expires_at=now + timedelta(hours=1),
            ),
        )
        if platform_admin:
            session.add(
                PlatformRoleAssignment(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    role=AuthRole.PLATFORM_ADMIN.value,
                    assigned_at=now,
                ),
            )
        session.commit()
    return user_id, token


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _seed_runtime_diagnostic(engine: Engine) -> None:
    with Session(engine) as session:
        RuntimeDiagnosticsService(session).record(
            RuntimeDiagnosticCreate(
                severity=DiagnosticSeverity.ERROR,
                component=DiagnosticComponent.RUNTIME,
                event_type="runtime.test",
                message="Runtime test diagnostic",
                details={"token": "secret", "note": "visible"},
            ),
        )
        session.commit()
