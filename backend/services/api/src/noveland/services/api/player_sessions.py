from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from noveland.player_sessions import (
    PlayerSessionNotFoundError,
    PlayerSessionRead,
    PlayerSessionService,
    PlayerSessionUpsert,
    PlayerSessionValidationError,
)
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_db_session,
    get_world_member_context,
)
from sqlalchemy.orm import Session

router = APIRouter(tags=["player-sessions"])


@router.get(
    "/worlds/{world_id}/player-sessions/resume",
    response_model=PlayerSessionRead,
)
def get_player_session_resume(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID, Query()],
    player_actor_id: Annotated[uuid.UUID, Query()],
) -> PlayerSessionRead:
    _ = world_id
    try:
        return PlayerSessionService(db_session).get_resume(
            context.world_id,
            worldline_id=worldline_id,
            player_actor_id=player_actor_id,
            user_id=context.subject.user_id,
        )
    except PlayerSessionNotFoundError as exc:
        raise _not_found() from exc
    except PlayerSessionValidationError as exc:
        raise _bad_request(str(exc)) from exc


@router.post(
    "/worlds/{world_id}/player-sessions/resume",
    response_model=PlayerSessionRead,
)
def upsert_player_session_resume(
    world_id: uuid.UUID,
    session_upsert: PlayerSessionUpsert,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PlayerSessionRead:
    _ = world_id
    require_csrf(request)
    try:
        return PlayerSessionService(db_session).upsert_resume(
            context.world_id,
            session_upsert,
            user_id=context.subject.user_id,
        )
    except PlayerSessionNotFoundError as exc:
        raise _not_found() from exc
    except (PlayerSessionValidationError, ValueError) as exc:
        raise _bad_request(str(exc)) from exc


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Player session not found",
    )


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
