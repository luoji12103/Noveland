from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.services.api.app import create_app
from noveland.services.api.csrf import SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

TEST_DATABASE_URL = os.environ.get("NOVELAND_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="NOVELAND_TEST_DATABASE_URL is not set",
)


@pytest.fixture()
def engine() -> Iterator[Engine]:
    if TEST_DATABASE_URL is None:
        pytest.skip("NOVELAND_TEST_DATABASE_URL is not set")
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


def test_world_management_flow_against_postgres(engine: Engine) -> None:
    user_id, token = _seed_platform_admin_session(engine)
    client = _client_for_engine(engine)
    client.cookies.set(SESSION_COOKIE_NAME, token)
    slug = f"world-{uuid.uuid4().hex[:12]}"

    create_world = client.post("/worlds", json={"slug": slug, "name": "Integration World"})
    world_id = create_world.json()["id"]
    create_scene = client.post(
        f"/worlds/{world_id}/scenes",
        json={"scene_key": "home", "name": "Home"},
    )
    create_agent = client.post(
        f"/worlds/{world_id}/agents",
        json={
            "agent_key": "guide",
            "display_name": "Guide",
            "kind": "role_agent",
            "home_scene_id": create_scene.json()["id"],
        },
    )
    list_worlds = client.get("/worlds")

    assert create_world.status_code == 201
    assert create_world.json()["owner_user_id"] == str(user_id)
    assert create_scene.status_code == 201
    assert create_agent.status_code == 201
    assert slug in {world["slug"] for world in list_worlds.json()}


def _client_for_engine(engine: Engine) -> TestClient:
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
    return TestClient(app)


def _seed_platform_admin_session(engine: Engine) -> tuple[uuid.UUID, str]:
    user_id = uuid.uuid4()
    token = f"token-{user_id}"
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(
            User(
                id=user_id,
                email=f"{user_id}@example.test",
                display_name="Integration Admin",
                is_active=True,
            ),
        )
        session.flush()
        session.add(
            AuthSession(
                id=uuid.uuid4(),
                user_id=user_id,
                token_hash=hash_session_token(token),
                status=AuthSessionStatus.ACTIVE.value,
                expires_at=now + timedelta(hours=1),
            ),
        )
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
