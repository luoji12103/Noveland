from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_db_session,
    get_world_admin_context,
)
from noveland.world_packaging import (
    WorldPackageApplyRequest,
    WorldPackageApplyResult,
    WorldPackageExportRequest,
    WorldPackageImportPreviewRequest,
    WorldPackagePreviewResult,
    WorldPackagingNotFoundError,
    WorldPackagingService,
    WorldPackagingValidationError,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/packages", tags=["world-packaging"])


@router.post("/export-preview", response_model=WorldPackagePreviewResult)
def export_world_package_preview(
    world_id: uuid.UUID,
    request: WorldPackageExportRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldPackagePreviewResult:
    try:
        return WorldPackagingService(db_session).export_preview(world_id, request)
    except WorldPackagingNotFoundError as exc:
        raise _not_found() from exc


@router.post("/import-preview", response_model=WorldPackagePreviewResult)
def import_world_package_preview(
    world_id: uuid.UUID,
    request: WorldPackageImportPreviewRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldPackagePreviewResult:
    _ = world_id
    return WorldPackagingService(db_session).preview_import(request.manifest)


@router.post("/import-apply", response_model=WorldPackageApplyResult)
def apply_world_package_import(
    world_id: uuid.UUID,
    request: WorldPackageApplyRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldPackageApplyResult:
    _ = world_id
    try:
        return WorldPackagingService(db_session).apply_import(
            context.subject.user_id,
            request,
            actor_ref=f"user:{context.subject.user_id}",
        )
    except WorldPackagingValidationError as exc:
        raise _bad_request(str(exc)) from exc


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="World package source not found",
    )


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
