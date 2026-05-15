from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response as FastAPIResponse
from noveland.core.settings import load_settings
from noveland.media.errors import MediaStorageError
from noveland.media.storage import LocalMediaObjectStorage
from noveland.reader_delivery import ReaderMediaDeliveryService
from noveland.reader_delivery.contracts import ReaderMediaDescriptor
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_db_session,
    get_world_member_context,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/reader/media", tags=["reader-media"])


def _reader_media_storage() -> LocalMediaObjectStorage:
    return LocalMediaObjectStorage(load_settings().object_storage_root / "media")


@router.get("", response_model=list[ReaderMediaDescriptor])
def list_reader_media(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[ReaderMediaDescriptor]:
    _ = context
    return ReaderMediaDeliveryService(db_session).list_media(
        world_id,
        worldline_id=worldline_id,
        limit=limit,
    )


@router.get("/objects/{object_id}/download")
def download_reader_media_object(
    world_id: uuid.UUID,
    object_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_reader_media_storage)],
    worldline_id: uuid.UUID | None = None,
) -> FastAPIResponse:
    _ = context
    try:
        result = ReaderMediaDeliveryService(db_session, storage=storage).read_object(
            world_id,
            object_id,
            worldline_id=worldline_id,
        )
    except (MediaStorageError, OSError) as exc:
        raise _not_found() from exc
    if result is None:
        raise _not_found()
    descriptor, data = result
    return FastAPIResponse(
        content=data,
        media_type=descriptor.content_type,
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.get("/{asset_id}", response_model=ReaderMediaDescriptor)
def get_reader_media(
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
) -> ReaderMediaDescriptor:
    _ = context
    descriptor = ReaderMediaDeliveryService(db_session).get_media(
        world_id,
        asset_id,
        worldline_id=worldline_id,
    )
    if descriptor is None:
        raise _not_found()
    return descriptor


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reader media not found")
