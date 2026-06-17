from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from noveland.auth.contracts import AuthRole, AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User, UserCredential
from noveland.auth.services import hash_session_token
from noveland.core.settings import load_settings
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from pwdlib import PasswordHash
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_csrf_sets_readable_csrf_cookie() -> None:
    client, _engine = _client_with_database()

    response = client.get("/auth/csrf")

    assert response.status_code == 200
    csrf_token = response.json()["csrf_token"]
    assert csrf_token
    assert client.cookies.get(CSRF_COOKIE_NAME) == csrf_token
    assert _cookie_header(response, CSRF_COOKIE_NAME) is not None
    assert "HttpOnly" not in _cookie_header(response, CSRF_COOKIE_NAME)


def test_login_rejects_unknown_wrong_inactive_and_invalid_requests() -> None:
    client, engine = _client_with_database()
    _seed_user(engine, email="admin@example.test", password="correct-password")
    csrf_headers = _csrf_headers(client)

    unknown = client.post(
        "/auth/login",
        json={"email": "missing@example.test", "password": "correct-password"},
        headers=csrf_headers,
    )
    wrong = client.post(
        "/auth/login",
        json={"email": "admin@example.test", "password": "wrong-password"},
        headers=csrf_headers,
    )
    invalid = client.post("/auth/login", json={"email": "not-an-email"}, headers=csrf_headers)

    inactive_email = "inactive@example.test"
    _seed_user(engine, email=inactive_email, password="correct-password")
    _deactivate_user(engine, inactive_email)
    inactive = client.post(
        "/auth/login",
        json={"email": inactive_email, "password": "correct-password"},
        headers=csrf_headers,
    )

    assert unknown.status_code == 401
    assert wrong.status_code == 401
    assert inactive.status_code == 401
    assert invalid.status_code == 422


def test_login_requires_csrf_before_setting_session_cookie() -> None:
    client, engine = _client_with_database()
    _seed_user(engine, email="admin@example.test", password="correct-password")

    missing_csrf = client.post(
        "/auth/login",
        json={"email": "admin@example.test", "password": "correct-password"},
    )
    csrf_headers = _csrf_headers(client)
    wrong_csrf = client.post(
        "/auth/login",
        json={"email": "admin@example.test", "password": "correct-password"},
        headers={CSRF_HEADER_NAME: "wrong-token"},
    )

    assert csrf_headers[CSRF_HEADER_NAME]
    assert missing_csrf.status_code == 403
    assert wrong_csrf.status_code == 403
    assert client.cookies.get(SESSION_COOKIE_NAME) is None


def test_login_sets_session_cookie_and_me_returns_subject() -> None:
    client, engine = _client_with_database()
    user_id = _seed_user(engine, email="admin@example.test", password="correct-password")

    response = client.post(
        "/auth/login",
        json={"email": "ADMIN@example.test", "password": "correct-password"},
        headers=_csrf_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "user_id": str(user_id),
        "email": "admin@example.test",
        "display_name": "Admin",
        "roles": ["platform_admin"],
    }
    assert "token" not in body
    assert client.cookies.get(SESSION_COOKIE_NAME)
    assert client.cookies.get(CSRF_COOKIE_NAME)
    assert "HttpOnly" in _cookie_header(response, SESSION_COOKIE_NAME)
    assert "HttpOnly" not in _cookie_header(response, CSRF_COOKIE_NAME)
    assert "Max-Age=604800" in _cookie_header(response, SESSION_COOKIE_NAME)

    me_response = client.get("/auth/me")

    assert me_response.status_code == 200
    assert me_response.json() == body


def test_auth_cookie_policy_uses_configured_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOVELAND_AUTH_SESSION_TTL_SECONDS", "900")
    monkeypatch.setenv("NOVELAND_AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("NOVELAND_AUTH_COOKIE_SAMESITE", "strict")
    load_settings.cache_clear()
    try:
        client, engine = _client_with_database()
        _seed_user(engine, email="admin@example.test", password="correct-password")

        response = client.post(
            "/auth/login",
            json={"email": "admin@example.test", "password": "correct-password"},
            headers=_csrf_headers(client),
        )

        session_cookie = _cookie_header(response, SESSION_COOKIE_NAME)
        csrf_cookie = _cookie_header(response, CSRF_COOKIE_NAME)
        assert response.status_code == 200
        assert "Max-Age=900" in session_cookie
        assert "Secure" in session_cookie
        assert "SameSite=strict" in session_cookie
        assert "Max-Age=900" in csrf_cookie
        assert "Secure" in csrf_cookie
        assert "SameSite=strict" in csrf_cookie
    finally:
        load_settings.cache_clear()


def test_me_rejects_missing_invalid_and_expired_sessions() -> None:
    client, engine = _client_with_database()
    user_id = _seed_user(engine, email="admin@example.test", password="correct-password")

    missing = client.get("/auth/me")
    client.cookies.set(SESSION_COOKIE_NAME, "invalid")
    invalid = client.get("/auth/me")
    client.cookies.set(SESSION_COOKIE_NAME, "expired-token")
    _insert_expired_session(engine, user_id, "expired-token")
    expired = client.get("/auth/me")

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert expired.status_code == 401


def test_logout_requires_csrf_revokes_session_and_clears_cookies() -> None:
    client, engine = _client_with_database()
    _seed_user(engine, email="admin@example.test", password="correct-password")
    login_response = client.post(
        "/auth/login",
        json={"email": "admin@example.test", "password": "correct-password"},
        headers=_csrf_headers(client),
    )
    session_token = client.cookies.get(SESSION_COOKIE_NAME)
    csrf_token = client.cookies.get(CSRF_COOKIE_NAME)
    assert login_response.status_code == 200
    assert session_token is not None
    assert csrf_token is not None

    missing_csrf = client.post("/auth/logout")
    wrong_csrf = client.post("/auth/logout", headers={CSRF_HEADER_NAME: "wrong"})
    logout_response = client.post("/auth/logout", headers={CSRF_HEADER_NAME: csrf_token})
    me_after_logout = client.get("/auth/me")

    assert missing_csrf.status_code == 403
    assert wrong_csrf.status_code == 403
    assert logout_response.status_code == 204
    assert me_after_logout.status_code == 401
    assert client.cookies.get(SESSION_COOKIE_NAME) is None
    assert client.cookies.get(CSRF_COOKIE_NAME) is None
    assert _session_status(engine, session_token) == AuthSessionStatus.REVOKED.value


def _csrf_headers(client: TestClient) -> dict[str, str]:
    response = client.get("/auth/csrf")
    assert response.status_code == 200
    csrf_token = response.json()["csrf_token"]
    assert csrf_token
    return {CSRF_HEADER_NAME: csrf_token, "Cookie": f"{CSRF_COOKIE_NAME}={csrf_token}"}


def _client_with_database() -> tuple[TestClient, Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _create_auth_tables(engine)
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


def _create_auth_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, UserCredential.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
    ):
        table.create(engine)


def _seed_user(engine: Engine, email: str, password: str) -> uuid.UUID:
    with Session(engine) as session:
        now = datetime.now(UTC)
        user = User(
            id=uuid.uuid4(),
            email=email.lower(),
            display_name="Admin",
            is_active=True,
        )
        session.add(user)
        session.flush()
        session.add(
            UserCredential(
                id=uuid.uuid4(),
                user_id=user.id,
                password_hash=PasswordHash.recommended().hash(password),
                password_set_at=now,
                password_updated_at=now,
            ),
        )
        session.add(
            PlatformRoleAssignment(
                id=uuid.uuid4(),
                user_id=user.id,
                role=AuthRole.PLATFORM_ADMIN.value,
                assigned_at=now,
            ),
        )
        session.commit()
        return user.id


def _deactivate_user(engine: Engine, email: str) -> None:
    with Session(engine) as session:
        user = session.query(User).filter(User.email == email).one()
        user.is_active = False
        session.commit()


def _insert_expired_session(engine: Engine, user_id: uuid.UUID, token: str) -> None:
    with Session(engine) as session:
        session.add(
            AuthSession(
                id=uuid.uuid4(),
                user_id=user_id,
                token_hash=hash_session_token(token),
                status=AuthSessionStatus.ACTIVE.value,
                expires_at=datetime.now(UTC) - timedelta(minutes=1),
            ),
        )
        session.commit()


def _session_status(engine: Engine, token: str) -> str:
    with Session(engine) as session:
        session_model = session.query(AuthSession).filter(
            AuthSession.token_hash == hash_session_token(token),
        ).one()
        return session_model.status


def _cookie_header(response: Response, cookie_name: str) -> str:
    headers = response.headers.get_list("set-cookie")
    for header in headers:
        if header.startswith(f"{cookie_name}="):
            return header
    raise AssertionError(f"missing Set-Cookie header for {cookie_name}")
