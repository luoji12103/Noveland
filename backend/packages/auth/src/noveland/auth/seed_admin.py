from __future__ import annotations

import argparse
import uuid
from datetime import UTC, datetime

from noveland.auth.contracts import AuthRole, PasswordCredentialSet
from noveland.auth.models import PlatformRoleAssignment, User
from noveland.auth.services import PasswordCredentialService
from noveland.core.database import create_engine_from_settings, create_session_factory
from noveland.core.settings import load_settings
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session


def seed_admin(
    session: Session,
    email: str,
    password: str,
    display_name: str,
) -> uuid.UUID:
    normalized_email = _normalize_email(email)
    _validate_password(password)
    user = session.scalars(select(User).where(User.email == normalized_email)).one_or_none()
    if user is None:
        user = User(
            id=uuid.uuid4(),
            email=normalized_email,
            display_name=display_name,
            is_active=True,
        )
        session.add(user)
        session.flush()
    else:
        user.display_name = display_name
        user.is_active = True
        session.flush()

    PasswordCredentialService(session).set_password(
        PasswordCredentialSet(user_id=user.id, password=SecretStr(password)),
    )
    _ensure_platform_admin_role(session, user.id)
    session.flush()
    return user.id


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a local Noveland platform admin.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--display-name", required=True)
    args = parser.parse_args()

    engine = create_engine_from_settings(load_settings())
    try:
        session_factory = create_session_factory(engine)
        with session_factory() as session:
            try:
                user_id = seed_admin(
                    session,
                    email=args.email,
                    password=args.password,
                    display_name=args.display_name,
                )
                session.commit()
            except Exception:
                session.rollback()
                raise
    finally:
        engine.dispose()

    print(f"Seeded platform admin {args.email.strip().lower()} ({user_id})")


def _ensure_platform_admin_role(session: Session, user_id: uuid.UUID) -> None:
    existing_role = session.scalars(
        select(PlatformRoleAssignment).where(
            PlatformRoleAssignment.user_id == user_id,
            PlatformRoleAssignment.role == AuthRole.PLATFORM_ADMIN.value,
        ),
    ).one_or_none()
    if existing_role is not None:
        return
    session.add(
        PlatformRoleAssignment(
            id=uuid.uuid4(),
            user_id=user_id,
            role=AuthRole.PLATFORM_ADMIN.value,
            assigned_at=datetime.now(UTC),
        ),
    )


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if "@" not in normalized:
        raise ValueError("email must be an email address")
    return normalized


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
