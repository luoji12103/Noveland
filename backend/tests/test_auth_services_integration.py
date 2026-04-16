from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from noveland.auth import (
    AuthRole,
    AuthSessionCreate,
    AuthSessionService,
    AuthSessionStatus,
    InvalidCredentialsError,
    InvalidSessionError,
    PasswordCredentialService,
    PasswordCredentialSet,
)
from noveland.auth.services import hash_session_token
from pwdlib import PasswordHash
from pydantic import SecretStr
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

TEST_DATABASE_URL = os.environ.get("NOVELAND_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="NOVELAND_TEST_DATABASE_URL is not set",
)


class UpdatingPasswordHash:
    def hash(self, password: str) -> str:
        return f"fake:{password}"

    def verify_and_update(self, password: str, hash: str) -> tuple[bool, str | None]:
        if password != "correct-password" or not hash.startswith("$argon2id$"):
            return False, None
        return True, "fake:upgraded"


@pytest.fixture()
def engine() -> Iterator[Engine]:
    if TEST_DATABASE_URL is None:
        pytest.skip("NOVELAND_TEST_DATABASE_URL is not set")
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session
        session.rollback()


def test_password_credential_service_hashes_verifies_and_upgrades(session: Session) -> None:
    user_id = _insert_user(session)
    service = PasswordCredentialService(session)

    credential = service.set_password(
        PasswordCredentialSet(user_id=user_id, password=SecretStr("correct-password")),
    )

    assert credential.password_hash.startswith("$argon2id$")
    assert "correct-password" not in credential.password_hash
    assert service.verify_password(user_id, "correct-password").id == credential.id
    with pytest.raises(InvalidCredentialsError):
        service.verify_password(user_id, "wrong-password")

    upgrade_service = PasswordCredentialService(
        session,
        password_hash=cast(PasswordHash, UpdatingPasswordHash()),
    )
    upgraded = upgrade_service.verify_password(user_id, "correct-password")

    assert upgraded.password_hash == "fake:upgraded"


def test_auth_session_service_creates_authenticates_revokes_and_expires(
    session: Session,
) -> None:
    user_id = _insert_user(session)
    _assign_platform_admin(session, user_id)
    service = AuthSessionService(session)

    created = service.create_session(
        AuthSessionCreate(
            user_id=user_id,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            user_agent="integration-test",
            ip_address="127.0.0.1",
        ),
    )

    assert created.session.status is AuthSessionStatus.ACTIVE
    assert created.session.token_hash == hash_session_token(created.token)
    assert created.session.token_hash != created.token
    assert len(created.token) >= 32

    subject = service.authenticate_session(created.token)
    assert subject.user_id == user_id
    assert subject.session_id == created.session.id
    assert subject.roles == frozenset({AuthRole.PLATFORM_ADMIN})

    revoked = service.revoke_session(created.token)
    revoked_again = service.revoke_session(created.token)
    assert revoked.status is AuthSessionStatus.REVOKED
    assert revoked_again.id == revoked.id
    with pytest.raises(InvalidSessionError):
        service.authenticate_session(created.token)

    expiring = service.create_session(
        AuthSessionCreate(
            user_id=user_id,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ),
    )
    expired = service.expire_session(expiring.token)
    assert expired.status is AuthSessionStatus.EXPIRED
    with pytest.raises(InvalidSessionError):
        service.authenticate_session(expiring.token)


def _insert_user(session: Session) -> uuid.UUID:
    user_id = uuid.uuid4()
    session.execute(
        text(
            """
            INSERT INTO users (id, email, display_name)
            VALUES (CAST(:user_id AS uuid), :email, :display_name)
            """,
        ),
        {
            "user_id": str(user_id),
            "email": f"{user_id}@example.test",
            "display_name": "Integration User",
        },
    )
    return user_id


def _assign_platform_admin(session: Session, user_id: uuid.UUID) -> None:
    session.execute(
        text(
            """
            INSERT INTO platform_role_assignments (user_id, role)
            VALUES (CAST(:user_id AS uuid), 'platform_admin')
            """,
        ),
        {"user_id": str(user_id)},
    )
