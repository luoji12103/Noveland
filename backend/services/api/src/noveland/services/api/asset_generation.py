from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from noveland.asset_generation.contracts import (
    AssetGenerationApplyRequest,
    AssetGenerationApplyResult,
    AssetGenerationPolicyCreate,
    AssetGenerationPolicyRead,
    AssetGenerationPolicyUpdate,
    AssetGenerationPreviewRequest,
    AssetGenerationPreviewResult,
    AssetGenerationRunRead,
    MediaJobCancelSupersededRequest,
    MediaJobCancelSupersededResult,
    MediaJobReprioritizeRequest,
    MediaJobReprioritizeResult,
)
from noveland.asset_generation.service import (
    AssetGenerationNotFoundError,
    AssetGenerationService,
    AssetGenerationValidationError,
)
from noveland.auth import AuthenticatedSubject
from noveland.media.errors import MediaConflictError
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_current_subject,
    get_db_session,
    get_world_admin_context,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/asset-generation", tags=["asset-generation"])
media_jobs_router = APIRouter(prefix="/worlds/{world_id}/media/jobs", tags=["asset-generation"])


class AssetGenerationPolicyCreateRequest(BaseModel):
    worldline_id: uuid.UUID
    policy_key: str = Field(min_length=1, max_length=120)
    status: str = "active"
    budget_json: dict[str, Any] = Field(default_factory=dict)
    lookahead_json: dict[str, Any] = Field(default_factory=dict)
    provider_preferences_json: dict[str, Any] = Field(default_factory=dict)
    rules_json: dict[str, Any] = Field(default_factory=dict)


@router.get("/policies", response_model=list[AssetGenerationPolicyRead])
def list_asset_generation_policies(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID, Query()],
) -> list[AssetGenerationPolicyRead]:
    try:
        return AssetGenerationService(db_session).list_policies(
            world_id,
            worldline_id=worldline_id,
        )
    except AssetGenerationValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/policies",
    response_model=AssetGenerationPolicyRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_asset_generation_policy(
    world_id: uuid.UUID,
    request: AssetGenerationPolicyCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AssetGenerationPolicyRead:
    try:
        return AssetGenerationService(db_session).create_policy(
            AssetGenerationPolicyCreate(world_id=world_id, **request.model_dump())
        )
    except (AssetGenerationValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.patch(
    "/policies/{policy_id}",
    response_model=AssetGenerationPolicyRead,
    dependencies=[Depends(require_csrf)],
)
def update_asset_generation_policy(
    world_id: uuid.UUID,
    policy_id: uuid.UUID,
    request: AssetGenerationPolicyUpdate,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AssetGenerationPolicyRead:
    try:
        return AssetGenerationService(db_session).update_policy(world_id, policy_id, request)
    except AssetGenerationNotFoundError as exc:
        raise _not_found() from exc
    except (AssetGenerationValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/preview",
    response_model=AssetGenerationPreviewResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def preview_asset_generation(
    world_id: uuid.UUID,
    request: AssetGenerationPreviewRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AssetGenerationPreviewResult:
    try:
        return AssetGenerationService(db_session).preview(
            world_id,
            request,
            actor_ref=f"user:{subject.user_id}",
        )
    except (AssetGenerationValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/apply",
    response_model=AssetGenerationApplyResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def apply_asset_generation(
    world_id: uuid.UUID,
    request: AssetGenerationApplyRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AssetGenerationApplyResult:
    try:
        return AssetGenerationService(db_session).apply(
            world_id,
            request,
            actor_ref=f"user:{subject.user_id}",
        )
    except AssetGenerationNotFoundError as exc:
        raise _not_found() from exc
    except (AssetGenerationValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/runs/{run_id}", response_model=AssetGenerationRunRead)
def get_asset_generation_run(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AssetGenerationRunRead:
    try:
        return AssetGenerationService(db_session).get_run(world_id, run_id)
    except AssetGenerationNotFoundError as exc:
        raise _not_found() from exc


@media_jobs_router.post(
    "/reprioritize",
    response_model=MediaJobReprioritizeResult,
    dependencies=[Depends(require_csrf)],
)
def reprioritize_media_jobs(
    world_id: uuid.UUID,
    request: MediaJobReprioritizeRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaJobReprioritizeResult:
    try:
        return AssetGenerationService(db_session).reprioritize_jobs(world_id, request)
    except AssetGenerationNotFoundError as exc:
        raise _not_found() from exc
    except (AssetGenerationValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@media_jobs_router.post(
    "/cancel-superseded",
    response_model=MediaJobCancelSupersededResult,
    dependencies=[Depends(require_csrf)],
)
def cancel_superseded_media_jobs(
    world_id: uuid.UUID,
    request: MediaJobCancelSupersededRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaJobCancelSupersededResult:
    try:
        return AssetGenerationService(db_session).cancel_superseded_jobs(world_id, request)
    except AssetGenerationNotFoundError as exc:
        raise _not_found() from exc
    except (AssetGenerationValidationError, MediaConflictError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
