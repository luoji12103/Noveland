from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from noveland.auth import AuthenticatedSubject, AuthRole
from noveland.worlds.models import World, WorldMembership
from sqlalchemy import select
from sqlalchemy.orm import Session


def is_platform_admin(subject: AuthenticatedSubject) -> bool:
    return AuthRole.PLATFORM_ADMIN in subject.roles


def require_platform_admin(subject: AuthenticatedSubject) -> AuthenticatedSubject:
    if not is_platform_admin(subject):
        raise _forbidden_error()
    return subject


def world_membership_role(
    session: Session,
    user_id: uuid.UUID,
    world_id: uuid.UUID,
) -> AuthRole | None:
    role_value = session.scalars(
        select(WorldMembership.role).where(
            WorldMembership.world_id == world_id,
            WorldMembership.user_id == user_id,
        ),
    ).one_or_none()
    return None if role_value is None else AuthRole(role_value)


def require_world_member(
    session: Session,
    subject: AuthenticatedSubject,
    world_id: uuid.UUID,
) -> AuthRole | None:
    if is_platform_admin(subject):
        _require_world_exists(session, world_id)
        return None

    role = world_membership_role(session, subject.user_id, world_id)
    if role is None:
        raise _not_found_error()
    return role


def require_world_admin(
    session: Session,
    subject: AuthenticatedSubject,
    world_id: uuid.UUID,
) -> AuthRole | None:
    if is_platform_admin(subject):
        _require_world_exists(session, world_id)
        return None

    role = world_membership_role(session, subject.user_id, world_id)
    if role is None:
        raise _not_found_error()
    if role != AuthRole.WORLD_ADMIN:
        raise _forbidden_error()
    return role


def _require_world_exists(session: Session, world_id: uuid.UUID) -> None:
    world_exists = session.scalars(select(World.id).where(World.id == world_id)).first()
    if world_exists is None:
        raise _not_found_error()


def _forbidden_error() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _not_found_error() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="World not found")
