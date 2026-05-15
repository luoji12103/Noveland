from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from noveland.narrative_quality.contracts import (
    NarrativeQualityContextPreview,
    NarrativeQualityContextPreviewRequest,
)
from noveland.narrative_quality.service import (
    NarrativeQualityService,
    NarrativeQualityValidationError,
)
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_db_session,
    get_world_admin_context,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/narrative-quality", tags=["narrative-quality"])


@router.post(
    "/context/preview",
    response_model=NarrativeQualityContextPreview,
    dependencies=[Depends(require_csrf)],
)
def preview_narrative_quality_context(
    world_id: uuid.UUID,
    request: NarrativeQualityContextPreviewRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> NarrativeQualityContextPreview:
    try:
        return NarrativeQualityService(db_session).preview_context(world_id, request)
    except NarrativeQualityValidationError as exc:
        raise _unprocessable(str(exc)) from exc
    except ValueError as exc:
        raise _not_found(str(exc)) from exc


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
