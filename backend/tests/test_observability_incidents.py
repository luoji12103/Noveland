from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast

from fastapi.testclient import TestClient
from noveland.adapters.models import ProviderProfile
from noveland.agents.models import Agent, AgentRuntimeRun
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.events.models import WorldEventModel, WorldSnapshotModel
from noveland.invocations.models import ModelInvocation
from noveland.media.models import MediaAsset, MediaJob
from noveland.memory.models import MemoryBackendProfile, MemoryWriteJob
from noveland.observability import (
    DiagnosticComponent,
    DiagnosticSeverity,
    IncidentDiagnosticsService,
    RuntimeDiagnosticCreate,
    RuntimeDiagnosticsService,
)
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.providers.models import (
    ProviderBudgetPolicy,
    ProviderHealthCheck,
    ProviderIntegration,
)
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import LongRunEvalRun, World, Worldline
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_incident_summary_aggregates_safe_evidence_refs() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_incident_world(engine)
    _seed_incident_evidence(engine, world_id, worldline_id)

    with Session(engine) as session:
        summary = IncidentDiagnosticsService(session).summary(world_id=world_id)

    components = {component.component: component for component in summary.components}
    assert summary.status == "blocked"
    assert summary.error_count == 6
    assert summary.warning_count == 2
    assert components["runtime_diagnostics"].error_count == 1
    assert components["provider_health"].error_count == 1
    assert components["provider_health"].warning_count == 1
    assert components["provider_budget"].error_count == 1
    assert components["model_invocations"].error_count == 1
    assert components["media_jobs"].error_count == 1
    assert components["multimodal_evals"].error_count == 1
    assert components["narrative_quality"].warning_count == 1
    assert summary.retention.authority == "runtime_diagnostic_events"

    response_text = summary.model_dump_json()
    assert "sk-live-secret" not in response_text
    assert "Bearer" not in response_text
    assert "storage_uri" not in response_text
    assert "media://private-object" not in response_text
    assert "/tmp/private-file" not in response_text
    assert "raw prompt" not in response_text
    assert "raw output" not in response_text
    assert "base64" not in response_text


def test_incident_summary_endpoint_is_platform_admin_only_and_safe() -> None:
    client, engine = _client_with_database()
    platform_user_id, platform_token = _seed_user(
        engine,
        "platform-incidents@example.test",
        platform_admin=True,
    )
    world_id, worldline_id = _seed_incident_world(engine, owner_user_id=platform_user_id)
    _seed_incident_evidence(engine, world_id, worldline_id)
    _authenticate(client, platform_token)

    response = client.get(
        f"/observability/incidents/summary?world_id={world_id}&retention_days=30",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["world_id"] == str(world_id)
    assert response.json()["retention"]["authority"] == "runtime_diagnostic_events"
    assert "sk-live-secret" not in response.text
    assert "storage_uri" not in response.text
    assert "media://private-object" not in response.text
    assert "/tmp/private-file" not in response.text
    assert "raw prompt" not in response.text
    assert "raw output" not in response.text

    _user_id, member_token = _seed_user(engine, "member-incidents@example.test", False)
    _authenticate(client, member_token)
    forbidden = client.get("/observability/incidents/summary")
    assert forbidden.status_code == 403


def test_incident_summary_world_filter_excludes_other_world_evidence() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_incident_world(engine, slug="included-world")
    other_world_id, other_worldline_id = _seed_incident_world(engine, slug="other-world")
    _seed_incident_evidence(engine, world_id, worldline_id)
    _seed_media_failure(engine, other_world_id, other_worldline_id)

    with Session(engine) as session:
        summary = IncidentDiagnosticsService(session).summary(world_id=world_id)
        global_summary = IncidentDiagnosticsService(session).summary()

    included = {component.component: component for component in summary.components}
    global_components = {component.component: component for component in global_summary.components}
    assert included["media_jobs"].error_count == 1
    assert global_components["media_jobs"].error_count == 2
    assert all(
        ref.world_id in {world_id, None}
        for component in summary.components
        for ref in component.evidence_refs
    )


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        User.__table__,
        AuthSession.__table__,
        PlatformRoleAssignment.__table__,
        ProviderProfile.__table__,
        MemoryBackendProfile.__table__,
        World.__table__,
        Worldline.__table__,
        WorldEventModel.__table__,
        WorldSnapshotModel.__table__,
        Agent.__table__,
        AgentRuntimeRun.__table__,
        ConversationSession.__table__,
        ConversationTurn.__table__,
        MediaAsset.__table__,
        MediaJob.__table__,
        MemoryWriteJob.__table__,
        ModelInvocation.__table__,
        RuntimeDiagnosticEvent.__table__,
        ProviderIntegration.__table__,
        ProviderHealthCheck.__table__,
        ProviderBudgetPolicy.__table__,
        LongRunEvalRun.__table__,
    ):
        cast(Table, table).create(engine)
    return engine


def _client_with_database() -> tuple[TestClient, Engine]:
    engine = _engine()
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


def _seed_incident_world(
    engine: Engine,
    *,
    owner_user_id: uuid.UUID | None = None,
    slug: str = "incident-world",
) -> tuple[uuid.UUID, uuid.UUID]:
    user_id = owner_user_id or uuid.uuid4()
    world_id = uuid.uuid4()
    worldline_id = uuid.uuid4()
    with Session(engine) as session:
        if owner_user_id is None:
            session.add(User(id=user_id, email=f"{slug}@example.test", display_name=slug))
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug=slug,
                name=slug,
                rules_config={},
            ),
        )
        session.add(
            Worldline(
                id=worldline_id,
                world_id=world_id,
                worldline_key="primary",
                name="Primary",
                description=None,
                parent_worldline_id=None,
                forked_from_snapshot_id=None,
                fork_event_sequence=None,
                status="active",
                created_by_actor_ref="system:test",
                metadata={},
            ),
        )
        session.commit()
    return world_id, worldline_id


def _seed_incident_evidence(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> None:
    now = datetime.now(UTC)
    provider_id = uuid.uuid4()
    with Session(engine) as session:
        RuntimeDiagnosticsService(session).record(
            RuntimeDiagnosticCreate(
                severity=DiagnosticSeverity.ERROR,
                component=DiagnosticComponent.RUNTIME,
                event_type="runtime.failed",
                message="runtime failed with sk-live-secret and /tmp/private-file",
                details={
                    "authorization": "Bearer sk-live-secret",
                    "storage_uri": "media://private-object",
                    "raw_prompt": "raw prompt text",
                },
                occurred_at=now,
                world_id=world_id,
            ),
        )
        session.add(
            ProviderIntegration(
                id=provider_id,
                world_id=world_id,
                scope_kind="world",
                scope_key=str(world_id),
                provider_kind="text_generation",
                adapter_kind="fake",
                provider_key="incident-provider",
                display_name="Incident Provider",
                base_url=None,
                auth_ref="env:OPENAI_API_KEY",
                config_json={},
                default_params_json={},
                status="active",
                visibility="world_admin",
            ),
        )
        session.add(
            ProviderHealthCheck(
                id=uuid.uuid4(),
                provider_integration_id=provider_id,
                status="unhealthy",
                latency_ms=None,
                checked_at=now,
                error_text="auth failed for sk-live-secret",
                metadata_json={"authorization": "Bearer sk-live-secret"},
            ),
        )
        session.add(
            ProviderHealthCheck(
                id=uuid.uuid4(),
                provider_integration_id=provider_id,
                status="degraded",
                latency_ms=5000,
                checked_at=now - timedelta(minutes=1),
                error_text="slow",
                metadata_json={},
            ),
        )
        session.add(
            ProviderBudgetPolicy(
                id=uuid.uuid4(),
                world_id=world_id,
                provider_id=provider_id,
                policy_key="incident-stop",
                status="active",
                emergency_stop_enabled=True,
                limits_json={"max_daily_estimated_cost": 1},
                metadata_json={"note": "safe"},
            ),
        )
        session.add(
            ModelInvocation(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                trace_id=uuid.uuid4(),
                parent_invocation_id=None,
                invocation_kind="text_to_speech",
                actor_kind="service",
                actor_ref="service:test",
                agent_id=None,
                conversation_id=None,
                turn_id=None,
                world_event_id=None,
                media_job_id=None,
                media_asset_id=None,
                memory_write_job_id=None,
                provider_kind="local_stub",
                provider_profile_id=None,
                model_name="fake",
                model_version=None,
                prompt_template_key=None,
                prompt_template_version=None,
                input_text="raw prompt with sk-live-secret",
                output_text="raw output with media://private-object",
                input_json={"prompt": "raw prompt"},
                output_json={"output": "raw output"},
                request_params_json={"authorization": "Bearer sk-live-secret"},
                response_metadata_json={"storage_uri": "media://private-object"},
                usage_json=None,
                latency_ms=None,
                estimated_cost=Decimal("0"),
                status="failed",
                error_text="/tmp/private-file failed",
                visibility="world_admin",
                redaction_status="redacted",
                retention_policy="local_debug",
                contains_sensitive_context=True,
                purge_after=None,
            ),
        )
        session.add(
            MediaJob(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                conversation_id=None,
                turn_id=None,
                agent_id=None,
                job_kind="image_generation",
                provider_kind="fake",
                status="failed",
                priority=0,
                cancel_policy=None,
                deadline_hint=None,
                dedupe_key=None,
                invalidation_key=None,
                source_event_id=None,
                source_invocation_id=None,
                provider_config_json={"api_key": "sk-live-secret"},
                request_json={"storage_uri": "media://private-object", "bytes": "base64-data"},
                result_json={"raw_output": "raw output"},
                error_text="/tmp/private-file",
                created_by_actor_ref="system:test",
                started_at=None,
                finished_at=now,
            ),
        )
        session.add(
            LongRunEvalRun(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                eval_key="multimodal-smoke",
                horizon_days=7,
                status="failed",
                started_at=now,
                finished_at=now,
                metrics={"storage_uri": "media://private-object"},
                recommendations=[{"message": "repair media"}],
                blockers=[{"message": "raw prompt leak"}],
                metadata_json={},
            ),
        )
        session.add(
            LongRunEvalRun(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                eval_key="narrative-quality-seven-day",
                horizon_days=7,
                status="warning",
                started_at=now,
                finished_at=now,
                metrics={"note": "safe"},
                recommendations=[],
                blockers=[],
                metadata_json={},
            ),
        )
        session.commit()


def _seed_media_failure(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> None:
    with Session(engine) as session:
        session.add(
            MediaJob(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                conversation_id=None,
                turn_id=None,
                agent_id=None,
                job_kind="speech_generation",
                provider_kind="fake",
                status="failed",
                priority=0,
                cancel_policy=None,
                deadline_hint=None,
                dedupe_key=None,
                invalidation_key=None,
                source_event_id=None,
                source_invocation_id=None,
                provider_config_json={},
                request_json={},
                result_json={},
                error_text="other world failure",
                created_by_actor_ref="system:test",
                started_at=None,
                finished_at=None,
            ),
        )
        session.commit()
