from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from noveland.auth import AuthenticatedSubject
from noveland.narrative_quality.contracts import (
    NarrativeQualityContextPreview,
    NarrativeQualityContextPreviewRequest,
    NarrativeQualityContinuityReviewRequest,
    NarrativeQualityContinuityReviewResult,
    NarrativeQualityDialogueReviewRequest,
    NarrativeQualityDialogueReviewResult,
    NarrativeQualityGMProposalGenerateRequest,
    NarrativeQualityGMProposalGenerationResult,
    NarrativeQualityLongRunEvalResult,
    NarrativeQualityLongRunEvalRunRequest,
    NarrativeQualityPacingReviewRequest,
    NarrativeQualityPacingReviewResult,
    NarrativeQualityPresentationAlignmentRequest,
    NarrativeQualityPresentationAlignmentResult,
    NarrativeQualityProgressionReviewRequest,
    NarrativeQualityProgressionReviewResult,
    NarrativeQualityWriterGenerateRequest,
    NarrativeQualityWriterGenerationResult,
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


@router.post(
    "/dialogue/review",
    response_model=NarrativeQualityDialogueReviewResult,
    dependencies=[Depends(require_csrf)],
)
def review_dialogue_style_and_ooc(
    world_id: uuid.UUID,
    request: NarrativeQualityDialogueReviewRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> NarrativeQualityDialogueReviewResult:
    try:
        return NarrativeQualityService(db_session).review_dialogue(world_id, request)
    except NarrativeQualityValidationError as exc:
        raise _unprocessable(str(exc)) from exc
    except ValueError as exc:
        raise _not_found(str(exc)) from exc


@router.post(
    "/presentations/alignment",
    response_model=NarrativeQualityPresentationAlignmentResult,
    dependencies=[Depends(require_csrf)],
)
def review_presentation_alignment(
    world_id: uuid.UUID,
    request: NarrativeQualityPresentationAlignmentRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> NarrativeQualityPresentationAlignmentResult:
    try:
        return NarrativeQualityService(db_session).review_presentation_alignment(
            world_id,
            request,
        )
    except NarrativeQualityValidationError as exc:
        raise _unprocessable(str(exc)) from exc
    except ValueError as exc:
        raise _not_found(str(exc)) from exc


@router.post(
    "/writer/generate",
    response_model=NarrativeQualityWriterGenerationResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def generate_narrative_writer_v2_draft(
    world_id: uuid.UUID,
    request: NarrativeQualityWriterGenerateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> NarrativeQualityWriterGenerationResult:
    actor_ref = "platform_admin" if is_platform_admin(subject) else f"world_admin:{subject.user_id}"
    try:
        return NarrativeQualityService(db_session).generate_narrative_v2(
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


@router.post(
    "/continuity/review",
    response_model=NarrativeQualityContinuityReviewResult,
    dependencies=[Depends(require_csrf)],
)
def review_narrative_continuity_v2(
    world_id: uuid.UUID,
    request: NarrativeQualityContinuityReviewRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> NarrativeQualityContinuityReviewResult:
    try:
        return NarrativeQualityService(db_session).review_continuity_v2(world_id, request)
    except NarrativeQualityValidationError as exc:
        raise _unprocessable(str(exc)) from exc
    except ValueError as exc:
        raise _not_found(str(exc)) from exc


@router.post(
    "/pacing/review",
    response_model=NarrativeQualityPacingReviewResult,
    dependencies=[Depends(require_csrf)],
)
def review_runtime_pacing(
    world_id: uuid.UUID,
    request: NarrativeQualityPacingReviewRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> NarrativeQualityPacingReviewResult:
    try:
        return NarrativeQualityService(db_session).review_runtime_pacing(world_id, request)
    except NarrativeQualityValidationError as exc:
        raise _unprocessable(str(exc)) from exc
    except ValueError as exc:
        raise _not_found(str(exc)) from exc


@router.post(
    "/progression/review",
    response_model=NarrativeQualityProgressionReviewResult,
    dependencies=[Depends(require_csrf)],
)
def review_route_relationship_progression(
    world_id: uuid.UUID,
    request: NarrativeQualityProgressionReviewRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> NarrativeQualityProgressionReviewResult:
    try:
        return NarrativeQualityService(db_session).review_route_relationship_progression(
            world_id,
            request,
        )
    except NarrativeQualityValidationError as exc:
        raise _unprocessable(str(exc)) from exc
    except ValueError as exc:
        raise _not_found(str(exc)) from exc


@router.post(
    "/long-run-evals/run",
    response_model=NarrativeQualityLongRunEvalResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def run_long_living_world_simulation_eval(
    world_id: uuid.UUID,
    request: NarrativeQualityLongRunEvalRunRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> NarrativeQualityLongRunEvalResult:
    try:
        return NarrativeQualityService(db_session).run_long_living_world_eval(
            world_id,
            request,
        )
    except NarrativeQualityValidationError as exc:
        raise _unprocessable(str(exc)) from exc
    except ValueError as exc:
        raise _not_found(str(exc)) from exc


@router.get("/long-run-evals", response_model=list[NarrativeQualityLongRunEvalResult])
def list_long_living_world_simulation_evals(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[NarrativeQualityLongRunEvalResult]:
    try:
        return NarrativeQualityService(db_session).list_long_living_world_evals(
            world_id,
            worldline_id,
            limit=limit,
        )
    except NarrativeQualityValidationError as exc:
        raise _unprocessable(str(exc)) from exc
    except ValueError as exc:
        raise _not_found(str(exc)) from exc


@router.get(
    "/long-run-evals/{run_id}",
    response_model=NarrativeQualityLongRunEvalResult,
)
def get_long_living_world_simulation_eval(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
) -> NarrativeQualityLongRunEvalResult:
    try:
        return NarrativeQualityService(db_session).get_long_living_world_eval(
            world_id,
            worldline_id,
            run_id,
        )
    except NarrativeQualityValidationError as exc:
        raise _unprocessable(str(exc)) from exc
    except ValueError as exc:
        raise _not_found(str(exc)) from exc


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
