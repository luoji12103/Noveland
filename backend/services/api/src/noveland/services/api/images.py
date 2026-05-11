from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from noveland.auth import AuthenticatedSubject
from noveland.core.settings import load_settings
from noveland.media.errors import MediaConflictError, MediaNotFoundError, MediaValidationError
from noveland.media.image_contracts import (
    ImageComposeRequest,
    ImageEditRequest,
    ImageGenerateRequest,
    ImageResult,
)
from noveland.media.image_service import ImageService
from noveland.media.storage import LocalMediaObjectStorage
from noveland.providers.registry import ProviderNotFoundError, ProviderValidationError
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

router = APIRouter(prefix="/worlds/{world_id}/images", tags=["images"])


def _image_storage() -> LocalMediaObjectStorage:
    return LocalMediaObjectStorage(load_settings().object_storage_root / "media")


@router.post(
    "/generate",
    response_model=ImageResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def generate_image(
    world_id: uuid.UUID,
    request: ImageGenerateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_image_storage)],
) -> ImageResult:
    try:
        return ImageService(db_session, storage).generate_image(
            world_id,
            request,
            actor_ref=_actor_ref(subject),
        )
    except ProviderNotFoundError as exc:
        raise _not_found() from exc
    except (
        MediaValidationError,
        ProviderValidationError,
        ProviderExecutionError,
        ValueError,
    ) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/edit",
    response_model=ImageResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def edit_image(
    world_id: uuid.UUID,
    request: ImageEditRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_image_storage)],
) -> ImageResult:
    try:
        return ImageService(db_session, storage).edit_image(
            world_id,
            request,
            actor_ref=_actor_ref(subject),
        )
    except ProviderNotFoundError as exc:
        raise _not_found() from exc
    except (
        MediaValidationError,
        ProviderValidationError,
        ProviderExecutionError,
        ValueError,
    ) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/compose",
    response_model=ImageResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def compose_image(
    world_id: uuid.UUID,
    request: ImageComposeRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_image_storage)],
) -> ImageResult:
    try:
        return ImageService(db_session, storage).compose_image(
            world_id,
            request,
            actor_ref=_actor_ref(subject),
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    except (MediaConflictError, MediaValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/jobs/{job_id}")
def get_image_job(
    world_id: uuid.UUID,
    job_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_image_storage)],
) -> object:
    job = ImageService(db_session, storage).get_job(world_id, job_id)
    if job is None:
        raise _not_found()
    return job


def _actor_ref(subject: AuthenticatedSubject) -> str:
    if is_platform_admin(subject):
        return "platform_admin"
    return f"world_admin:{subject.user_id}"


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
