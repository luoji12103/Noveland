from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from noveland.auth import AuthenticatedSubject
from noveland.media.contracts import (
    MediaAssetCreate,
    MediaAssetInputCreate,
    MediaAssetInputRecord,
    MediaAssetKind,
    MediaAssetLineage,
    MediaAssetListFilters,
    MediaAssetRecord,
    MediaAssetReferences,
    MediaAssetRole,
    MediaAssetStatus,
    MediaAssetUpdate,
    MediaContextCreate,
    MediaContextRecord,
    MediaContextRole,
    MediaInputRole,
    MediaJobCreate,
    MediaJobKind,
    MediaJobRecord,
    MediaJobStatus,
    MediaSourceKind,
    MediaVisibility,
)
from noveland.media.errors import MediaConflictError, MediaNotFoundError, MediaValidationError
from noveland.media.service import MediaJobService, MediaService
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_current_subject,
    get_db_session,
    get_world_admin_context,
    get_world_member_context,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/media", tags=["media"])


class MediaAssetCreateRequest(BaseModel):
    worldline_id: uuid.UUID | None = None
    asset_kind: MediaAssetKind
    asset_role: MediaAssetRole
    source_kind: MediaSourceKind
    visibility: MediaVisibility = MediaVisibility.PRIVATE
    filename: str | None = Field(default=None, min_length=1, max_length=220)
    mime_type: str | None = Field(default=None, min_length=1, max_length=120)
    file_ext: str | None = Field(default=None, min_length=1, max_length=20)
    size_bytes: int | None = Field(default=None, ge=0)
    checksum_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    width: int | None = Field(default=None, ge=0)
    height: int | None = Field(default=None, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    sample_rate_hz: int | None = Field(default=None, ge=0)
    audio_channels: int | None = Field(default=None, ge=0)
    has_alpha: bool | None = None
    color_mode: str | None = Field(default=None, min_length=1, max_length=40)
    provider_kind: str | None = Field(default=None, min_length=1, max_length=64)
    source_job_id: uuid.UUID | None = None
    source_event_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class MediaAssetUpdateRequest(BaseModel):
    visibility: MediaVisibility | None = None
    status: MediaAssetStatus | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    metadata: dict[str, object] | None = None


class MediaContextCreateRequest(BaseModel):
    worldline_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    turn_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    world_event_id: uuid.UUID | None = None
    narrative_artifact_id: uuid.UUID | None = None
    context_role: MediaContextRole = MediaContextRole.ATTACHMENT
    metadata: dict[str, object] = Field(default_factory=dict)


class MediaAssetInputCreateRequest(BaseModel):
    worldline_id: uuid.UUID | None = None
    input_asset_id: uuid.UUID
    source_job_id: uuid.UUID | None = None
    input_role: MediaInputRole = MediaInputRole.SOURCE
    display_order: int = Field(default=0, ge=0)
    metadata: dict[str, object] = Field(default_factory=dict)


class MediaJobCreateRequest(BaseModel):
    worldline_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    turn_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    job_kind: MediaJobKind
    provider_kind: str | None = Field(default=None, min_length=1, max_length=64)
    priority: int = Field(default=0, ge=0)
    cancel_policy: str | None = Field(default=None, min_length=1, max_length=40)
    deadline_hint: datetime | None = None
    dedupe_key: str | None = Field(default=None, min_length=1, max_length=160)
    invalidation_key: str | None = Field(default=None, min_length=1, max_length=160)
    request_json: dict[str, object] = Field(default_factory=dict)


@router.get("/assets", response_model=list[MediaAssetRecord])
def list_media_assets(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
    asset_kind: Annotated[MediaAssetKind | None, Query()] = None,
    asset_role: Annotated[MediaAssetRole | None, Query()] = None,
    status_filter: Annotated[MediaAssetStatus | None, Query(alias="status")] = None,
    visibility: Annotated[MediaVisibility | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[MediaAssetRecord]:
    return MediaService(db_session).list_assets(
        world_id,
        MediaAssetListFilters(
            worldline_id=worldline_id,
            asset_kind=asset_kind,
            asset_role=asset_role,
            status=status_filter,
            visibility=visibility,
            limit=limit,
        ),
        member_visible_only=not _context.is_platform_admin and _context.role != "world_admin",
    )


@router.post(
    "/assets",
    response_model=MediaAssetRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_media_asset(
    world_id: uuid.UUID,
    request: MediaAssetCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaAssetRecord:
    try:
        return MediaService(db_session).create_asset(
            MediaAssetCreate(
                world_id=world_id,
                worldline_id=request.worldline_id,
                asset_kind=request.asset_kind,
                asset_role=request.asset_role,
                source_kind=request.source_kind,
                status=MediaAssetStatus.REGISTERED,
                visibility=request.visibility,
                filename=request.filename,
                mime_type=request.mime_type,
                file_ext=request.file_ext,
                size_bytes=request.size_bytes,
                checksum_sha256=request.checksum_sha256,
                width=request.width,
                height=request.height,
                duration_ms=request.duration_ms,
                sample_rate_hz=request.sample_rate_hz,
                audio_channels=request.audio_channels,
                has_alpha=request.has_alpha,
                color_mode=request.color_mode,
                provider_kind=request.provider_kind,
                source_job_id=request.source_job_id,
                source_event_id=request.source_event_id,
                title=request.title,
                description=request.description,
                metadata=dict(request.metadata),
            ),
            actor_ref=f"user:{subject.user_id}",
        )
    except MediaValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/assets/{asset_id}", response_model=MediaAssetRecord)
def get_media_asset(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
) -> MediaAssetRecord:
    record = MediaService(db_session).get_asset(
        world_id,
        asset_id,
        worldline_id=worldline_id,
        member_visible_only=not _context.is_platform_admin and _context.role != "world_admin",
    )
    if record is None:
        raise _not_found()
    return record


@router.patch(
    "/assets/{asset_id}",
    response_model=MediaAssetRecord,
    dependencies=[Depends(require_csrf)],
)
def update_media_asset(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    request: MediaAssetUpdateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaAssetRecord:
    try:
        return MediaService(db_session).update_asset(
            world_id,
            asset_id,
            MediaAssetUpdate(
                visibility=request.visibility,
                status=request.status,
                title=request.title,
                description=request.description,
                metadata=None if request.metadata is None else dict(request.metadata),
            ),
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    except MediaValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.delete(
    "/assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_media_asset(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        MediaService(db_session).delete_asset(world_id, asset_id)
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/assets/{asset_id}/contexts",
    response_model=MediaContextRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def attach_media_context(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    request: MediaContextCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaContextRecord:
    try:
        return MediaService(db_session).attach_context(
            world_id,
            asset_id,
            MediaContextCreate(
                world_id=world_id,
                worldline_id=request.worldline_id,
                conversation_id=request.conversation_id,
                turn_id=request.turn_id,
                agent_id=request.agent_id,
                world_event_id=request.world_event_id,
                narrative_artifact_id=request.narrative_artifact_id,
                context_role=request.context_role,
                metadata=dict(request.metadata),
            ),
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    except MediaValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/assets/{asset_id}/contexts", response_model=list[MediaContextRecord])
def list_media_contexts(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[MediaContextRecord]:
    try:
        service = MediaService(db_session)
        _require_visible_asset(service, world_id, asset_id, context)
        return service.list_contexts(world_id, asset_id)
    except MediaNotFoundError as exc:
        raise _not_found() from exc


@router.delete(
    "/assets/{asset_id}/contexts/{context_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def detach_media_context(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    context_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        MediaService(db_session).detach_context(world_id, asset_id, context_id)
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/assets/{asset_id}/inputs",
    response_model=MediaAssetInputRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def add_media_asset_input(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    request: MediaAssetInputCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaAssetInputRecord:
    try:
        return MediaService(db_session).add_input(
            world_id,
            asset_id,
            MediaAssetInputCreate(
                world_id=world_id,
                worldline_id=request.worldline_id,
                input_asset_id=request.input_asset_id,
                source_job_id=request.source_job_id,
                input_role=request.input_role,
                display_order=request.display_order,
                metadata=dict(request.metadata),
            ),
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    except MediaValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/assets/{asset_id}/inputs", response_model=list[MediaAssetInputRecord])
def list_media_asset_inputs(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[MediaAssetInputRecord]:
    try:
        service = MediaService(db_session)
        _require_visible_asset(service, world_id, asset_id, context)
        return service.list_inputs(world_id, asset_id)
    except MediaNotFoundError as exc:
        raise _not_found() from exc


@router.get("/assets/{asset_id}/references", response_model=MediaAssetReferences)
def media_asset_references(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaAssetReferences:
    try:
        service = MediaService(db_session)
        _require_visible_asset(service, world_id, asset_id, context)
        return service.references(world_id, asset_id)
    except MediaNotFoundError as exc:
        raise _not_found() from exc


@router.get("/assets/{asset_id}/lineage", response_model=MediaAssetLineage)
def media_asset_lineage(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaAssetLineage:
    try:
        service = MediaService(db_session)
        _require_visible_asset(service, world_id, asset_id, context)
        return service.lineage(world_id, asset_id)
    except MediaNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/jobs",
    response_model=MediaJobRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_media_job(
    world_id: uuid.UUID,
    request: MediaJobCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaJobRecord:
    try:
        return MediaJobService(db_session).create_job(
            MediaJobCreate(
                world_id=world_id,
                worldline_id=request.worldline_id,
                conversation_id=request.conversation_id,
                turn_id=request.turn_id,
                agent_id=request.agent_id,
                job_kind=request.job_kind,
                provider_kind=request.provider_kind,
                priority=request.priority,
                cancel_policy=request.cancel_policy,
                deadline_hint=request.deadline_hint,
                dedupe_key=request.dedupe_key,
                invalidation_key=request.invalidation_key,
                request_json=dict(request.request_json),
            ),
            actor_ref=f"user:{subject.user_id}",
        )
    except MediaValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/jobs", response_model=list[MediaJobRecord])
def list_media_jobs(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
    status_filter: Annotated[MediaJobStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[MediaJobRecord]:
    try:
        return MediaJobService(db_session).list_jobs(
            world_id,
            worldline_id=worldline_id,
            status=status_filter,
            limit=limit,
        )
    except MediaValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=MediaJobRecord)
def get_media_job(
    world_id: uuid.UUID,
    job_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
) -> MediaJobRecord:
    try:
        record = MediaJobService(db_session).get_job(world_id, job_id, worldline_id=worldline_id)
    except MediaValidationError as exc:
        raise _unprocessable(str(exc)) from exc
    if record is None:
        raise _not_found()
    return record


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=MediaJobRecord,
    dependencies=[Depends(require_csrf)],
)
def cancel_media_job(
    world_id: uuid.UUID,
    job_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaJobRecord:
    try:
        return MediaJobService(db_session).cancel_job(world_id, job_id)
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    except MediaConflictError as exc:
        raise _conflict(str(exc)) from exc


@router.post(
    "/jobs/{job_id}/retry",
    response_model=MediaJobRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def retry_media_job(
    world_id: uuid.UUID,
    job_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaJobRecord:
    try:
        return MediaJobService(db_session).retry_job(
            world_id,
            job_id,
            actor_ref=f"user:{subject.user_id}",
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    except MediaConflictError as exc:
        raise _conflict(str(exc)) from exc


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _require_visible_asset(
    service: MediaService,
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    context: WorldAccessContext,
) -> None:
    record = service.get_asset_by_id(
        world_id,
        asset_id,
        member_visible_only=not context.is_platform_admin and context.role != "world_admin",
    )
    if record is None:
        raise MediaNotFoundError("media asset not found")
