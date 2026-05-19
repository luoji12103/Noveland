from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from noveland.auth import AuthenticatedSubject
from noveland.private_beta import (
    PrivateBetaInviteCreate,
    PrivateBetaInviteCreated,
    PrivateBetaInviteRead,
    PrivateBetaInviteRedeem,
    PrivateBetaInviteRevoke,
    PrivateBetaInviteStatus,
    PrivateBetaNotFoundError,
    PrivateBetaOnboardingStatus,
    PrivateBetaPlayerProfileCreate,
    PrivateBetaPlayerProfileResult,
    PrivateBetaRedeemResult,
    PrivateBetaService,
    PrivateBetaValidationError,
)
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_current_subject,
    get_db_session,
    get_world_admin_context,
    get_world_member_context,
)
from sqlalchemy.orm import Session

router = APIRouter(tags=["private-beta"])


@router.get(
    "/worlds/{world_id}/private-beta/invites",
    response_model=list[PrivateBetaInviteRead],
)
def list_private_beta_invites(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    status_filter: Annotated[PrivateBetaInviteStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[PrivateBetaInviteRead]:
    try:
        return PrivateBetaService(db_session).list_invites(
            world_id,
            status=status_filter,
            limit=limit,
        )
    except PrivateBetaNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/worlds/{world_id}/private-beta/invites",
    response_model=PrivateBetaInviteCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_private_beta_invite(
    world_id: uuid.UUID,
    invite_create: PrivateBetaInviteCreate,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PrivateBetaInviteCreated:
    _ = world_id
    require_csrf(request)
    try:
        return PrivateBetaService(db_session).create_invite(
            context.world_id,
            invite_create,
            actor_ref=_actor_ref(context.subject),
        )
    except PrivateBetaNotFoundError as exc:
        raise _not_found() from exc
    except PrivateBetaValidationError as exc:
        raise _bad_request(str(exc)) from exc


@router.get(
    "/worlds/{world_id}/private-beta/invites/{invite_id}",
    response_model=PrivateBetaInviteRead,
)
def get_private_beta_invite(
    world_id: uuid.UUID,
    invite_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PrivateBetaInviteRead:
    try:
        return PrivateBetaService(db_session).get_invite(world_id, invite_id)
    except PrivateBetaNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/worlds/{world_id}/private-beta/invites/{invite_id}/revoke",
    response_model=PrivateBetaInviteRead,
)
def revoke_private_beta_invite(
    world_id: uuid.UUID,
    invite_id: uuid.UUID,
    revoke: PrivateBetaInviteRevoke,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PrivateBetaInviteRead:
    _ = world_id
    require_csrf(request)
    try:
        return PrivateBetaService(db_session).revoke_invite(
            context.world_id,
            invite_id,
            revoke,
            actor_ref=_actor_ref(context.subject),
        )
    except PrivateBetaNotFoundError as exc:
        raise _not_found() from exc
    except PrivateBetaValidationError as exc:
        raise _bad_request(str(exc)) from exc


@router.post("/private-beta/invites/redeem", response_model=PrivateBetaRedeemResult)
def redeem_private_beta_invite(
    redeem: PrivateBetaInviteRedeem,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PrivateBetaRedeemResult:
    require_csrf(request)
    try:
        return PrivateBetaService(db_session).redeem_invite(
            redeem.token,
            user_id=subject.user_id,
        )
    except PrivateBetaNotFoundError as exc:
        raise _not_found() from exc
    except PrivateBetaValidationError as exc:
        raise _bad_request(str(exc)) from exc


@router.get("/private-beta/onboarding", response_model=PrivateBetaOnboardingStatus)
def get_private_beta_onboarding_status(
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PrivateBetaOnboardingStatus:
    return PrivateBetaService(db_session).onboarding_status(user_id=subject.user_id)


@router.post(
    "/worlds/{world_id}/private-beta/onboarding/player-profile",
    response_model=PrivateBetaPlayerProfileResult,
)
def bootstrap_private_beta_player_profile(
    world_id: uuid.UUID,
    profile_create: PrivateBetaPlayerProfileCreate,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PrivateBetaPlayerProfileResult:
    _ = world_id
    require_csrf(request)
    try:
        return PrivateBetaService(db_session).bootstrap_player_profile(
            context.world_id,
            context.subject.user_id,
            profile_create,
        )
    except PrivateBetaNotFoundError as exc:
        raise _not_found() from exc
    except (PrivateBetaValidationError, ValueError) as exc:
        raise _bad_request(str(exc)) from exc


def _actor_ref(subject: AuthenticatedSubject) -> str:
    return f"user:{subject.user_id}"


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Private beta record not found",
    )


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
