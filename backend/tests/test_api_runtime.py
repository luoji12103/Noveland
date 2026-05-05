from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from fastapi.testclient import TestClient
from noveland.adapters.models import ProviderProfile
from noveland.agents.models import Agent, AgentPersona, AgentRuntimeRun
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.core.models import RuntimeControlState
from noveland.core.settings import load_settings
from noveland.events.models import WorldEventModel, WorldSnapshotModel
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
    supervision = client.get("/runtime/supervision")
    tool_policy = client.get("/runtime/tool-policy")
    _seed_runtime_diagnostic(engine)
    diagnostics = client.get("/runtime/diagnostics")
    metrics = client.get("/metrics")
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
    provider_health = client.get("/provider-profiles/health")
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
    assert status.json()["runtime_health"]["status"] == "stopped"
    assert status.json()["runtime_health"]["recent_error_count"] == 0
    assert supervision.status_code == 200
    assert supervision.json()["api_status"] == "ok"
    assert supervision.json()["database_status"] == "ok"
    assert supervision.json()["runtime_process_expected"] is False
    assert tool_policy.status_code == 200
    assert tool_policy.json()["policy_mode"] == "policy_only"
    assert tool_policy.json()["execution_enabled"] is False
    assert tool_policy.json()["runtime_execution_enabled"] is False
    assert tool_policy.json()["default_permission_mode"] == "disabled"
    assert "secret-token" not in tool_policy.text
    assert metrics.status_code == 200
    assert "noveland_runtime_desired_state" in metrics.text
    assert 'noveland_memory_write_jobs{status="failed"}' in metrics.text
    assert "secret" not in metrics.text
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
    assert provider_health.status_code == 200
    assert provider_health.json()[0]["profile_key"] == "openai-local"
    assert provider_health.json()[0]["health"] == "configuration_error"
    assert provider_health.json()[0]["api_key_ref"] == "openai-local"
    assert provider_health.json()[0]["secret_ref_status"] == "missing"
    assert "NOVELAND_PROVIDER_API_KEYS_JSON" in provider_health.json()[0]["secret_ref_message"]
    assert provider_health.json()[0]["missing_secret_ref"] is True
    assert provider_health.json()[0]["recent_error_count"] == 1
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
    dry_run = client.get("/memory-backfill/dry-run?limit=20")
    execute_backfill = client.post("/memory-backfill/execute?limit=20")
    queue_readiness = client.get("/memory-queue/readiness")
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
    assert jobs.json()["jobs"][0]["is_retryable"] is True
    assert jobs.json()["jobs"][0]["terminal_reason"] is None
    assert jobs.json()["jobs"][0]["last_log_success"] is False
    assert retry_job.status_code == 200
    assert retry_job.json()["status"] == "pending"
    assert retry_job.json()["last_error"] is None
    assert status_after_retry.status_code == 200
    assert status_after_retry.json()["memory_write_jobs"]["pending_count"] == 1
    assert status_after_retry.json()["memory_write_jobs"]["failed_count"] == 0
    assert status_after_retry.json()["memory_write_jobs"]["retryable_failed_count"] == 0
    assert status_after_retry.json()["runtime_health"]["status"] == "stopped"
    assert dry_run.status_code == 200
    assert dry_run.json()["candidate_count"] == 1
    assert dry_run.json()["skipped_existing_count"] == 0
    assert {
        summary["source_kind"]: summary for summary in dry_run.json()["source_summaries"]
    }["agent_run"]["candidate_count"] == 1
    assert execute_backfill.status_code == 200
    assert execute_backfill.json()["enqueued_count"] == 1
    assert execute_backfill.json()["dry_run_before"]["candidate_count"] == 1
    assert queue_readiness.status_code == 200
    assert queue_readiness.json()["external_queue_ready"] is True
    assert queue_readiness.json()["issues"] == []
    assert eval_smoke.status_code == 200
    assert eval_smoke.json()["case_count"] == 1
    assert eval_smoke.json()["hit_case_count"] == 1
    assert eval_smoke.json()["recommendations"] == [
        "Memory eval is healthy for the sampled retrieval logs.",
    ]
    assert update_profile.status_code == 200
    assert update_profile.json()["is_enabled"] is False


def test_non_platform_admin_cannot_access_runtime_surface() -> None:
    client, engine = _client_with_database()
    _user_id, token = _seed_user(engine, "member@example.test", platform_admin=False)
    _authenticate(client, token)

    control = client.get("/runtime/control")
    diagnostics = client.get("/runtime/diagnostics")
    retention = client.get("/runtime/diagnostics/retention")
    prune = client.post("/runtime/diagnostics/prune")
    supervision = client.get("/runtime/supervision")
    tool_policy = client.get("/runtime/tool-policy")
    scale_readiness = client.get("/runtime/scale-readiness")
    metrics = client.get("/metrics")
    profiles = client.get("/provider-profiles")
    provider_health = client.get("/provider-profiles/health")
    plugin_bindings = client.get("/plugins/bindings")
    memory_jobs = client.get(f"/memory-backend-profiles/{uuid.uuid4()}/jobs")
    retry_memory_job = client.post(f"/memory-write-jobs/{uuid.uuid4()}/retry")
    memory_backfill = client.get("/memory-backfill/dry-run")
    memory_backfill_execute = client.post("/memory-backfill/execute")
    memory_queue_readiness = client.get("/memory-queue/readiness")

    assert control.status_code == 403
    assert diagnostics.status_code == 403
    assert retention.status_code == 403
    assert prune.status_code == 403
    assert supervision.status_code == 403
    assert tool_policy.status_code == 403
    assert scale_readiness.status_code == 403
    assert metrics.status_code == 403
    assert profiles.status_code == 403
    assert provider_health.status_code == 403
    assert plugin_bindings.status_code == 403
    assert memory_jobs.status_code == 403
    assert retry_memory_job.status_code == 403
    assert memory_backfill.status_code == 403
    assert memory_backfill_execute.status_code == 403
    assert memory_queue_readiness.status_code == 403


def test_platform_admin_dry_runs_and_prunes_diagnostic_retention() -> None:
    client, engine = _client_with_database()
    _user_id, token = _seed_user(engine, "platform@example.test", platform_admin=True)
    _authenticate(client, token)
    now = datetime.now(UTC)
    with Session(engine) as session:
        RuntimeDiagnosticsService(session).record(
            RuntimeDiagnosticCreate(
                severity=DiagnosticSeverity.INFO,
                component=DiagnosticComponent.RUNTIME,
                event_type="runtime.old",
                message="Old runtime diagnostic",
                details={},
                occurred_at=now - timedelta(days=60),
            ),
        )
        RuntimeDiagnosticsService(session).record(
            RuntimeDiagnosticCreate(
                severity=DiagnosticSeverity.INFO,
                component=DiagnosticComponent.RUNTIME,
                event_type="runtime.recent",
                message="Recent runtime diagnostic",
                details={},
                occurred_at=now,
            ),
        )
        session.commit()

    dry_run = client.get("/runtime/diagnostics/retention?retention_days=30")
    prune = client.post("/runtime/diagnostics/prune?retention_days=30&limit=10")
    diagnostics = client.get("/runtime/diagnostics?limit=10")

    assert dry_run.status_code == 200
    assert dry_run.json()["pruneable_count"] == 1
    assert dry_run.json()["retained_count"] == 1
    assert dry_run.json()["pruned_count"] is None
    assert prune.status_code == 200
    assert prune.json()["pruned_count"] == 1
    assert prune.json()["pruneable_count"] == 0
    assert [item["event_type"] for item in diagnostics.json()] == ["runtime.recent"]


def test_platform_admin_gets_scale_readiness_report() -> None:
    client, engine = _client_with_database()
    owner_id, token = _seed_user(engine, "platform@example.test", platform_admin=True)
    world_id = _seed_world(engine, owner_id, "scale-world")
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
    _seed_memory_backend_logs(engine, profile_id, world_id, agent_id)
    provider = client.post(
        "/provider-profiles",
        json={
            "profile_key": "openai-local",
            "name": "OpenAI Local",
            "provider_type": "openai_compatible",
            "base_url": "https://api.example.test/v1",
            "model_name": "gpt-test",
            "capabilities": {},
            "api_key_ref": "missing-provider-secret",
        },
    )

    report = client.get("/runtime/scale-readiness")

    assert provider.status_code == 201
    assert report.status_code == 200
    assert report.json()["status"] == "blocked"
    assert report.json()["section_count"] == 6
    sections = {section["area"]: section for section in report.json()["sections"]}
    assert sections["database_indexes"]["metrics"]["world_count"] == 1
    assert sections["memory_queue_throughput"]["status"] == "watch"
    assert sections["memory_queue_throughput"]["metrics"]["failed_count"] == 1
    assert sections["provider_limits"]["status"] == "blocked"
    assert sections["provider_limits"]["metrics"]["unhealthy_enabled_profile_count"] == 1
    assert sections["snapshot_storage"]["metrics"]["snapshot_count"] == 0
    assert "missing-provider-secret" not in report.text


def test_provider_health_reports_secret_ref_statuses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "NOVELAND_PROVIDER_API_KEYS_JSON",
        '{"configured-ref":"secret-key","empty-ref":""}',
    )
    load_settings.cache_clear()
    try:
        client, engine = _client_with_database()
        _user_id, token = _seed_user(engine, "platform@example.test", platform_admin=True)
        _authenticate(client, token)
        for profile_key, api_key_ref in (
            ("configured-provider", "configured-ref"),
            ("empty-provider", "empty-ref"),
            ("missing-provider", "missing-ref"),
        ):
            response = client.post(
                "/provider-profiles",
                json={
                    "profile_key": profile_key,
                    "name": profile_key,
                    "provider_type": "openai_compatible",
                    "base_url": "https://api.example.test/v1",
                    "model_name": "gpt-test",
                    "capabilities": {},
                    "api_key_ref": api_key_ref,
                },
            )
            assert response.status_code == 201

        health = client.get("/provider-profiles/health")

        assert health.status_code == 200
        assert "secret-key" not in health.text
        records = {record["profile_key"]: record for record in health.json()}
        assert records["configured-provider"]["api_key_ref"] == "configured-ref"
        assert records["configured-provider"]["secret_ref_status"] == "configured"
        assert records["configured-provider"]["secret_ref_message"] is None
        assert records["configured-provider"]["missing_secret_ref"] is False
        assert records["configured-provider"]["health"] == "untested"
        assert records["empty-provider"]["secret_ref_status"] == "empty"
        assert records["empty-provider"]["missing_secret_ref"] is True
        assert records["empty-provider"]["health"] == "configuration_error"
        assert "empty" in records["empty-provider"]["secret_ref_message"]
        assert records["missing-provider"]["secret_ref_status"] == "missing"
        assert records["missing-provider"]["missing_secret_ref"] is True
        assert records["missing-provider"]["health"] == "configuration_error"
        assert "missing-ref" in records["missing-provider"]["secret_ref_message"]
    finally:
        load_settings.cache_clear()


def test_platform_admin_lists_plugin_bindings_with_validation_status() -> None:
    client, engine = _client_with_database()
    owner_id, token = _seed_user(engine, "platform@example.test", platform_admin=True)
    world_id = _seed_world(engine, owner_id, "plugin-world")
    agent_id = _seed_agent(engine, world_id, "guide")
    _seed_persona_and_conversation_bindings(engine, world_id, agent_id)
    _authenticate(client, token)
    create_profile = client.post(
        "/provider-profiles",
        json={
            "profile_key": "openai-local",
            "name": "OpenAI Local",
            "provider_type": "openai_compatible",
            "plugin_identifier": "builtin.openai_compatible",
            "plugin_config": {"headers": {"X-Test": "1"}},
            "base_url": "https://api.example.test/v1",
            "model_name": "gpt-test",
            "capabilities": {},
            "api_key_ref": "openai-local",
        },
    )

    bindings = client.get("/plugins/bindings")
    model_provider_bindings = client.get("/plugins/bindings?category=model_provider")

    assert create_profile.status_code == 201
    assert bindings.status_code == 200
    records = {
        (record["owner_kind"], record["plugin_identifier"]): record
        for record in bindings.json()
    }
    assert records[("provider_profile", "builtin.openai_compatible")]["validation_status"] == "ok"
    assert records[("provider_profile", "builtin.openai_compatible")]["config_present"] is True
    assert "X-Test" not in bindings.text
    assert records[("world_memory", "builtin.local_pgvector_memory")]["validation_status"] == "ok"
    assert records[("world_rules", "missing.world_rules")]["validation_status"] == "missing_plugin"
    assert records[("agent_persona", "builtin.openai_compatible")]["validation_status"] == (
        "category_mismatch"
    )
    assert records[("conversation_writer", "builtin.default_narrative_writer")][
        "validation_status"
    ] == "ok"
    assert model_provider_bindings.status_code == 200
    assert {record["category"] for record in model_provider_bindings.json()} == {"model_provider"}


def test_plugin_config_failures_emit_redacted_plugin_diagnostics() -> None:
    client, engine = _client_with_database()
    _user_id, token = _seed_user(engine, "platform@example.test", platform_admin=True)
    _authenticate(client, token)

    response = client.post(
        "/provider-profiles",
        json={
            "profile_key": "bad-plugin",
            "name": "Bad Plugin",
            "provider_type": "openai_compatible",
            "plugin_identifier": "builtin.openai_compatible",
            "plugin_config": {
                "headers": {"Authorization": "secret-token"},
                "unexpected": "not allowed",
            },
            "base_url": "https://api.example.test/v1",
            "model_name": "gpt-test",
            "capabilities": {},
            "api_key_ref": "openai-local",
        },
    )
    diagnostics = client.get("/runtime/diagnostics?component=plugin")

    assert response.status_code == 422
    assert diagnostics.status_code == 200
    assert diagnostics.json()[0]["component"] == "plugin"
    assert diagnostics.json()[0]["event_type"] == "plugin.binding_invalid_config"
    assert diagnostics.json()[0]["details"] == {
        "plugin_identifier": "builtin.openai_compatible",
        "category": "model_provider",
        "owner_kind": "provider_profile",
        "owner_key": "bad-plugin",
    }
    assert "secret-token" not in diagnostics.text


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
        AgentPersona.__table__,
        WorldScheduleRule.__table__,
        ConversationSession.__table__,
        ConversationTurn.__table__,
        WorldEventModel.__table__,
        WorldSnapshotModel.__table__,
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


def _seed_persona_and_conversation_bindings(
    engine: Engine,
    world_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> None:
    with Session(engine) as session:
        world = session.get(World, world_id)
        assert world is not None
        world.world_rules_plugin_identifier = "missing.world_rules"
        session.add(
            AgentPersona(
                world_id=world_id,
                agent_id=agent_id,
                persona_text="Guide persona",
                behavior_policy={},
                policy_plugin_identifier="builtin.openai_compatible",
                policy_plugin_config={},
                is_enabled=True,
            )
        )
        session.add(
            ConversationSession(
                world_id=world_id,
                session_key="plugin-conversation",
                title="Plugin Conversation",
                scope_type="world",
                mode="manual_chain",
                status="draft",
                objective="",
                opening_prompt="",
                max_turns=4,
                next_turn_index=0,
                policy_config={},
                writer_config={
                    "writer_plugin_identifier": "builtin.default_narrative_writer",
                    "writer_plugin_config": {},
                },
                memory_config={},
            )
        )
        session.commit()


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
        agent_run = AgentRuntimeRun(
            world_id=world_id,
            agent_id=agent_id,
            status="succeeded",
            trigger_source="runtime_tick",
            prompt_text="Store this memory.",
            response_text="Stored memory response.",
            diagnostics={},
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
        session.add(agent_run)
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
            MemoryWriteLog(
                job_id=failed_job.id,
                backend="local_pgvector",
                success=False,
                latency_ms=None,
                request_summary={"source": "runtime"},
                response_summary={"error": "backend timeout"},
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
