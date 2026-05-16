from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from noveland.moderation import (
    ModerationActionCreate,
    ModerationActionRead,
    ModerationIncidentCreate,
    ModerationIncidentRead,
    ModerationIncidentReview,
    ModerationNotFoundError,
    ModerationReportCreate,
    ModerationReportRead,
    ModerationReportReview,
    ModerationService,
    ModerationValidationError,
)
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_db_session,
    get_world_admin_context,
    get_world_member_context,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/moderation", tags=["moderation"])


@router.get("/reports", response_model=list[ModerationReportRead])
def list_moderation_reports(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[ModerationReportRead]:
    _ = world_id
    return ModerationService(db_session).list_reports(
        context.world_id,
        worldline_id=worldline_id,
        status=status_filter,
        limit=limit,
    )


@router.post(
    "/reports",
    response_model=ModerationReportRead,
    status_code=status.HTTP_201_CREATED,
)
def create_moderation_report(
    world_id: uuid.UUID,
    request: ModerationReportCreate,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ModerationReportRead:
    _ = world_id
    try:
        return ModerationService(db_session).create_report(
            context.world_id,
            context.subject.user_id,
            request,
            actor_ref=_actor_ref(context),
        )
    except ModerationNotFoundError as exc:
        raise _not_found() from exc
    except ModerationValidationError as exc:
        raise _bad_request(str(exc)) from exc


@router.patch("/reports/{report_id}", response_model=ModerationReportRead)
def review_moderation_report(
    world_id: uuid.UUID,
    report_id: uuid.UUID,
    request: ModerationReportReview,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ModerationReportRead:
    _ = world_id
    try:
        return ModerationService(db_session).review_report(
            context.world_id,
            report_id,
            request,
            actor_ref=_actor_ref(context),
        )
    except ModerationNotFoundError as exc:
        raise _not_found() from exc
    except ModerationValidationError as exc:
        raise _bad_request(str(exc)) from exc


@router.get("/actions", response_model=list[ModerationActionRead])
def list_moderation_actions(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[ModerationActionRead]:
    _ = world_id
    return ModerationService(db_session).list_actions(
        context.world_id,
        worldline_id=worldline_id,
        status=status_filter,
        limit=limit,
    )


@router.post(
    "/actions",
    response_model=ModerationActionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_moderation_action(
    world_id: uuid.UUID,
    request: ModerationActionCreate,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ModerationActionRead:
    _ = world_id
    try:
        return ModerationService(db_session).create_action(
            context.world_id,
            request,
            actor_ref=_actor_ref(context),
            actor_is_platform_admin=context.is_platform_admin,
        )
    except ModerationNotFoundError as exc:
        raise _not_found() from exc
    except ModerationValidationError as exc:
        raise _bad_request(str(exc)) from exc


@router.get("/incidents", response_model=list[ModerationIncidentRead])
def list_moderation_incidents(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[ModerationIncidentRead]:
    _ = world_id
    return ModerationService(db_session).list_incidents(
        context.world_id,
        worldline_id=worldline_id,
        status=status_filter,
        limit=limit,
    )


@router.post(
    "/incidents",
    response_model=ModerationIncidentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_moderation_incident(
    world_id: uuid.UUID,
    request: ModerationIncidentCreate,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ModerationIncidentRead:
    _ = world_id
    try:
        return ModerationService(db_session).create_incident(
            context.world_id,
            request,
            actor_ref=_actor_ref(context),
        )
    except ModerationNotFoundError as exc:
        raise _not_found() from exc
    except ModerationValidationError as exc:
        raise _bad_request(str(exc)) from exc


@router.patch("/incidents/{incident_id}", response_model=ModerationIncidentRead)
def review_moderation_incident(
    world_id: uuid.UUID,
    incident_id: uuid.UUID,
    request: ModerationIncidentReview,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ModerationIncidentRead:
    _ = world_id
    try:
        return ModerationService(db_session).review_incident(
            context.world_id,
            incident_id,
            request,
            actor_ref=_actor_ref(context),
        )
    except ModerationNotFoundError as exc:
        raise _not_found() from exc
    except ModerationValidationError as exc:
        raise _bad_request(str(exc)) from exc


def _actor_ref(context: WorldAccessContext) -> str:
    return f"user:{context.subject.user_id}"


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Moderation record not found",
    )


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
