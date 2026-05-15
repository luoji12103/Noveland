from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from noveland.auth import AuthenticatedSubject
from noveland.narrative_quality.contracts import (
    NarrativeQualityContextPreview,
    NarrativeQualityContextPreviewRequest,
    NarrativeQualityGMProposalGenerateRequest,
    NarrativeQualityGMProposalGenerationResult,
)
from noveland.narrative_quality.service import (
    NarrativeQualityService,
    NarrativeQualityValidationError,
)
from noveland.providers.registry import ProviderValidationError
from noveland.providers.service import ProviderExecutionError
from noveland.services.api.authorization import is_platform_admin
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_current_subject,
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


@router.post(
    "/gm/proposals/generate",
    response_model=NarrativeQualityGMProposalGenerationResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def generate_provider_backed_gm_proposal(
    world_id: uuid.UUID,
    request: NarrativeQualityGMProposalGenerateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> NarrativeQualityGMProposalGenerationResult:
    actor_ref = "platform_admin" if is_platform_admin(subject) else f"world_admin:{subject.user_id}"
    try:
        return NarrativeQualityService(db_session).generate_gm_proposal(
            world_id,
            request,
            actor_ref=actor_ref,
        )
    except NarrativeQualityValidationError as exc:
        raise _unprocessable(str(exc)) from exc
    except (ProviderExecutionError, ProviderValidationError) as exc:
        raise _unprocessable(str(exc)) from exc
    except ValueError as exc:
        raise _not_found(str(exc)) from exc


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
