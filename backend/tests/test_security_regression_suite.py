from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.authoring.models import AuthoringImportProposal
from noveland.events.models import WorldEventModel
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import World, Worldline, WorldMembership
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from tests.fixtures.authoring_sample_import import create_authoring_sample_import
from tests.fixtures.multimodal_sample_world import create_multimodal_sample_world
from tests.fixtures.security_regression import (
    FORBIDDEN_PAYLOAD_FIXTURE,
    assert_no_forbidden_tokens,
    contains_forbidden_payload,
)


def test_forbidden_payload_helper_catches_secret_prompt_and_storage_markers() -> None:
    assert contains_forbidden_payload(FORBIDDEN_PAYLOAD_FIXTURE) is True

    safe_projection = {
        "evidence_refs": [{"kind": "model_invocation", "id": str(uuid.uuid4())}],
        "status": "blocked",
        "counts": {"failed": 1},
    }
    assert contains_forbidden_payload(safe_projection) is False
    assert_no_forbidden_tokens(json.dumps(safe_projection))

    with pytest.raises(AssertionError):
        assert_no_forbidden_tokens(json.dumps(FORBIDDEN_PAYLOAD_FIXTURE))


def test_lower_privilege_admin_surfaces_remain_denied_without_forbidden_tokens() -> None:
    client, engine = _client_with_database()
    owner_id, _owner_token = _seed_user(engine, "owner-security@example.test")
    member_id, member_token = _seed_user(engine, "member-security@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    _authenticate(client, member_token)

    conversation_id = uuid.uuid4()
    turn_id = uuid.uuid4()
    member_routes: list[tuple[str, str, dict[str, str] | None]] = [
        ("GET", "/observability/incidents/summary", None),
        ("GET", "/runtime/diagnostics", None),
        ("GET", "/metrics", None),
        ("GET", f"/worlds/{world_id}/providers", None),
        ("GET", f"/worlds/{world_id}/model-invocations", None),
        (
            "GET",
            f"/worlds/{world_id}/authoring/source-batches",
            {"worldline_id": str(worldline_id)},
        ),
        ("GET", f"/worlds/{world_id}/diagnostics/multimodal", None),
        (
            "GET",
            f"/worlds/{world_id}/narrative-quality/dashboard",
            {"worldline_id": str(worldline_id)},
        ),
        ("GET", f"/worlds/{world_id}/asset-generation/policies", None),
    ]

    for method, path, params in member_routes:
        response = client.request(method, path, params=params)
        assert response.status_code == 403, path
        assert_no_forbidden_tokens(response.text)

    presentation_path = (
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation"
    )
    for method, path, body in (
        ("PUT", presentation_path, {"emotion_key": "happy"}),
        ("PATCH", presentation_path, {"emotion_key": "happy"}),
        ("POST", f"{presentation_path}/render-visual", {"location_key": "classroom"}),
    ):
        response = client.request(method, path, json=body)
        assert response.status_code == 403, path
        assert_no_forbidden_tokens(response.text)

    client.cookies.clear()
    client.headers.clear()
    for _method, path, params in member_routes:
        response = client.get(path, params=params)
        assert response.status_code == 401, path
        assert_no_forbidden_tokens(response.text)


def test_sample_fixtures_remain_free_of_forbidden_event_and_proposal_payloads(
    tmp_path: Path,
) -> None:
    multimodal_sample = create_multimodal_sample_world(tmp_path / "multimodal")
    with Session(multimodal_sample.engine) as session:
        world_events = session.scalars(select(WorldEventModel)).all()
        assert world_events
        for event in world_events:
            assert contains_forbidden_payload(event.payload) is False

    authoring_sample = create_authoring_sample_import()
    with Session(authoring_sample.engine) as session:
        proposals = session.scalars(select(AuthoringImportProposal)).all()
        assert proposals
        for proposal in proposals:
            payloads = {
                "proposed": proposal.proposed_payload_json,
                "evidence": proposal.evidence_json,
                "applied": proposal.applied_ref_json,
            }
            assert contains_forbidden_payload(payloads) is False


def test_security_regression_coverage_map_references_existing_checks() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    expected_coverage = {
        "tests/test_api_permission_matrix.py": (
            "test_world_member_is_denied_high_risk_admin_surfaces_without_leaks",
            "FORBIDDEN_RESPONSE_TOKENS",
        ),
        "tests/test_provider_execution_service.py": (
            "test_resolved_secret_is_not_written_to_ledger",
            "snapshot.raw_request_json",
        ),
        "tests/test_multimodal_sample_world_regression.py": (
            "test_sample_world_security_boundaries_and_admin_controlled_generation",
            "test_sample_world_multimodal_diagnostics_pass",
        ),
        "tests/test_authoring_regression_fixture.py": (
            "test_authoring_sample_fixture_has_no_runtime_or_media_side_effects",
            "full_raw_source",
        ),
        "tests/test_narrative_quality_service.py": (
            "test_narrative_quality_dashboard_detects_blockers_and_sanitizes_evidence",
            "test_narrative_quality_dashboard_rejects_foreign_worldline",
        ),
        "tests/test_observability_incidents.py": (
            "test_incident_summary_aggregates_safe_evidence_refs",
            "test_incident_summary_endpoint_is_platform_admin_only_and_safe",
        ),
    }

    for relative_path, markers in expected_coverage.items():
        text = (repo_root / relative_path).read_text(encoding="utf-8")
        for marker in markers:
            assert marker in text, f"{marker} missing from {relative_path}"


def _client_with_database() -> tuple[TestClient, Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        cast(Table, User.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, WorldMembership.__table__),
    ):
        table.create(engine)
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


def _seed_user(engine: Engine, email: str) -> tuple[uuid.UUID, str]:
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
        session.commit()
    return user_id, token


def _seed_world(engine: Engine, owner_user_id: uuid.UUID) -> uuid.UUID:
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=owner_user_id,
                slug=f"security-world-{world_id.hex[:8]}",
                name="Security World",
            ),
        )
        session.commit()
    return world_id


def _seed_worldline(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        worldline = ensure_primary_worldline(session, world_id)
        session.commit()
        return worldline.id


def _add_membership(
    engine: Engine,
    world_id: uuid.UUID,
    user_id: uuid.UUID,
    role: AuthRole,
) -> None:
    with Session(engine) as session:
        session.add(
            WorldMembership(
                id=uuid.uuid4(),
                world_id=world_id,
                user_id=user_id,
                role=role.value,
            ),
        )
        session.commit()


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf")
    client.headers.update({CSRF_HEADER_NAME: "csrf"})
