from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from noveland.auth import AuthenticatedSubject
from noveland.authoring.contracts import (
    AuthoringApplyRequest,
    AuthoringApplyResult,
    AuthoringImportRunCreate,
    AuthoringImportRunKind,
    AuthoringImportRunRead,
    AuthoringPreviewRequest,
    AuthoringPreviewResult,
    AuthoringProposalCreate,
    AuthoringProposalDraft,
    AuthoringProposalRead,
    AuthoringReviewDecisionCreate,
    AuthoringReviewDecisionRead,
    AuthoringSourceAssetCreate,
    AuthoringSourceAssetKind,
    AuthoringSourceAssetRead,
    AuthoringSourceBatchCreate,
    AuthoringSourceBatchRead,
    AuthoringSourceBatchStatus,
    AuthoringSourceFragmentCreate,
    AuthoringSourceFragmentKind,
    AuthoringSourceFragmentRead,
    AuthoringSourceVisibility,
)
from noveland.authoring.service import (
    AuthoringNotFoundError,
    AuthoringService,
    AuthoringValidationError,
)
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_current_subject,
    get_db_session,
    get_world_admin_context,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/authoring", tags=["authoring"])


class AuthoringSourceBatchCreateRequest(BaseModel):
    worldline_id: uuid.UUID
    batch_key: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    source_kind: AuthoringSourceAssetKind = AuthoringSourceAssetKind.OTHER
    status: AuthoringSourceBatchStatus = AuthoringSourceBatchStatus.ACTIVE
    visibility: AuthoringSourceVisibility = AuthoringSourceVisibility.PRIVATE
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AuthoringSourceAssetCreateRequest(BaseModel):
    worldline_id: uuid.UUID
    media_asset_id: uuid.UUID | None = None
    source_asset_kind: AuthoringSourceAssetKind = AuthoringSourceAssetKind.OTHER
    source_label: str = Field(min_length=1, max_length=160)
    source_ref: str | None = Field(default=None, max_length=240)
    status: AuthoringSourceBatchStatus = AuthoringSourceBatchStatus.ACTIVE
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AuthoringSourceFragmentCreateRequest(BaseModel):
    worldline_id: uuid.UUID
    fragment_key: str = Field(min_length=1, max_length=120)
    fragment_kind: AuthoringSourceFragmentKind = AuthoringSourceFragmentKind.OTHER
    sequence: int = Field(ge=0)
    excerpt_text: str | None = Field(default=None, max_length=4000)
    locator_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AuthoringImportRunCreateRequest(BaseModel):
    worldline_id: uuid.UUID
    source_batch_id: uuid.UUID | None = None
    run_kind: AuthoringImportRunKind = AuthoringImportRunKind.PREVIEW
    summary_json: dict[str, Any] = Field(default_factory=dict)


@router.get("/source-batches", response_model=list[AuthoringSourceBatchRead])
def list_authoring_source_batches(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID, Query()],
) -> list[AuthoringSourceBatchRead]:
    try:
        return AuthoringService(db_session).list_source_batches(
            world_id,
            worldline_id=worldline_id,
        )
    except AuthoringValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/source-batches",
    response_model=AuthoringSourceBatchRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_authoring_source_batch(
    world_id: uuid.UUID,
    request: AuthoringSourceBatchCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringSourceBatchRead:
    try:
        return AuthoringService(db_session).create_source_batch(
            AuthoringSourceBatchCreate(world_id=world_id, **request.model_dump()),
            actor_ref=f"user:{subject.user_id}",
        )
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/source-batches/{batch_id}", response_model=AuthoringSourceBatchRead)
def get_authoring_source_batch(
    world_id: uuid.UUID,
    batch_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringSourceBatchRead:
    try:
        return AuthoringService(db_session).get_source_batch(world_id, batch_id)
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/source-batches/{batch_id}/assets",
    response_model=AuthoringSourceAssetRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def add_authoring_source_asset(
    world_id: uuid.UUID,
    batch_id: uuid.UUID,
    request: AuthoringSourceAssetCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringSourceAssetRead:
    try:
        return AuthoringService(db_session).add_source_asset(
            AuthoringSourceAssetCreate(
                world_id=world_id,
                batch_id=batch_id,
                **request.model_dump(),
            )
        )
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/source-assets/{source_asset_id}/fragments",
    response_model=AuthoringSourceFragmentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def add_authoring_source_fragment(
    world_id: uuid.UUID,
    source_asset_id: uuid.UUID,
    request: AuthoringSourceFragmentCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringSourceFragmentRead:
    try:
        return AuthoringService(db_session).add_source_fragment(
            AuthoringSourceFragmentCreate(
                world_id=world_id,
                source_asset_id=source_asset_id,
                **request.model_dump(),
            )
        )
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/import-runs", response_model=list[AuthoringImportRunRead])
def list_authoring_import_runs(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID, Query()],
) -> list[AuthoringImportRunRead]:
    try:
        return AuthoringService(db_session).list_import_runs(world_id, worldline_id=worldline_id)
    except AuthoringValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/import-runs",
    response_model=AuthoringImportRunRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_authoring_import_run(
    world_id: uuid.UUID,
    request: AuthoringImportRunCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringImportRunRead:
    try:
        return AuthoringService(db_session).create_import_run(
            AuthoringImportRunCreate(world_id=world_id, **request.model_dump()),
            actor_ref=f"user:{subject.user_id}",
        )
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/import-runs/{run_id}", response_model=AuthoringImportRunRead)
def get_authoring_import_run(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringImportRunRead:
    try:
        return AuthoringService(db_session).get_import_run(world_id, run_id)
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/import-runs/{run_id}/proposals",
    response_model=AuthoringProposalRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_authoring_import_proposal(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    request: AuthoringProposalDraft,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringProposalRead:
    try:
        run = AuthoringService(db_session).get_import_run(world_id, run_id)
        return AuthoringService(db_session).create_proposal(
            AuthoringProposalCreate.from_draft(
                world_id=world_id,
                worldline_id=run.worldline_id,
                run_id=run_id,
                draft=request,
            )
        )
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/import-runs/{run_id}/preview",
    response_model=AuthoringPreviewResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def preview_authoring_import_run(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    request: AuthoringPreviewRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringPreviewResult:
    try:
        return AuthoringService(db_session).preview(world_id, run_id, request)
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/import-runs/{run_id}/apply",
    response_model=AuthoringApplyResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def apply_authoring_import_run(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    request: AuthoringApplyRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringApplyResult:
    try:
        return AuthoringService(db_session).apply(world_id, run_id, request)
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/proposals/{proposal_id}/review",
    response_model=AuthoringReviewDecisionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def review_authoring_import_proposal(
    world_id: uuid.UUID,
    proposal_id: uuid.UUID,
    request: AuthoringReviewDecisionCreate,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringReviewDecisionRead:
    try:
        return AuthoringService(db_session).review_proposal(
            world_id,
            proposal_id,
            request,
            actor_ref=f"user:{subject.user_id}",
        )
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
