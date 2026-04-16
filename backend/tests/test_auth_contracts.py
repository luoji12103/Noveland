from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from noveland.auth import (
    AuthRole,
    AuthSessionCreate,
    AuthSessionStatus,
    PasswordCredentialSet,
)
from noveland.auth.services import hash_session_token
from pydantic import SecretStr, ValidationError


def test_auth_roles_cover_baseline_roles() -> None:
    assert {role.value for role in AuthRole} == {
        "agent_runtime",
        "human_user",
        "platform_admin",
        "world_admin",
    }


def test_auth_session_statuses_cover_lifecycle_states() -> None:
    assert {status.value for status in AuthSessionStatus} == {
        "active",
        "expired",
        "revoked",
    }


def test_password_credential_rejects_short_passwords() -> None:
    with pytest.raises(ValidationError):
        PasswordCredentialSet(user_id=uuid.uuid4(), password=SecretStr("short"))


def test_session_create_requires_timezone_aware_expiration() -> None:
    with pytest.raises(ValidationError):
        AuthSessionCreate(
            user_id=uuid.uuid4(),
            expires_at=datetime(2026, 4, 16, 12, 0),
        )


def test_session_create_normalizes_expiration_to_utc() -> None:
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    session_create = AuthSessionCreate(
        user_id=uuid.uuid4(),
        expires_at=expires_at,
        user_agent="unit-test",
        ip_address="127.0.0.1",
    )

    assert session_create.expires_at.tzinfo is UTC
    assert session_create.user_agent == "unit-test"
    assert session_create.ip_address == "127.0.0.1"


def test_session_token_hash_does_not_reveal_plaintext_token() -> None:
    token = "plain-session-token"
    token_hash = hash_session_token(token)

    assert token_hash != token
    assert len(token_hash) == 64
    assert hash_session_token(token) == token_hash
