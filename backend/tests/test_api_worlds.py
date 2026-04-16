from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi.testclient import TestClient
from noveland.agents.models import Agent
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import Scene, World, WorldMembership
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_platform_admin_can_create_list_and_update_worlds() -> None:
    client, engine = _client_with_database()
    platform_user_id, token = _seed_user(engine, "platform@example.test", platform_admin=True)
    _authenticate(client, token)

    create_response = client.post(
        "/worlds",
        json={
            "slug": "first-world",
            "name": "First World",
            "description": "Initial test world",
            "rules_config": {"mode": "local"},
        },
    )
    world = create_response.json()
    list_response = client.get("/worlds")
    update_response = client.patch(
        f"/worlds/{world['id']}",
        json={"name": "Renamed World", "is_active": False},
    )
    deactivate_response = client.delete(f"/worlds/{world['id']}")
    inactive_world = _world_is_active(engine, uuid.UUID(world["id"]))

    assert create_response.status_code == 201
    assert world["owner_user_id"] == str(platform_user_id)
    assert list_response.status_code == 200
    assert [item["slug"] for item in list_response.json()] == ["first-world"]
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Renamed World"
    assert update_response.json()["is_active"] is False
    assert deactivate_response.status_code == 204
    assert inactive_world is False
    assert _membership_role(engine, uuid.UUID(world["id"]), platform_user_id) == "world_admin"


def test_world_member_can_read_but_not_mutate_and_non_member_is_hidden() -> None:
    client, engine = _client_with_database()
    owner_id, _owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    _stranger_id, stranger_token = _seed_user(engine, "stranger@example.test")
    world_id = _seed_world(engine, owner_id, "shared-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    member_list = client.get("/worlds")
    member_get = client.get(f"/worlds/{world_id}")
    member_patch = client.patch(f"/worlds/{world_id}", json={"name": "Blocked"})
    member_candidates = client.get(f"/worlds/{world_id}/member-candidates")

    _authenticate(client, stranger_token)
    stranger_list = client.get("/worlds")
    stranger_get = client.get(f"/worlds/{world_id}")

    assert [item["id"] for item in member_list.json()] == [str(world_id)]
    assert member_get.status_code == 200
    assert member_patch.status_code == 403
    assert member_candidates.status_code == 403
    assert stranger_list.json() == []
    assert stranger_get.status_code == 404


def test_world_mutations_require_csrf() -> None:
    client, engine = _client_with_database()
    platform_user_id, token = _seed_user(engine, "platform@example.test", platform_admin=True)
    _authenticate_session_only(client, token)

    missing_csrf = client.post("/worlds", json={"slug": "missing-csrf", "name": "Blocked"})
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    wrong_csrf = client.post(
        "/worlds",
        headers={CSRF_HEADER_NAME: "wrong-token"},
        json={"slug": "wrong-csrf", "name": "Blocked"},
    )
    allowed = client.post(
        "/worlds",
        headers={CSRF_HEADER_NAME: "csrf-token"},
        json={"slug": "allowed-world", "name": "Allowed"},
    )

    assert platform_user_id
    assert missing_csrf.status_code == 403
    assert wrong_csrf.status_code == 403
    assert allowed.status_code == 201


def test_world_admin_manages_scenes_agents_and_conflicts() -> None:
    client, engine = _client_with_database()
    owner_id, token = _seed_user(engine, "owner@example.test")
    other_owner_id, _other_token = _seed_user(engine, "other@example.test")
    world_id = _seed_world(engine, owner_id, "agent-world")
    other_world_id = _seed_world(engine, other_owner_id, "other-world")
    other_scene_id = _seed_scene(engine, other_world_id, "outside")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, token)

    scene_response = client.post(
        f"/worlds/{world_id}/scenes",
        json={"scene_key": "home", "name": "Home"},
    )
    scene_id = scene_response.json()["id"]
    duplicate_scene = client.post(
        f"/worlds/{world_id}/scenes",
        json={"scene_key": "home", "name": "Home Again"},
    )
    update_scene = client.patch(
        f"/worlds/{world_id}/scenes/{scene_id}",
        json={"name": "New Home", "is_active": False},
    )
    deactivate_scene = client.delete(f"/worlds/{world_id}/scenes/{scene_id}")
    agent_response = client.post(
        f"/worlds/{world_id}/agents",
        json={
            "agent_key": "guide",
            "display_name": "Guide",
            "kind": "role_agent",
            "home_scene_id": scene_id,
            "config": {"tone": "direct"},
        },
    )
    duplicate_agent = client.post(
        f"/worlds/{world_id}/agents",
        json={"agent_key": "guide", "display_name": "Guide", "kind": "role_agent"},
    )
    cross_world_agent = client.post(
        f"/worlds/{world_id}/agents",
        json={
            "agent_key": "outsider",
            "display_name": "Outsider",
            "kind": "role_agent",
            "home_scene_id": str(other_scene_id),
        },
    )
    update_agent = client.patch(
        f"/worlds/{world_id}/agents/{agent_response.json()['id']}",
        json={"display_name": "Guide Updated", "is_enabled": False},
    )
    deactivate_agent = client.delete(f"/worlds/{world_id}/agents/{agent_response.json()['id']}")
    list_agents = client.get(f"/worlds/{world_id}/agents")

    assert scene_response.status_code == 201
    assert duplicate_scene.status_code == 409
    assert update_scene.status_code == 200
    assert update_scene.json()["is_active"] is False
    assert deactivate_scene.status_code == 204
    assert _scene_is_active(engine, uuid.UUID(scene_id)) is False
    assert agent_response.status_code == 201
    assert duplicate_agent.status_code == 409
    assert cross_world_agent.status_code == 404
    assert update_agent.status_code == 200
    assert update_agent.json()["display_name"] == "Guide Updated"
    assert deactivate_agent.status_code == 204
    assert _agent_is_enabled(engine, uuid.UUID(agent_response.json()["id"])) is False
    assert list_agents.json()[0]["agent_key"] == "guide"


def test_membership_management_and_final_admin_guard() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    user_id, _user_token = _seed_user(engine, "user@example.test")
    second_admin_id, _second_token = _seed_user(engine, "second@example.test")
    world_id = _seed_world(engine, owner_id, "membership-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, owner_token)

    invalid_role = client.put(
        f"/worlds/{world_id}/memberships/{user_id}",
        json={"user_id": str(user_id), "role": "platform_admin"},
    )
    create_member = client.put(
        f"/worlds/{world_id}/memberships/{user_id}",
        json={"user_id": str(user_id), "role": "human_user"},
    )
    list_members = client.get(f"/worlds/{world_id}/memberships")
    member_candidates = client.get(
        f"/worlds/{world_id}/member-candidates",
        params={"query": "user", "limit": 5},
    )
    invalid_limit = client.get(f"/worlds/{world_id}/member-candidates", params={"limit": 51})
    delete_member = client.delete(f"/worlds/{world_id}/memberships/{user_id}")
    downgrade_final_admin = client.put(
        f"/worlds/{world_id}/memberships/{owner_id}",
        json={"user_id": str(owner_id), "role": "human_user"},
    )
    delete_final_admin = client.delete(f"/worlds/{world_id}/memberships/{owner_id}")
    add_second_admin = client.put(
        f"/worlds/{world_id}/memberships/{second_admin_id}",
        json={"user_id": str(second_admin_id), "role": "world_admin"},
    )
    delete_original_admin = client.delete(f"/worlds/{world_id}/memberships/{owner_id}")

    assert invalid_role.status_code == 422
    assert create_member.status_code == 200
    assert create_member.json()["role"] == "human_user"
    assert create_member.json()["user"]["email"] == "user@example.test"
    assert sorted(item["role"] for item in list_members.json()) == ["human_user", "world_admin"]
    assert list_members.json()[0]["user"]["email"]
    assert member_candidates.status_code == 200
    assert invalid_limit.status_code == 422
    assert member_candidates.json() == [
        {
            "id": str(user_id),
            "email": "user@example.test",
            "display_name": "user@example.test",
            "is_active": True,
            "role": "human_user",
        },
    ]
    assert delete_member.status_code == 204
    assert downgrade_final_admin.status_code == 409
    assert delete_final_admin.status_code == 409
    assert add_second_admin.status_code == 200
    assert delete_original_admin.status_code == 204


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
        cast(Table, User.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
        cast(Table, World.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, Scene.__table__),
        cast(Table, Agent.__table__),
    ):
        table.create(engine)


def _seed_user(engine: Engine, email: str, platform_admin: bool = False) -> tuple[uuid.UUID, str]:
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
                is_active=True,
            ),
        )
        session.commit()
    return world_id


def _seed_scene(engine: Engine, world_id: uuid.UUID, scene_key: str) -> uuid.UUID:
    scene_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Scene(
                id=scene_id,
                world_id=world_id,
                scene_key=scene_key,
                name=scene_key,
                is_active=True,
            ),
        )
        session.commit()
    return scene_id


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


def _membership_role(engine: Engine, world_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
    with Session(engine) as session:
        return session.scalars(
            select(WorldMembership.role).where(
                WorldMembership.world_id == world_id,
                WorldMembership.user_id == user_id,
            ),
        ).one_or_none()


def _world_is_active(engine: Engine, world_id: uuid.UUID) -> bool:
    with Session(engine) as session:
        return bool(session.scalars(select(World.is_active).where(World.id == world_id)).one())


def _scene_is_active(engine: Engine, scene_id: uuid.UUID) -> bool:
    with Session(engine) as session:
        return bool(session.scalars(select(Scene.is_active).where(Scene.id == scene_id)).one())


def _agent_is_enabled(engine: Engine, agent_id: uuid.UUID) -> bool:
    with Session(engine) as session:
        return bool(session.scalars(select(Agent.is_enabled).where(Agent.id == agent_id)).one())


def _authenticate(client: TestClient, token: str) -> None:
    _authenticate_session_only(client, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _authenticate_session_only(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
