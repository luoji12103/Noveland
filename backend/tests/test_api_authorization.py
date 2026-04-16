from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated, cast

from fastapi import Depends
from fastapi.testclient import TestClient
from noveland.auth import AuthenticatedSubject
from noveland.auth.contracts import AuthRole, AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.services.api.app import create_app
from noveland.services.api.csrf import SESSION_COOKIE_NAME
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_db_session,
    get_platform_admin_subject,
    get_world_admin_context,
    get_world_member_context,
)
from noveland.worlds.models import World, WorldMembership
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_platform_admin_passes_platform_and_world_checks() -> None:
    client, engine = _client_with_database()
    platform_user_id, token = _seed_user(engine, "platform@example.test", platform_admin=True)
    world_id = _seed_world(engine, platform_user_id, slug="world-one")
    client.cookies.set(SESSION_COOKIE_NAME, token)

    platform_response = client.get("/test-auth/platform")
    member_response = client.get(f"/test-auth/worlds/{world_id}/member")
    admin_response = client.get(f"/test-auth/worlds/{world_id}/admin")

    assert platform_response.status_code == 200
    assert member_response.json() == {
        "world_id": str(world_id),
        "role": None,
        "is_platform_admin": True,
    }
    assert admin_response.status_code == 200


def test_world_admin_passes_own_world_and_not_other_world() -> None:
    client, engine = _client_with_database()
    owner_id, token = _seed_user(engine, "owner@example.test")
    other_owner_id, _other_token = _seed_user(engine, "other@example.test")
    world_id = _seed_world(engine, owner_id, slug="owned-world")
    other_world_id = _seed_world(engine, other_owner_id, slug="other-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    client.cookies.set(SESSION_COOKIE_NAME, token)

    own_world = client.get(f"/test-auth/worlds/{world_id}/admin")
    other_world = client.get(f"/test-auth/worlds/{other_world_id}/admin")

    assert own_world.status_code == 200
    assert own_world.json()["role"] == AuthRole.WORLD_ADMIN.value
    assert other_world.status_code == 404


def test_human_user_can_read_member_context_but_cannot_admin() -> None:
    client, engine = _client_with_database()
    owner_id, _owner_token = _seed_user(engine, "owner@example.test")
    user_id, token = _seed_user(engine, "human@example.test")
    world_id = _seed_world(engine, owner_id, slug="shared-world")
    _add_membership(engine, world_id, user_id, AuthRole.HUMAN_USER)
    client.cookies.set(SESSION_COOKIE_NAME, token)

    member_response = client.get(f"/test-auth/worlds/{world_id}/member")
    admin_response = client.get(f"/test-auth/worlds/{world_id}/admin")
    platform_response = client.get("/test-auth/platform")

    assert member_response.status_code == 200
    assert member_response.json()["role"] == AuthRole.HUMAN_USER.value
    assert admin_response.status_code == 403
    assert admin_response.json()["detail"] == "Forbidden"
    assert platform_response.status_code == 403


def test_missing_session_and_inaccessible_worlds_fail_with_expected_statuses() -> None:
    client, engine = _client_with_database()
    owner_id, _owner_token = _seed_user(engine, "owner@example.test")
    user_id, token = _seed_user(engine, "stranger@example.test")
    world_id = _seed_world(engine, owner_id, slug="private-world")

    missing_session = client.get(f"/test-auth/worlds/{world_id}/member")
    client.cookies.set(SESSION_COOKIE_NAME, token)
    inaccessible_world = client.get(f"/test-auth/worlds/{world_id}/member")
    missing_world = client.get(f"/test-auth/worlds/{uuid.uuid4()}/member")

    assert user_id
    assert missing_session.status_code == 401
    assert inaccessible_world.status_code == 404
    assert missing_world.status_code == 404


def _client_with_database() -> tuple[TestClient, Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _create_tables(engine)
    app = create_app()

    @app.get("/test-auth/platform")
    def test_platform(
        subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    ) -> dict[str, str]:
        return {"user_id": str(subject.user_id)}

    @app.get("/test-auth/worlds/{world_id}/member")
    def test_world_member(
        context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    ) -> dict[str, object]:
        return _context_response(context)

    @app.get("/test-auth/worlds/{world_id}/admin")
    def test_world_admin(
        context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    ) -> dict[str, object]:
        return _context_response(context)

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


def _context_response(context: WorldAccessContext) -> dict[str, object]:
    return {
        "world_id": str(context.world_id),
        "role": context.role,
        "is_platform_admin": context.is_platform_admin,
    }


def _create_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
        cast(Table, World.__table__),
        cast(Table, WorldMembership.__table__),
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
