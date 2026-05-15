from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import World, Worldline, WorldMembership
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

FORBIDDEN_RESPONSE_TOKENS = (
    "authorization",
    "base64",
    "bearer",
    "bytes",
    "filesystem",
    "media://",
    "prompt_snapshot",
    "raw_output",
    "raw_prompt",
    "resolved_secret",
    "sk-test",
    "storage_uri",
)


def test_permission_matrix_document_covers_high_risk_surfaces() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    matrix = (repo_root / "docs/agent/architecture/permission-matrix.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "Providers",
        "Model invocations",
        "Media admin catalog",
        "Authoring/import",
        "Multimodal evals",
        "Narrative quality",
        "Forbidden Lower-Privilege Data",
        "resolved provider secrets",
        "raw prompts",
        "storage URIs",
    ):
        assert expected in matrix


def test_world_member_is_denied_high_risk_admin_surfaces_without_leaks() -> None:
    client, engine = _client_with_database()
    owner_id, _owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    _authenticate(client, member_token)

    conversation_id = uuid.uuid4()
    turn_id = uuid.uuid4()
    routes = [
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
        ("GET", f"/worlds/{world_id}/visual/sprite-sets", None),
        ("GET", f"/worlds/{world_id}/speech/voice-profiles", None),
        ("GET", f"/worlds/{world_id}/asset-generation/policies", None),
        (
            "GET",
            f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation",
            None,
        ),
    ]

    for method, path, params in routes:
        response = client.request(method, path, params=params)
        assert response.status_code == 403, path
        _assert_no_forbidden_tokens(response.text)


def test_unauthenticated_actor_is_denied_admin_surfaces_without_leaks() -> None:
    client, engine = _client_with_database()
    owner_id, _owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)

    routes = [
        f"/worlds/{world_id}/providers",
        f"/worlds/{world_id}/model-invocations",
        f"/worlds/{world_id}/authoring/source-batches?worldline_id={worldline_id}",
        f"/worlds/{world_id}/diagnostics/multimodal",
        f"/worlds/{world_id}/narrative-quality/dashboard?worldline_id={worldline_id}",
    ]

    for path in routes:
        response = client.get(path)
        assert response.status_code == 401, path
        _assert_no_forbidden_tokens(response.text)


def _assert_no_forbidden_tokens(text: str) -> None:
    lowered = text.lower()
    for token in FORBIDDEN_RESPONSE_TOKENS:
        assert token not in lowered


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
            )
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
                slug=f"world-{world_id.hex[:8]}",
                name="World",
            )
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
            )
        )
        session.commit()


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf")
    client.headers.update({CSRF_HEADER_NAME: "csrf"})
