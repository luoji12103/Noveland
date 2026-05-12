from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from noveland.core.settings import load_settings
from noveland.media.storage import LocalMediaObjectStorage
from noveland.multimodal_eval.contracts import (
    MultimodalDiagnosticsResult,
    MultimodalEvalRunRead,
    MultimodalEvalRunRequest,
)
from noveland.multimodal_eval.service import (
    MultimodalEvalNotFoundError,
    MultimodalEvalService,
)
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_db_session,
    get_world_admin_context,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}", tags=["multimodal-evals"])


def _eval_storage() -> LocalMediaObjectStorage:
    return LocalMediaObjectStorage(load_settings().object_storage_root / "media")


@router.get("/multimodal-evals", response_model=list[MultimodalEvalRunRead])
def list_multimodal_evals(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[MultimodalEvalRunRead]:
    try:
        return MultimodalEvalService(db_session).list_runs(
            world_id,
            worldline_id=worldline_id,
            limit=limit,
        )
    except ValueError as exc:
        raise _not_found(str(exc)) from exc


@router.post(
    "/multimodal-evals/run",
    response_model=MultimodalEvalRunRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def run_multimodal_eval(
    world_id: uuid.UUID,
    request: MultimodalEvalRunRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_eval_storage)],
) -> MultimodalEvalRunRead:
    try:
        return MultimodalEvalService(db_session, storage).run_eval(world_id, request)
    except ValueError as exc:
        raise _not_found(str(exc)) from exc


@router.get("/multimodal-evals/{run_id}", response_model=MultimodalEvalRunRead)
def get_multimodal_eval(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MultimodalEvalRunRead:
    try:
        return MultimodalEvalService(db_session).get_run(world_id, run_id)
    except MultimodalEvalNotFoundError as exc:
        raise _not_found("Not found") from exc


@router.get("/diagnostics/multimodal", response_model=MultimodalDiagnosticsResult)
def get_multimodal_diagnostics(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_eval_storage)],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
) -> MultimodalDiagnosticsResult:
    try:
        return MultimodalEvalService(db_session, storage).diagnostics(
            world_id,
            worldline_id=worldline_id,
        )
    except ValueError as exc:
        raise _not_found(str(exc)) from exc


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
