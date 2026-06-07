from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from noveland.player_privacy import (
    PlayerPrivacyExport,
    PlayerPrivacyNotFoundError,
    PlayerPrivacyRequestCreate,
    PlayerPrivacyRequestRead,
    PlayerPrivacyRequestReview,
    PlayerPrivacyService,
    PlayerPrivacyValidationError,
)
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_db_session,
    get_world_admin_context,
    get_world_member_context,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/player/privacy", tags=["player-privacy"])


@router.get("/export", response_model=PlayerPrivacyExport)
def preview_player_privacy_export(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
) -> PlayerPrivacyExport:
    _ = world_id
    try:
        return PlayerPrivacyService(db_session).build_export(
            context.world_id,
            context.subject.user_id,
            worldline_id=worldline_id,
        )
    except PlayerPrivacyNotFoundError as exc:
        raise _not_found() from exc


@router.post("/export", response_model=PlayerPrivacyExport, dependencies=[Depends(require_csrf)])
def create_player_privacy_export_request(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    request: PlayerPrivacyRequestCreate | None = None,
) -> PlayerPrivacyExport:
    _ = world_id
    try:
        return PlayerPrivacyService(db_session).build_export(
            context.world_id,
            context.subject.user_id,
            worldline_id=None if request is None else request.worldline_id,
            persist_request=True,
            actor_ref=_actor_ref(context),
        )
    except PlayerPrivacyNotFoundError as exc:
        raise _not_found() from exc
    except PlayerPrivacyValidationError as exc:
        raise _bad_request(str(exc)) from exc


@router.get("/requests", response_model=list[PlayerPrivacyRequestRead])
def list_player_privacy_requests(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[PlayerPrivacyRequestRead]:
    _ = world_id
    return PlayerPrivacyService(db_session).list_requests(
        context.world_id,
        worldline_id=worldline_id,
        user_id=context.subject.user_id,
        include_all_users=context.is_platform_admin or context.role == "world_admin",
        limit=limit,
    )


@router.post(
    "/delete-requests",
    response_model=PlayerPrivacyRequestRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_player_delete_request(
    world_id: uuid.UUID,
    request: PlayerPrivacyRequestCreate,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PlayerPrivacyRequestRead:
    _ = world_id
    try:
        return PlayerPrivacyService(db_session).create_delete_request(
            context.world_id,
            context.subject.user_id,
            request,
            actor_ref=_actor_ref(context),
        )
    except PlayerPrivacyNotFoundError as exc:
        raise _not_found() from exc
    except PlayerPrivacyValidationError as exc:
        raise _bad_request(str(exc)) from exc


@router.patch(
    "/requests/{request_id}",
    response_model=PlayerPrivacyRequestRead,
    dependencies=[Depends(require_csrf)],
)
def review_player_privacy_request(
    world_id: uuid.UUID,
    request_id: uuid.UUID,
    request: PlayerPrivacyRequestReview,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PlayerPrivacyRequestRead:
    _ = world_id
    try:
        return PlayerPrivacyService(db_session).review_request(
            context.world_id,
            request_id,
            request,
            actor_ref=_actor_ref(context),
        )
    except PlayerPrivacyNotFoundError as exc:
        raise _not_found() from exc
    except PlayerPrivacyValidationError as exc:
        raise _bad_request(str(exc)) from exc


def _actor_ref(context: WorldAccessContext) -> str:
    return f"user:{context.subject.user_id}"


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Player privacy record not found",
    )


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
