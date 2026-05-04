from __future__ import annotations

import os
import sys
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from noveland.auth.seed_admin import main as seed_admin_main
from noveland.auth.seed_admin import seed_admin
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME
from noveland.services.api.dependencies import get_db_session
from sqlalchemy import create_engine, select
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


def test_seed_admin_and_http_auth_flow_against_postgres(engine: Engine) -> None:
    email = f"admin-{uuid.uuid4()}@example.test"
    with Session(engine) as session:
        first_user_id = seed_admin(
            session,
            email=email,
            password="correct-password",
            display_name="Admin One",
        )
        second_user_id = seed_admin(
            session,
            email=email.upper(),
            password="correct-password",
            display_name="Admin Two",
        )
        session.commit()

    assert first_user_id == second_user_id
    assert _platform_admin_role_count(engine, first_user_id) == 1

    client = _client_for_engine(engine)
    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": "correct-password"},
    )
    csrf_token = client.cookies.get(CSRF_COOKIE_NAME)
    me_response = client.get("/auth/me")
    logout_response = client.post(
        "/auth/logout",
        headers={CSRF_HEADER_NAME: csrf_token or ""},
    )
    me_after_logout = client.get("/auth/me")

    assert login_response.status_code == 200
    assert login_response.json()["display_name"] == "Admin Two"
    assert me_response.status_code == 200
    assert logout_response.status_code == 204
    assert me_after_logout.status_code == 401


def test_seed_admin_cli_updates_platform_admin_against_postgres(
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if TEST_DATABASE_URL is None:
        pytest.skip("NOVELAND_TEST_DATABASE_URL is not set")
    email = f"cli-admin-{uuid.uuid4()}@example.test"
    monkeypatch.setenv("NOVELAND_DATABASE_URL", TEST_DATABASE_URL)

    _run_seed_admin_cli(monkeypatch, email, "correct-password", "CLI Admin One")
    _run_seed_admin_cli(monkeypatch, email.upper(), "correct-password", "CLI Admin Two")

    user_id = _user_id_by_email(engine, email)
    assert user_id is not None
    assert _platform_admin_role_count(engine, user_id) == 1

    client = _client_for_engine(engine)
    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": "correct-password"},
    )

    assert login_response.status_code == 200
    assert login_response.json()["display_name"] == "CLI Admin Two"


def test_seed_admin_rejects_short_password(engine: Engine) -> None:
    with Session(engine) as session:
        with pytest.raises(ValueError, match="password must be at least 8 characters"):
            seed_admin(
                session,
                email=f"short-{uuid.uuid4()}@example.test",
                password="short",
                display_name="Short Password",
            )


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


def _platform_admin_role_count(engine: Engine, user_id: uuid.UUID) -> int:
    from noveland.auth.models import PlatformRoleAssignment

    with Session(engine) as session:
        roles = session.scalars(
            select(PlatformRoleAssignment).where(
                PlatformRoleAssignment.user_id == user_id,
                PlatformRoleAssignment.role == "platform_admin",
            ),
        ).all()
        return len(roles)


def _user_id_by_email(engine: Engine, email: str) -> uuid.UUID | None:
    from noveland.auth.models import User

    with Session(engine) as session:
        return session.scalars(select(User.id).where(User.email == email.lower())).one_or_none()


def _run_seed_admin_cli(
    monkeypatch: pytest.MonkeyPatch,
    email: str,
    password: str,
    display_name: str,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "noveland-seed-admin",
            "--email",
            email,
            "--password",
            password,
            "--display-name",
            display_name,
        ],
    )
    seed_admin_main()
