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
from noveland.memory.models import (
    AgentMemoryItem,
    MemoryBackendProfile,
    MemoryRetrievalLog,
    MemoryWriteJob,
    MemoryWriteLog,
)
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
    assert status.json()["memory_write_jobs"]["failed_count"] == 0
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


def test_platform_admin_manages_memory_backend_profiles_and_ops_surface() -> None:
    client, engine = _client_with_database()
    owner_id, token = _seed_user(engine, "platform@example.test", platform_admin=True)
    world_id = _seed_world(engine, owner_id, "memory-admin")
    agent_id = _seed_agent(engine, world_id, "guide")
    _authenticate(client, token)

    create_profile = client.post(
        "/memory-backend-profiles",
        json={
            "profile_key": "local-memory",
            "name": "Local memory",
            "backend_kind": "local_pgvector",
            "vector_store_config": {},
            "llm_config": {},
            "embedder_config": {},
            "reranker_config": {},
            "secret_refs": {},
        },
    )
    profile_id = uuid.UUID(create_profile.json()["id"])
    _attach_world_memory_profile(engine, world_id, profile_id)
    failed_job_id = _seed_memory_backend_logs(engine, profile_id, world_id, agent_id)

    list_profiles = client.get("/memory-backend-profiles")
    health = client.get(f"/memory-backend-profiles/{profile_id}/health")
    logs = client.get(f"/memory-backend-profiles/{profile_id}/logs?limit=5")
    jobs = client.get(f"/memory-backend-profiles/{profile_id}/jobs?status=failed&limit=5")
    retry_job = client.post(f"/memory-write-jobs/{failed_job_id}/retry")
    status_after_retry = client.get("/runtime/status")
    eval_smoke = client.post(f"/memory-backend-profiles/{profile_id}/eval-smoke")
    update_profile = client.patch(
        f"/memory-backend-profiles/{profile_id}",
        json={"name": "Local memory updated", "is_enabled": False},
    )

    assert create_profile.status_code == 201
    assert list_profiles.status_code == 200
    assert list_profiles.json()[0]["profile_key"] == "local-memory"
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert logs.status_code == 200
    assert logs.json()["write_logs"][0]["backend"] == "local_pgvector"
    assert logs.json()["retrieval_logs"][0]["query_text"] == "Stored memory"
    assert jobs.status_code == 200
    assert jobs.json()["jobs"][0]["id"] == str(failed_job_id)
    assert jobs.json()["jobs"][0]["last_error"] == "backend timeout"
    assert retry_job.status_code == 200
    assert retry_job.json()["status"] == "pending"
    assert retry_job.json()["last_error"] is None
    assert status_after_retry.status_code == 200
    assert status_after_retry.json()["memory_write_jobs"]["pending_count"] == 1
    assert status_after_retry.json()["memory_write_jobs"]["failed_count"] == 0
    assert eval_smoke.status_code == 200
    assert eval_smoke.json()["case_count"] == 1
    assert eval_smoke.json()["hit_case_count"] == 1
    assert update_profile.status_code == 200
    assert update_profile.json()["is_enabled"] is False


def test_non_platform_admin_cannot_access_runtime_surface() -> None:
    client, engine = _client_with_database()
    _user_id, token = _seed_user(engine, "member@example.test", platform_admin=False)
    _authenticate(client, token)

    control = client.get("/runtime/control")
    diagnostics = client.get("/runtime/diagnostics")
    profiles = client.get("/provider-profiles")
    memory_jobs = client.get(f"/memory-backend-profiles/{uuid.uuid4()}/jobs")
    retry_memory_job = client.post(f"/memory-write-jobs/{uuid.uuid4()}/retry")

    assert control.status_code == 403
    assert diagnostics.status_code == 403
    assert profiles.status_code == 403
    assert memory_jobs.status_code == 403
    assert retry_memory_job.status_code == 403


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
        MemoryBackendProfile.__table__,
        Agent.__table__,
        WorldScheduleRule.__table__,
        WorldEventModel.__table__,
        AgentMemoryItem.__table__,
        MemoryWriteJob.__table__,
        MemoryWriteLog.__table__,
        MemoryRetrievalLog.__table__,
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


def _seed_world(engine: Engine, owner_user_id: uuid.UUID, slug: str) -> uuid.UUID:
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=owner_user_id,
                slug=slug,
                name=slug,
                rules_config={},
            ),
        )
        session.commit()
    return world_id


def _seed_agent(engine: Engine, world_id: uuid.UUID, agent_key: str) -> uuid.UUID:
    agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key=agent_key,
                display_name=agent_key,
                kind="role_agent",
                config={},
            ),
        )
        session.commit()
    return agent_id


def _attach_world_memory_profile(
    engine: Engine,
    world_id: uuid.UUID,
    profile_id: uuid.UUID,
) -> None:
    with Session(engine) as session:
        world = session.get(World, world_id)
        assert world is not None
        world.memory_backend_profile_id = profile_id
        session.commit()


def _seed_memory_backend_logs(
    engine: Engine,
    profile_id: uuid.UUID,
    world_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> uuid.UUID:
    with Session(engine) as session:
        memory_item = AgentMemoryItem(
            world_id=world_id,
            agent_id=agent_id,
            content="Stored memory",
            metadata_json={"source": "runtime"},
            embedding=[0.5] * 1536,
            visibility="private",
            is_active=True,
        )
        session.add(memory_item)
        session.flush()
        job = MemoryWriteJob(
            world_id=world_id,
            agent_id=agent_id,
            backend_profile_id=profile_id,
            source_kind="agent_run",
            source_id=uuid.uuid4(),
            payload_json={"content": "Stored memory"},
            dedupe_key="memory-job-1",
            status="succeeded",
            attempt_count=1,
            next_attempt_at=datetime.now(UTC),
        )
        session.add(job)
        session.flush()
        failed_job = MemoryWriteJob(
            world_id=world_id,
            agent_id=agent_id,
            backend_profile_id=profile_id,
            source_kind="conversation_turn",
            source_id=uuid.uuid4(),
            payload_json={"content": "Failed memory"},
            dedupe_key="memory-job-failed",
            status="failed",
            attempt_count=2,
            next_attempt_at=datetime.now(UTC),
            last_error="backend timeout",
        )
        session.add(failed_job)
        session.flush()
        failed_job_id = failed_job.id
        session.add(
            MemoryWriteLog(
                job_id=job.id,
                backend="local_pgvector",
                success=True,
                latency_ms=5,
                request_summary={"source": "runtime"},
                response_summary={"recorded_count": 1},
                correlation_ids={"world_id": str(world_id), "agent_id": str(agent_id)},
            )
        )
        session.add(
            MemoryRetrievalLog(
                world_id=world_id,
                agent_id=agent_id,
                backend_profile_id=profile_id,
                backend="local_pgvector",
                query_text="Stored memory",
                hit_count=1,
                selected_item_ids=[str(memory_item.id)],
                latency_ms=4,
                context_item_count=1,
            )
        )
        session.commit()
    return failed_job_id
