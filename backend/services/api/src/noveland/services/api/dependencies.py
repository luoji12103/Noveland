from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from noveland.auth import AuthenticatedSubject, AuthSessionService, InvalidSessionError
from noveland.core.database import create_engine_from_settings, create_session_factory
from noveland.core.settings import load_settings
from noveland.services.api.authorization import (
    is_platform_admin,
    require_platform_admin,
    require_world_admin,
    require_world_member,
)
from noveland.services.api.csrf import SESSION_COOKIE_NAME
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class WorldAccessContext:
    world_id: uuid.UUID
    subject: AuthenticatedSubject
    role: str | None
    is_platform_admin: bool


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine_from_settings(load_settings())


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return create_session_factory(get_engine())


def get_db_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_current_subject(
    request: Request,
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthenticatedSubject:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is None:
        raise _invalid_session_http_error()

    try:
        return AuthSessionService(db_session).authenticate_session(token)
    except InvalidSessionError as exc:
        raise _invalid_session_http_error() from exc


def get_platform_admin_subject(
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
) -> AuthenticatedSubject:
    return require_platform_admin(subject)


def get_world_member_context(
    world_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldAccessContext:
    role = require_world_member(db_session, subject, world_id)
    return WorldAccessContext(
        world_id=world_id,
        subject=subject,
        role=None if role is None else role.value,
        is_platform_admin=is_platform_admin(subject),
    )


def get_world_admin_context(
    world_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldAccessContext:
    role = require_world_admin(db_session, subject, world_id)
    return WorldAccessContext(
        world_id=world_id,
        subject=subject,
        role=None if role is None else role.value,
        is_platform_admin=is_platform_admin(subject),
    )


def _invalid_session_http_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing session",
    )
