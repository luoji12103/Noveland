from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import Response as FastAPIResponse
from noveland.auth import AuthenticatedSubject
from noveland.core.settings import load_settings
from noveland.media.catalog import (
    MediaCatalogService,
    MediaCollectionService,
    MediaLineageService,
)
from noveland.media.contracts import (
    ConversationTurnMediaAttachmentCreate,
    ConversationTurnMediaAttachmentRecord,
    MediaAssetCollectionCreate,
    MediaAssetCollectionItemCreate,
    MediaAssetCollectionItemRecord,
    MediaAssetCollectionItemUpdate,
    MediaAssetCollectionRecord,
    MediaAssetCollectionUpdate,
    MediaAssetCreate,
    MediaAssetInputCreate,
    MediaAssetInputRecord,
    MediaAssetKind,
    MediaAssetLineage,
    MediaAssetListFilters,
    MediaAssetRecord,
    MediaAssetReferences,
    MediaAssetRole,
    MediaAssetSearchFilters,
    MediaAssetSearchResult,
    MediaAssetStatus,
    MediaAssetTagCreate,
    MediaAssetTagFilter,
    MediaAssetTagRecord,
    MediaAssetTagUpdate,
    MediaAssetUpdate,
    MediaAssetUploadRequest,
    MediaAssetUploadResponse,
    MediaCollectionStatus,
    MediaContextCreate,
    MediaContextRecord,
    MediaContextRole,
    MediaInputRole,
    MediaJobCreate,
    MediaJobKind,
    MediaJobListFilters,
    MediaJobRecord,
    MediaJobStatus,
    MediaJobUpdate,
    MediaObjectCreate,
    MediaObjectRecord,
    MediaObjectRole,
    MediaReferenceCreate,
    MediaReferenceKind,
    MediaReferenceListFilters,
    MediaReferenceRecord,
    MediaReferenceRole,
    MediaSourceKind,
    MediaTagSourceKind,
    MediaVisibility,
)
from noveland.media.errors import (
    MediaConflictError,
    MediaNotFoundError,
    MediaStorageError,
    MediaValidationError,
)
from noveland.media.service import MediaJobService, MediaReferenceService, MediaService
from noveland.media.storage import LocalMediaObjectStorage
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
turn_media_router = APIRouter(
    prefix="/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/media",
    tags=["media"],
)

_MEMBER_METADATA_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "token",
    "bearer_token",
    "authorization",
    "secret",
    "client_secret",
    "access_key",
    "password",
    "private_key",
    "auth_ref",
    "storage_uri",
    "preview_uri",
    "thumbnail_uri",
    "object_path",
    "file_path",
    "filesystem_path",
    "local_model_path",
    "bytes",
    "base64",
    "raw_prompt",
    "raw_output",
    "prompt_snapshot",
    "provider_health",
    "diagnostics",
}
_MEMBER_METADATA_LEAK_PATTERN = re.compile(
    r"(storage_uri|media://|file://|s3://|gs://|/root/|/tmp/|base64,|"
    r"BEGIN PRIVATE KEY|sk-[A-Za-z0-9]|raw_prompt|raw_output|prompt_snapshot|"
    r"authorization|bearer\s+)",
    re.IGNORECASE,
)


def _media_storage() -> LocalMediaObjectStorage:
    return LocalMediaObjectStorage(load_settings().object_storage_root / "media")


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
    source_invocation_id: uuid.UUID | None = None
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
    source_event_id: uuid.UUID | None = None
    source_invocation_id: uuid.UUID | None = None
    provider_config_json: dict[str, object] = Field(default_factory=dict)
    request_json: dict[str, object] = Field(default_factory=dict)


class MediaJobUpdateRequest(BaseModel):
    status: MediaJobStatus | None = None
    priority: int | None = Field(default=None, ge=0)
    cancel_policy: str | None = Field(default=None, min_length=1, max_length=40)
    deadline_hint: datetime | None = None
    provider_kind: str | None = Field(default=None, min_length=1, max_length=64)
    provider_config_json: dict[str, object] | None = None
    request_json: dict[str, object] | None = None
    result_json: dict[str, object] | None = None
    error_text: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class MediaObjectCreateRequest(BaseModel):
    worldline_id: uuid.UUID | None = None
    object_role: MediaObjectRole = MediaObjectRole.ORIGINAL
    storage_uri: str = Field(min_length=1, max_length=500)
    filename: str | None = Field(default=None, min_length=1, max_length=220)
    mime_type: str = Field(min_length=1, max_length=120)
    size_bytes: int = Field(ge=0)
    checksum_sha256: str = Field(min_length=64, max_length=64)
    width: int | None = Field(default=None, ge=0)
    height: int | None = Field(default=None, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    sample_rate_hz: int | None = Field(default=None, ge=0)
    audio_channels: int | None = Field(default=None, ge=0)
    frame_rate: float | None = Field(default=None, ge=0)
    metadata: dict[str, object] = Field(default_factory=dict)


class MediaReferenceCreateRequest(BaseModel):
    worldline_id: uuid.UUID | None = None
    asset_id: uuid.UUID
    ref_kind: MediaReferenceKind
    ref_id: uuid.UUID
    ref_role: MediaReferenceRole = MediaReferenceRole.ATTACHMENT
    display_order: int = Field(default=0, ge=0)
    metadata: dict[str, object] = Field(default_factory=dict)


class ConversationTurnMediaAttachmentCreateRequest(BaseModel):
    worldline_id: uuid.UUID | None = None
    asset_id: uuid.UUID
    attachment_role: MediaReferenceRole = MediaReferenceRole.ATTACHMENT
    display_order: int = Field(default=0, ge=0)
    metadata: dict[str, object] = Field(default_factory=dict)


class MediaAssetTagCreateRequest(BaseModel):
    worldline_id: uuid.UUID | None = None
    tag_type: str = Field(min_length=1, max_length=40)
    tag_key: str = Field(min_length=1, max_length=80)
    tag_value: str = Field(min_length=1, max_length=220)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_kind: MediaTagSourceKind = MediaTagSourceKind.MANUAL
    visibility: MediaVisibility = MediaVisibility.WORLD_ADMIN
    metadata: dict[str, object] = Field(default_factory=dict)


class MediaAssetTagUpdateRequest(BaseModel):
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    visibility: MediaVisibility | None = None
    metadata: dict[str, object] | None = None


class MediaAssetCollectionCreateRequest(BaseModel):
    worldline_id: uuid.UUID | None = None
    collection_kind: str = Field(min_length=1, max_length=60)
    title: str = Field(min_length=1, max_length=160)
    description: str | None = None
    owner_agent_id: uuid.UUID | None = None
    visibility: MediaVisibility = MediaVisibility.WORLD_ADMIN
    metadata: dict[str, object] = Field(default_factory=dict)


class MediaAssetCollectionUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    visibility: MediaVisibility | None = None
    status: MediaCollectionStatus | None = None
    metadata: dict[str, object] | None = None


class MediaAssetCollectionItemCreateRequest(BaseModel):
    worldline_id: uuid.UUID | None = None
    asset_id: uuid.UUID
    role: str = Field(default="member", min_length=1, max_length=40)
    display_order: int = Field(default=0, ge=0)
    metadata: dict[str, object] = Field(default_factory=dict)


class MediaAssetCollectionItemUpdateRequest(BaseModel):
    display_order: int | None = Field(default=None, ge=0)
    metadata: dict[str, object] | None = None


@router.get("/assets", response_model=list[MediaAssetRecord])
def list_media_assets(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
    asset_kind: Annotated[MediaAssetKind | None, Query()] = None,
    asset_role: Annotated[MediaAssetRole | None, Query()] = None,
    source_kind: Annotated[MediaSourceKind | None, Query()] = None,
    status_filter: Annotated[MediaAssetStatus | None, Query(alias="status")] = None,
    visibility: Annotated[MediaVisibility | None, Query()] = None,
    created_after: Annotated[datetime | None, Query()] = None,
    created_before: Annotated[datetime | None, Query()] = None,
    source_event_id: Annotated[uuid.UUID | None, Query()] = None,
    source_invocation_id: Annotated[uuid.UUID | None, Query()] = None,
    ref_kind: Annotated[MediaReferenceKind | None, Query()] = None,
    ref_id: Annotated[uuid.UUID | None, Query()] = None,
    contains_text: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[MediaAssetRecord]:
    try:
        member_visible_only = _member_visible_only(_context)
        assets = MediaService(db_session).list_assets(
            world_id,
            MediaAssetListFilters(
                worldline_id=worldline_id,
                asset_kind=asset_kind,
                asset_role=asset_role,
                source_kind=source_kind,
                status=status_filter,
                visibility=visibility,
                created_after=created_after,
                created_before=created_before,
                source_event_id=source_event_id,
                source_invocation_id=source_invocation_id,
                ref_kind=ref_kind,
                ref_id=ref_id,
                contains_text=contains_text,
                limit=limit,
            ),
            member_visible_only=member_visible_only,
        )
        return [_media_asset_record_for_context(asset, _context) for asset in assets]
    except (MediaValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/assets/search", response_model=MediaAssetSearchResult)
def search_media_assets(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
    asset_kind: Annotated[MediaAssetKind | None, Query()] = None,
    asset_role: Annotated[MediaAssetRole | None, Query()] = None,
    source_kind: Annotated[MediaSourceKind | None, Query()] = None,
    status_filter: Annotated[MediaAssetStatus | None, Query(alias="status")] = None,
    visibility: Annotated[MediaVisibility | None, Query()] = None,
    has_alpha: Annotated[bool | None, Query()] = None,
    mime_type: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    provider_kind: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    used_by_agent_id: Annotated[uuid.UUID | None, Query()] = None,
    used_in_conversation_id: Annotated[uuid.UUID | None, Query()] = None,
    used_in_turn_id: Annotated[uuid.UUID | None, Query()] = None,
    used_in_world_event_id: Annotated[uuid.UUID | None, Query()] = None,
    collection_id: Annotated[uuid.UUID | None, Query()] = None,
    contains_text: Annotated[str | None, Query(max_length=120)] = None,
    tag: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> MediaAssetSearchResult:
    try:
        result = MediaCatalogService(db_session).search_assets(
            world_id,
            MediaAssetSearchFilters(
                worldline_id=worldline_id,
                asset_kind=asset_kind,
                asset_role=asset_role,
                source_kind=source_kind,
                status=status_filter,
                visibility=visibility,
                has_alpha=has_alpha,
                mime_type=mime_type,
                provider_kind=provider_kind,
                used_by_agent_id=used_by_agent_id,
                used_in_conversation_id=used_in_conversation_id,
                used_in_turn_id=used_in_turn_id,
                used_in_world_event_id=used_in_world_event_id,
                collection_id=collection_id,
                contains_text=contains_text,
                tags=tuple(_parse_tag_filters([] if tag is None else tag)),
                limit=limit,
            ),
            member_visible_only=_member_visible_only(context),
        )
        return result.model_copy(
            update={
                "assets": [
                    _media_asset_record_for_context(asset, context) for asset in result.assets
                ]
            }
        )
    except ValueError as exc:
        raise _unprocessable(str(exc)) from exc
    except MediaValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/assets/upload",
    response_model=MediaAssetUploadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def upload_media_asset(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_media_storage)],
    file: Annotated[UploadFile, File()],
    worldline_id: Annotated[uuid.UUID | None, Form()] = None,
    asset_kind: Annotated[MediaAssetKind, Form()] = MediaAssetKind.IMAGE,
    asset_role: Annotated[MediaAssetRole, Form()] = MediaAssetRole.REFERENCE_IMAGE,
    visibility: Annotated[MediaVisibility, Form()] = MediaVisibility.PRIVATE,
    title: Annotated[str | None, Form(max_length=160)] = None,
    description: Annotated[str | None, Form()] = None,
    metadata_json: Annotated[str | None, Form()] = None,
) -> MediaAssetUploadResponse:
    try:
        data = await file.read()
        metadata = _parse_multipart_json_object(metadata_json, "metadata_json")
        return MediaService(db_session, storage).upload_asset(
            MediaAssetUploadRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind=asset_kind,
                asset_role=asset_role,
                visibility=visibility,
                title=title,
                description=description,
                metadata=metadata,
            ),
            data=data,
            filename=Path(file.filename or "").name or None,
            mime_type=file.content_type or "application/octet-stream",
            actor_ref=f"user:{subject.user_id}",
        )
    except (MediaValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


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
                source_invocation_id=request.source_invocation_id,
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
        allow_restricted=_context.is_platform_admin,
    )
    if record is None:
        raise _not_found()
    return _media_asset_record_for_context(record, _context)


@router.get("/assets/{asset_id}/objects", response_model=list[MediaObjectRecord])
def list_media_asset_objects(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[MediaObjectRecord]:
    try:
        return MediaService(db_session).list_objects(
            world_id,
            asset_id,
            allow_restricted=context.is_platform_admin,
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/assets/{asset_id}/objects",
    response_model=MediaObjectRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_media_asset_object(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    request: MediaObjectCreateRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_media_storage)],
) -> MediaObjectRecord:
    try:
        service = MediaService(db_session)
        _require_visible_asset(service, world_id, asset_id, context)
        return MediaService(db_session, storage).add_object(
            world_id,
            asset_id,
            MediaObjectCreate(
                world_id=world_id,
                worldline_id=request.worldline_id,
                object_role=request.object_role,
                storage_uri=request.storage_uri,
                filename=request.filename,
                mime_type=request.mime_type,
                size_bytes=request.size_bytes,
                checksum_sha256=request.checksum_sha256,
                width=request.width,
                height=request.height,
                duration_ms=request.duration_ms,
                sample_rate_hz=request.sample_rate_hz,
                audio_channels=request.audio_channels,
                frame_rate=request.frame_rate,
                metadata=dict(request.metadata),
            ),
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    except (MediaValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/objects/{object_id}/download")
def download_media_object(
    world_id: uuid.UUID,
    object_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_media_storage)],
) -> FastAPIResponse:
    try:
        media_object, data = MediaService(db_session, storage).read_object_bytes(
            world_id,
            object_id,
            allow_restricted=context.is_platform_admin,
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    except MediaValidationError as exc:
        raise _unprocessable(str(exc)) from exc
    except MediaStorageError as exc:
        raise _not_found() from exc
    return FastAPIResponse(
        content=data,
        media_type=media_object.mime_type,
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.get("/assets/{asset_id}/tags", response_model=list[MediaAssetTagRecord])
def list_media_asset_tags(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[MediaAssetTagRecord]:
    try:
        service = MediaService(db_session)
        _require_visible_asset(service, world_id, asset_id, context)
        return [
            _media_asset_tag_record_for_context(record, context)
            for record in MediaCatalogService(db_session).list_tags(
                world_id,
                asset_id,
                member_visible_only=_member_visible_only(context),
            )
        ]
    except MediaNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/assets/{asset_id}/tags",
    response_model=MediaAssetTagRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_media_asset_tag(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    request: MediaAssetTagCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaAssetTagRecord:
    try:
        return MediaCatalogService(db_session).create_tag(
            world_id,
            asset_id,
            MediaAssetTagCreate(
                world_id=world_id,
                worldline_id=request.worldline_id,
                tag_type=request.tag_type,
                tag_key=request.tag_key,
                tag_value=request.tag_value,
                confidence=request.confidence,
                source_kind=request.source_kind,
                visibility=request.visibility,
                metadata=dict(request.metadata),
            ),
            actor_ref=f"user:{subject.user_id}",
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    except (MediaValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.patch(
    "/assets/{asset_id}/tags/{tag_id}",
    response_model=MediaAssetTagRecord,
    dependencies=[Depends(require_csrf)],
)
def update_media_asset_tag(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    tag_id: uuid.UUID,
    request: MediaAssetTagUpdateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaAssetTagRecord:
    try:
        return MediaCatalogService(db_session).update_tag(
            world_id,
            asset_id,
            tag_id,
            MediaAssetTagUpdate(
                confidence=request.confidence,
                visibility=request.visibility,
                metadata=None if request.metadata is None else dict(request.metadata),
            ),
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc


@router.delete(
    "/assets/{asset_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_media_asset_tag(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    tag_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        MediaCatalogService(db_session).delete_tag(world_id, asset_id, tag_id)
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
        return [
            _media_context_record_for_context(record, context)
            for record in service.list_contexts(world_id, asset_id)
        ]
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
        return [
            _media_asset_input_record_for_context(record, context)
            for record in service.list_inputs(world_id, asset_id)
        ]
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
        references = MediaLineageService(db_session).references(
            world_id,
            asset_id,
            member_visible_only=_member_visible_only(context),
        )
        return references.model_copy(
            update={
                "contexts": [
                    _media_context_record_for_context(record, context)
                    for record in references.contexts
                ],
                "tags": [
                    _media_asset_tag_record_for_context(record, context)
                    for record in references.tags
                ],
                "collections": [
                    _media_asset_collection_record_for_context(record, context)
                    for record in references.collections
                ],
            }
        )
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
        lineage = MediaLineageService(db_session).lineage(
            world_id,
            asset_id,
            member_visible_only=_member_visible_only(context),
        )
        return lineage.model_copy(
            update={
                "inputs": [
                    _media_asset_input_record_for_context(record, context)
                    for record in lineage.inputs
                ],
                "outputs": [
                    _media_asset_input_record_for_context(record, context)
                    for record in lineage.outputs
                ],
                "related_assets": [
                    _media_asset_record_for_context(asset, context)
                    for asset in lineage.related_assets
                ]
            }
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc


@router.get("/collections", response_model=list[MediaAssetCollectionRecord])
def list_media_asset_collections(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
    collection_kind: Annotated[str | None, Query(min_length=1, max_length=60)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[MediaAssetCollectionRecord]:
    try:
        return [
            _media_asset_collection_record_for_context(record, context)
            for record in MediaCollectionService(db_session).list_collections(
                world_id,
                worldline_id=worldline_id,
                collection_kind=None
                if collection_kind is None
                else collection_kind.strip().lower(),
                member_visible_only=_member_visible_only(context),
                limit=limit,
            )
        ]
    except MediaValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/collections",
    response_model=MediaAssetCollectionRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_media_asset_collection(
    world_id: uuid.UUID,
    request: MediaAssetCollectionCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaAssetCollectionRecord:
    try:
        return MediaCollectionService(db_session).create_collection(
            MediaAssetCollectionCreate(
                world_id=world_id,
                worldline_id=request.worldline_id,
                collection_kind=request.collection_kind,
                title=request.title,
                description=request.description,
                owner_agent_id=request.owner_agent_id,
                visibility=request.visibility,
                metadata=dict(request.metadata),
            ),
            actor_ref=f"user:{subject.user_id}",
        )
    except (MediaValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/collections/{collection_id}", response_model=MediaAssetCollectionRecord)
def get_media_asset_collection(
    world_id: uuid.UUID,
    collection_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaAssetCollectionRecord:
    record = MediaCollectionService(db_session).get_collection(
        world_id,
        collection_id,
        member_visible_only=_member_visible_only(context),
    )
    if record is None:
        raise _not_found()
    return _media_asset_collection_record_for_context(record, context)


@router.patch(
    "/collections/{collection_id}",
    response_model=MediaAssetCollectionRecord,
    dependencies=[Depends(require_csrf)],
)
def update_media_asset_collection(
    world_id: uuid.UUID,
    collection_id: uuid.UUID,
    request: MediaAssetCollectionUpdateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaAssetCollectionRecord:
    try:
        return MediaCollectionService(db_session).update_collection(
            world_id,
            collection_id,
            MediaAssetCollectionUpdate(
                title=request.title,
                description=request.description,
                visibility=request.visibility,
                status=request.status,
                metadata=None if request.metadata is None else dict(request.metadata),
            ),
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc


@router.delete(
    "/collections/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_media_asset_collection(
    world_id: uuid.UUID,
    collection_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        MediaCollectionService(db_session).delete_collection(world_id, collection_id)
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/collections/{collection_id}/items",
    response_model=list[MediaAssetCollectionItemRecord],
)
def list_media_asset_collection_items(
    world_id: uuid.UUID,
    collection_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[MediaAssetCollectionItemRecord]:
    try:
        return [
            _media_asset_collection_item_record_for_context(record, context)
            for record in MediaCollectionService(db_session).list_items(
                world_id,
                collection_id,
                member_visible_only=_member_visible_only(context),
            )
        ]
    except MediaNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/collections/{collection_id}/items",
    response_model=MediaAssetCollectionItemRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def add_media_asset_collection_item(
    world_id: uuid.UUID,
    collection_id: uuid.UUID,
    request: MediaAssetCollectionItemCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaAssetCollectionItemRecord:
    try:
        return MediaCollectionService(db_session).add_item(
            world_id,
            collection_id,
            MediaAssetCollectionItemCreate(
                world_id=world_id,
                worldline_id=request.worldline_id,
                asset_id=request.asset_id,
                role=request.role,
                display_order=request.display_order,
                metadata=dict(request.metadata),
            ),
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    except (MediaValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.patch(
    "/collections/{collection_id}/items/{item_id}",
    response_model=MediaAssetCollectionItemRecord,
    dependencies=[Depends(require_csrf)],
)
def update_media_asset_collection_item(
    world_id: uuid.UUID,
    collection_id: uuid.UUID,
    item_id: uuid.UUID,
    request: MediaAssetCollectionItemUpdateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaAssetCollectionItemRecord:
    try:
        return MediaCollectionService(db_session).update_item(
            world_id,
            collection_id,
            item_id,
            MediaAssetCollectionItemUpdate(
                display_order=request.display_order,
                metadata=None if request.metadata is None else dict(request.metadata),
            ),
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc


@router.delete(
    "/collections/{collection_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def remove_media_asset_collection_item(
    world_id: uuid.UUID,
    collection_id: uuid.UUID,
    item_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        MediaCollectionService(db_session).remove_item(world_id, collection_id, item_id)
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/references", response_model=list[MediaReferenceRecord])
def list_media_references(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
    asset_id: Annotated[uuid.UUID | None, Query()] = None,
    ref_kind: Annotated[MediaReferenceKind | None, Query()] = None,
    ref_id: Annotated[uuid.UUID | None, Query()] = None,
    ref_role: Annotated[MediaReferenceRole | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[MediaReferenceRecord]:
    try:
        return MediaReferenceService(db_session).list_references(
            world_id,
            MediaReferenceListFilters(
                worldline_id=worldline_id,
                asset_id=asset_id,
                ref_kind=ref_kind,
                ref_id=ref_id,
                ref_role=ref_role,
                limit=limit,
            ),
            allow_restricted_assets=context.is_platform_admin,
        )
    except MediaValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/references",
    response_model=MediaReferenceRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_media_reference(
    world_id: uuid.UUID,
    request: MediaReferenceCreateRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaReferenceRecord:
    try:
        return MediaReferenceService(db_session).create_reference(
            MediaReferenceCreate(
                world_id=world_id,
                worldline_id=request.worldline_id,
                asset_id=request.asset_id,
                ref_kind=request.ref_kind,
                ref_id=request.ref_id,
                ref_role=request.ref_role,
                display_order=request.display_order,
                metadata=dict(request.metadata),
            ),
            allow_restricted_assets=context.is_platform_admin,
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    except (MediaValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.delete(
    "/references/{reference_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_media_reference(
    world_id: uuid.UUID,
    reference_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        MediaReferenceService(db_session).delete_reference(
            world_id,
            reference_id,
            allow_restricted_assets=context.is_platform_admin,
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
                source_event_id=request.source_event_id,
                source_invocation_id=request.source_invocation_id,
                provider_config_json=dict(request.provider_config_json),
                request_json=dict(request.request_json),
            ),
            actor_ref=f"user:{subject.user_id}",
        )
    except MediaValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/jobs", response_model=list[MediaJobRecord])
def list_media_jobs(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
    job_kind: Annotated[MediaJobKind | None, Query()] = None,
    status_filter: Annotated[MediaJobStatus | None, Query(alias="status")] = None,
    priority_min: Annotated[int | None, Query(ge=0)] = None,
    priority_max: Annotated[int | None, Query(ge=0)] = None,
    agent_id: Annotated[uuid.UUID | None, Query()] = None,
    conversation_id: Annotated[uuid.UUID | None, Query()] = None,
    turn_id: Annotated[uuid.UUID | None, Query()] = None,
    source_event_id: Annotated[uuid.UUID | None, Query()] = None,
    source_invocation_id: Annotated[uuid.UUID | None, Query()] = None,
    provider_kind: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    invalidation_key: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
    created_after: Annotated[datetime | None, Query()] = None,
    created_before: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[MediaJobRecord]:
    try:
        return MediaJobService(db_session).list_jobs(
            world_id,
            MediaJobListFilters(
                worldline_id=worldline_id,
                job_kind=job_kind,
                status=status_filter,
                priority_min=priority_min,
                priority_max=priority_max,
                agent_id=agent_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                source_event_id=source_event_id,
                source_invocation_id=source_invocation_id,
                provider_kind=provider_kind,
                invalidation_key=invalidation_key,
                created_after=created_after,
                created_before=created_before,
                limit=limit,
            ),
        )
    except MediaValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=MediaJobRecord)
def get_media_job(
    world_id: uuid.UUID,
    job_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
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


@router.patch(
    "/jobs/{job_id}",
    response_model=MediaJobRecord,
    dependencies=[Depends(require_csrf)],
)
def update_media_job(
    world_id: uuid.UUID,
    job_id: uuid.UUID,
    request: MediaJobUpdateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaJobRecord:
    try:
        return MediaJobService(db_session).update_job(
            world_id,
            job_id,
            MediaJobUpdate(
                status=request.status,
                priority=request.priority,
                cancel_policy=request.cancel_policy,
                deadline_hint=request.deadline_hint,
                provider_kind=request.provider_kind,
                provider_config_json=(
                    None
                    if request.provider_config_json is None
                    else dict(request.provider_config_json)
                ),
                request_json=None if request.request_json is None else dict(request.request_json),
                result_json=None if request.result_json is None else dict(request.result_json),
                error_text=request.error_text,
                started_at=request.started_at,
                finished_at=request.finished_at,
            ),
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    except (MediaValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


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


@turn_media_router.get("", response_model=list[ConversationTurnMediaAttachmentRecord])
def list_conversation_turn_media(
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[ConversationTurnMediaAttachmentRecord]:
    try:
        return MediaReferenceService(db_session).list_turn_media(
            world_id,
            conversation_id,
            turn_id,
            allow_restricted_assets=context.is_platform_admin,
        )
    except MediaValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@turn_media_router.post(
    "",
    response_model=MediaReferenceRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_conversation_turn_media(
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
    request: ConversationTurnMediaAttachmentCreateRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MediaReferenceRecord:
    try:
        return MediaReferenceService(db_session).create_turn_media(
            world_id,
            conversation_id,
            turn_id,
            ConversationTurnMediaAttachmentCreate(
                worldline_id=request.worldline_id,
                asset_id=request.asset_id,
                attachment_role=request.attachment_role,
                display_order=request.display_order,
                metadata=dict(request.metadata),
            ),
            allow_restricted_assets=context.is_platform_admin,
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    except (MediaValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@turn_media_router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_conversation_turn_media(
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
    asset_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        MediaReferenceService(db_session).delete_turn_media(
            world_id,
            conversation_id,
            turn_id,
            asset_id,
            allow_restricted_assets=context.is_platform_admin,
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    except MediaValidationError as exc:
        raise _unprocessable(str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
        allow_restricted=context.is_platform_admin,
    )
    if record is None:
        raise MediaNotFoundError("media asset not found")


def _member_visible_only(context: WorldAccessContext) -> bool:
    return not context.is_platform_admin and context.role != "world_admin"


def _media_asset_record_for_context(
    record: MediaAssetRecord,
    context: WorldAccessContext,
) -> MediaAssetRecord:
    if not _member_visible_only(context):
        return record
    return record.model_copy(
        update={
            "storage_uri": None,
            "preview_uri": None,
            "thumbnail_uri": None,
            "metadata": _sanitize_member_metadata(record.metadata),
        }
    )


def _media_context_record_for_context(
    record: MediaContextRecord,
    context: WorldAccessContext,
) -> MediaContextRecord:
    if not _member_visible_only(context):
        return record
    return record.model_copy(update={"metadata": _sanitize_member_metadata(record.metadata)})


def _media_asset_input_record_for_context(
    record: MediaAssetInputRecord,
    context: WorldAccessContext,
) -> MediaAssetInputRecord:
    if not _member_visible_only(context):
        return record
    return record.model_copy(update={"metadata": _sanitize_member_metadata(record.metadata)})


def _media_asset_tag_record_for_context(
    record: MediaAssetTagRecord,
    context: WorldAccessContext,
) -> MediaAssetTagRecord:
    if not _member_visible_only(context):
        return record
    return record.model_copy(update={"metadata": _sanitize_member_metadata(record.metadata)})


def _media_asset_collection_record_for_context(
    record: MediaAssetCollectionRecord,
    context: WorldAccessContext,
) -> MediaAssetCollectionRecord:
    if not _member_visible_only(context):
        return record
    return record.model_copy(update={"metadata": _sanitize_member_metadata(record.metadata)})


def _media_asset_collection_item_record_for_context(
    record: MediaAssetCollectionItemRecord,
    context: WorldAccessContext,
) -> MediaAssetCollectionItemRecord:
    if not _member_visible_only(context):
        return record
    return record.model_copy(update={"metadata": _sanitize_member_metadata(record.metadata)})


def _sanitize_member_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    sanitized = _sanitize_member_metadata_value(metadata)
    return sanitized if isinstance(sanitized, dict) else {}


def _sanitize_member_metadata_value(value: object) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for raw_key, item in value.items():
            key = str(raw_key)
            if key.strip().lower() in _MEMBER_METADATA_SENSITIVE_KEYS:
                continue
            clean_item = _sanitize_member_metadata_value(item)
            if clean_item is not None:
                sanitized[key] = clean_item
        return sanitized
    if isinstance(value, list | tuple | set):
        return [
            clean_item
            for clean_item in (_sanitize_member_metadata_value(item) for item in list(value)[:50])
            if clean_item is not None
        ]
    if isinstance(value, str):
        return None if _MEMBER_METADATA_LEAK_PATTERN.search(value) else value[:500]
    if value is None or isinstance(value, bool | int | float):
        return value
    return str(value)[:200]


def _parse_tag_filters(encoded_filters: list[str]) -> list[MediaAssetTagFilter]:
    filters: list[MediaAssetTagFilter] = []
    for encoded in encoded_filters:
        filters.append(MediaAssetTagFilter.parse(encoded))
    return filters


def _parse_multipart_json_object(
    raw_value: str | None,
    field_name: str,
) -> dict[str, object]:
    if raw_value is None or raw_value.strip() == "":
        return {}
    parsed = json.loads(raw_value)
    if not isinstance(parsed, dict):
        raise ValueError(f"{field_name} must be a JSON object")
    return parsed
