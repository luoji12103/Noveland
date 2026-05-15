from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi.testclient import TestClient
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.events.models import WorldEventModel, WorldSnapshotModel
from noveland.invocations.models import ModelInvocation
from noveland.media.models import MediaAsset, MediaJob, MediaObject
from noveland.observability import (
    DiagnosticComponent,
    DiagnosticSeverity,
    ProductionReadinessGateService,
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
from noveland.worlds.models import (
    BetaChecklistItem,
    BetaChecklistRun,
    LivingWorldReleaseProfile,
    LongRunEvalRun,
    World,
    Worldline,
)
from sqlalchemy import Table, create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

FORBIDDEN_RESPONSE_TOKENS = (
    "sk-live-secret",
    "Bearer",
    "storage_uri",
    "media://private-object",
    "/tmp/private-file",
    "raw prompt",
    "raw output",
    "base64",
)


@dataclass(frozen=True, slots=True)
class _StorageAuditStub:
    status: str = "ok"
    finding_count: int = 0


def test_production_readiness_report_aggregates_existing_safe_evidence() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    _seed_ready_evidence(engine, world_id, worldline_id)

    with Session(engine) as session:
        report = ProductionReadinessGateService(session).report(
            world_id=world_id,
            storage_audit=_StorageAuditStub(),
        )

    sections = {section.section_key: section for section in report.sections}
    assert report.status == "ok"
    assert report.readiness_kind == "internal_production_readiness"
    assert report.blocker_count == 0
    assert sections["release_profile"].status == "ok"
    assert sections["beta_checklist"].status == "ok"
    assert sections["long_run_eval"].status == "ok"
    assert sections["provider_governance"].summary.startswith("1 active providers")
    assert sections["budget_controls"].status == "ok"
    assert sections["storage_integrity"].status == "ok"
    assert sections["security_regression"].evidence_refs[0].id == (
        "v0.7-security-regression-suite"
    )
    assert "public_launch_gate" in report.non_goals


def test_production_readiness_report_blocks_missing_or_failed_evidence_safely() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    _seed_blocking_evidence(engine, world_id, worldline_id)

    with Session(engine) as session:
        before_counts = _framework_counts(session)
        report = ProductionReadinessGateService(session).report(
            world_id=world_id,
            storage_audit=_StorageAuditStub(status="error", finding_count=2),
        )
        after_counts = _framework_counts(session)

    sections = {section.section_key: section for section in report.sections}
    assert report.status == "blocked"
    assert report.blocker_count >= 1
    assert sections["storage_integrity"].status == "blocked"
    assert sections["incident_diagnostics"].status == "blocked"
    assert before_counts == after_counts

    response_text = report.model_dump_json()
    for token in FORBIDDEN_RESPONSE_TOKENS:
        assert token not in response_text


def test_production_readiness_endpoint_is_platform_admin_only_and_safe() -> None:
    client, engine = _client_with_database()
    platform_user_id, platform_token = _seed_user(
        engine,
        "platform-readiness@example.test",
        platform_admin=True,
    )
    world_id, worldline_id = _seed_world(engine, owner_user_id=platform_user_id)
    _seed_blocking_evidence(engine, world_id, worldline_id)
    _authenticate(client, platform_token)

    response = client.get(f"/observability/readiness/production?world_id={world_id}")

    assert response.status_code == 200
    assert response.json()["readiness_kind"] == "internal_production_readiness"
    assert response.json()["world_id"] == str(world_id)
    assert response.json()["status"] == "blocked"
    for token in FORBIDDEN_RESPONSE_TOKENS:
        assert token not in response.text

    _member_id, member_token = _seed_user(engine, "member-readiness@example.test", False)
    _authenticate(client, member_token)
    forbidden = client.get("/observability/readiness/production")
    assert forbidden.status_code == 403
    for token in FORBIDDEN_RESPONSE_TOKENS:
        assert token not in forbidden.text


def test_production_readiness_does_not_create_duplicate_framework_tables() -> None:
    table_names = {
        "beta_checklist_runs",
        "beta_checklist_items",
        "long_run_eval_runs",
        "living_world_release_profiles",
    }
    assert "production_readiness_runs" not in table_names
    assert "production_readiness_reports" not in table_names


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
        World.__table__,
        Worldline.__table__,
        WorldEventModel.__table__,
        WorldSnapshotModel.__table__,
        MediaAsset.__table__,
        MediaObject.__table__,
        MediaJob.__table__,
        ModelInvocation.__table__,
        RuntimeDiagnosticEvent.__table__,
        ProviderIntegration.__table__,
        ProviderHealthCheck.__table__,
        ProviderBudgetPolicy.__table__,
        LongRunEvalRun.__table__,
        LivingWorldReleaseProfile.__table__,
        BetaChecklistRun.__table__,
        BetaChecklistItem.__table__,
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


def _seed_world(
    engine: Engine,
    *,
    owner_user_id: uuid.UUID | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    user_id = owner_user_id or uuid.uuid4()
    world_id = uuid.uuid4()
    worldline_id = uuid.uuid4()
    with Session(engine) as session:
        if owner_user_id is None:
            session.add(
                User(
                    id=user_id,
                    email=f"readiness-{world_id.hex[:8]}@example.test",
                    display_name="Readiness Owner",
                ),
            )
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug=f"readiness-{world_id.hex[:8]}",
                name="Readiness World",
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


def _seed_ready_evidence(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> None:
    now = datetime.now(UTC)
    provider_id = uuid.uuid4()
    checklist_id = uuid.uuid4()
    with Session(engine) as session:
        _seed_release_eval_and_checklist(
            session,
            world_id,
            worldline_id,
            checklist_id=checklist_id,
            checklist_status="passed",
            long_run_status="completed",
            multimodal_status="completed",
            narrative_status="completed",
            release_status="ready",
            now=now,
        )
        session.add(
            ProviderIntegration(
                id=provider_id,
                world_id=world_id,
                scope_kind="world",
                scope_key=str(world_id),
                provider_kind="text_generation",
                adapter_kind="fake",
                provider_key="readiness-provider",
                display_name="Readiness Provider",
                base_url=None,
                auth_ref="env:OPENAI_API_KEY",
                config_json={},
                default_params_json={},
                status="active",
                visibility="world_admin",
            ),
        )
        session.add(
            ProviderBudgetPolicy(
                id=uuid.uuid4(),
                world_id=world_id,
                provider_id=provider_id,
                policy_key="readiness-budget",
                status="active",
                emergency_stop_enabled=False,
                limits_json={"max_daily_estimated_cost": 10},
                metadata_json={},
            ),
        )
        session.commit()


def _seed_blocking_evidence(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> None:
    now = datetime.now(UTC)
    provider_id = uuid.uuid4()
    checklist_id = uuid.uuid4()
    with Session(engine) as session:
        _seed_release_eval_and_checklist(
            session,
            world_id,
            worldline_id,
            checklist_id=checklist_id,
            checklist_status="blocked",
            long_run_status="failed",
            multimodal_status="failed",
            narrative_status="warning",
            release_status="blocked",
            now=now,
        )
        RuntimeDiagnosticsService(session).record(
            RuntimeDiagnosticCreate(
                severity=DiagnosticSeverity.ERROR,
                component=DiagnosticComponent.RUNTIME,
                event_type="readiness.failed",
                message="runtime failed with sk-live-secret and /tmp/private-file",
                details={"authorization": "Bearer sk-live-secret"},
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
                provider_key="blocked-provider",
                display_name="Blocked Provider",
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
            ProviderBudgetPolicy(
                id=uuid.uuid4(),
                world_id=world_id,
                provider_id=provider_id,
                policy_key="blocked-budget",
                status="active",
                emergency_stop_enabled=True,
                limits_json={"max_daily_estimated_cost": 1},
                metadata_json={},
            ),
        )
        session.commit()


def _seed_release_eval_and_checklist(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    checklist_id: uuid.UUID,
    checklist_status: str,
    long_run_status: str,
    multimodal_status: str,
    narrative_status: str,
    release_status: str,
    now: datetime,
) -> None:
    session.add(
        LivingWorldReleaseProfile(
            id=uuid.uuid4(),
            world_id=world_id,
            profile_key="default",
            status=release_status,
            branch_policy={},
            backup_policy={},
            content_review_policy={},
            player_permission_policy={},
            worldline_policy={},
            checklist={},
            metadata_json={},
        ),
    )
    session.add(
        BetaChecklistRun(
            id=checklist_id,
            world_id=world_id,
            worldline_id=worldline_id,
            run_key="beta-readiness",
            status=checklist_status,
            summary="safe summary",
            evidence={"refs": []},
            blocker_count=0 if checklist_status == "passed" else 1,
            created_by_actor_ref="system:test",
            metadata_json={},
        ),
    )
    session.add(
        BetaChecklistItem(
            id=uuid.uuid4(),
            run_id=checklist_id,
            item_key="safe-check",
            title="Safe check",
            status=checklist_status,
            evidence={},
            recommendation=None,
        ),
    )
    for eval_key, status in (
        ("long-run-seven-day", long_run_status),
        ("multimodal-smoke", multimodal_status),
        ("narrative-quality-seven-day", narrative_status),
    ):
        session.add(
            LongRunEvalRun(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                eval_key=eval_key,
                horizon_days=7,
                status=status,
                started_at=now,
                finished_at=now,
                metrics={},
                recommendations=[],
                blockers=[],
                metadata_json={},
            ),
        )


def _framework_counts(session: Session) -> tuple[int, int, int]:
    return (
        int(session.scalar(select(func.count(BetaChecklistRun.id))) or 0),
        int(session.scalar(select(func.count(LongRunEvalRun.id))) or 0),
        int(session.scalar(select(func.count(LivingWorldReleaseProfile.id))) or 0),
    )
