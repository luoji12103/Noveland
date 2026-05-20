from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from noveland.auth.contracts import AuthRole
from noveland.beta_feedback import (
    BetaFeedbackIssueType,
    BetaFeedbackNotFoundError,
    BetaFeedbackReportCreate,
    BetaFeedbackReportRead,
    BetaFeedbackReportStatus,
    BetaFeedbackReportTriage,
    BetaFeedbackService,
    BetaFeedbackValidationError,
)
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_db_session,
    get_world_admin_context,
    get_world_member_context,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/beta-feedback", tags=["beta-feedback"])


@router.get("/reports", response_model=list[BetaFeedbackReportRead])
def list_beta_feedback_reports(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[BetaFeedbackReportStatus | None, Query(alias="status")] = None,
    issue_type: BetaFeedbackIssueType | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[BetaFeedbackReportRead]:
    _ = world_id
    try:
        return BetaFeedbackService(db_session).list_reports(
            context.world_id,
            actor_user_id=context.subject.user_id,
            actor_is_admin=_can_manage(context),
            worldline_id=worldline_id,
            status=status_filter,
            issue_type=None if issue_type is None else issue_type.value,
            limit=limit,
        )
    except BetaFeedbackNotFoundError as exc:
        raise _not_found() from exc
    except BetaFeedbackValidationError as exc:
        raise _bad_request(str(exc)) from exc


@router.post(
    "/reports",
    response_model=BetaFeedbackReportRead,
    status_code=status.HTTP_201_CREATED,
)
def create_beta_feedback_report(
    world_id: uuid.UUID,
    request_body: BetaFeedbackReportCreate,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> BetaFeedbackReportRead:
    _ = world_id
    require_csrf(request)
    try:
        return BetaFeedbackService(db_session).create_report(
            context.world_id,
            context.subject.user_id,
            request_body,
            actor_ref=_actor_ref(context),
            actor_is_admin=_can_manage(context),
        )
    except BetaFeedbackNotFoundError as exc:
        raise _not_found() from exc
    except BetaFeedbackValidationError as exc:
        raise _bad_request(str(exc)) from exc


@router.get("/reports/{report_id}", response_model=BetaFeedbackReportRead)
def get_beta_feedback_report(
    world_id: uuid.UUID,
    report_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> BetaFeedbackReportRead:
    _ = world_id
    try:
        return BetaFeedbackService(db_session).get_report(
            context.world_id,
            report_id,
            actor_user_id=context.subject.user_id,
            actor_is_admin=_can_manage(context),
        )
    except BetaFeedbackNotFoundError as exc:
        raise _not_found() from exc
    except BetaFeedbackValidationError as exc:
        raise _bad_request(str(exc)) from exc


@router.patch("/reports/{report_id}/triage", response_model=BetaFeedbackReportRead)
def triage_beta_feedback_report(
    world_id: uuid.UUID,
    report_id: uuid.UUID,
    request_body: BetaFeedbackReportTriage,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> BetaFeedbackReportRead:
    _ = world_id
    require_csrf(request)
    try:
        return BetaFeedbackService(db_session).triage_report(
            context.world_id,
            report_id,
            request_body,
            actor_ref=_actor_ref(context),
        )
    except BetaFeedbackNotFoundError as exc:
        raise _not_found() from exc
    except BetaFeedbackValidationError as exc:
        raise _bad_request(str(exc)) from exc


def _can_manage(context: WorldAccessContext) -> bool:
    return context.is_platform_admin or context.role == AuthRole.WORLD_ADMIN.value


def _actor_ref(context: WorldAccessContext) -> str:
    return f"user:{context.subject.user_id}"


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Beta feedback record not found",
    )


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
