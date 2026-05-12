from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from noveland.core.settings import load_settings
from noveland.media.errors import MediaConflictError, MediaNotFoundError, MediaValidationError
from noveland.media.storage import LocalMediaObjectStorage
from noveland.services.api.authorization import is_platform_admin
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_db_session,
    get_world_admin_context,
)
from noveland.visual.composition import VisualCompositionService
from noveland.visual.contracts import (
    BackgroundResolveRequest,
    BackgroundResolveResult,
    SceneBackgroundCreate,
    SceneBackgroundRead,
    SceneBackgroundUpdate,
    SceneComposeRequest,
    SceneComposeResult,
    SpriteResolveRequest,
    SpriteResolveResult,
    SpriteSetCreate,
    SpriteSetRead,
    SpriteSetUpdate,
    SpriteVariantCreate,
    SpriteVariantRead,
    SpriteVariantUpdate,
)
from noveland.visual.resolver import VisualResolver
from noveland.visual.service import (
    VisualAssetService,
    VisualNotFoundError,
    VisualValidationError,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/visual", tags=["visual"])
RESTRICTED_VISIBILITIES = {"developer_only", "hidden"}


def _visual_storage() -> LocalMediaObjectStorage:
    return LocalMediaObjectStorage(load_settings().object_storage_root / "media")


class SpriteSetCreateRequest(BaseModel):
    worldline_id: uuid.UUID
    agent_id: uuid.UUID
    style_key: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=200)
    default_variant_id: uuid.UUID | None = None
    status: str = "active"
    visibility: str = "world_admin"
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SpriteVariantCreateRequest(BaseModel):
    worldline_id: uuid.UUID
    asset_id: uuid.UUID
    expression_key: str = Field(default="neutral", min_length=1, max_length=80)
    pose_key: str | None = Field(default=None, min_length=1, max_length=80)
    outfit_key: str | None = Field(default=None, min_length=1, max_length=80)
    mood_tags: tuple[str, ...] = ()
    priority: int = Field(default=100, ge=0)
    is_default: bool = False
    status: str = "active"
    visibility: str = "world_admin"
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class BackgroundCreateRequest(BaseModel):
    worldline_id: uuid.UUID
    scene_id: uuid.UUID | None = None
    location_key: str = Field(min_length=1, max_length=120)
    time_of_day: str | None = Field(default=None, min_length=1, max_length=40)
    weather_key: str | None = Field(default=None, min_length=1, max_length=80)
    asset_id: uuid.UUID
    priority: int = Field(default=100, ge=0)
    is_default: bool = False
    status: str = "active"
    visibility: str = "world_admin"
    metadata_json: dict[str, Any] = Field(default_factory=dict)


@router.get("/sprite-sets", response_model=list[SpriteSetRead])
def list_sprite_sets(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID,
    agent_id: uuid.UUID | None = None,
) -> list[SpriteSetRead]:
    return VisualAssetService(db_session).list_sprite_sets(
        world_id,
        worldline_id=worldline_id,
        agent_id=agent_id,
        include_restricted=context.is_platform_admin,
    )


@router.post(
    "/sprite-sets",
    response_model=SpriteSetRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_sprite_set(
    world_id: uuid.UUID,
    request: SpriteSetCreateRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SpriteSetRead:
    _reject_restricted_visibility(request.visibility, context)
    try:
        return VisualAssetService(db_session).create_sprite_set(
            SpriteSetCreate(world_id=world_id, **request.model_dump())
        )
    except MediaNotFoundError as exc:
        raise _not_found() from exc
    except (MediaConflictError, MediaValidationError, VisualValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.patch(
    "/sprite-sets/{sprite_set_id}",
    response_model=SpriteSetRead,
    dependencies=[Depends(require_csrf)],
)
def update_sprite_set(
    world_id: uuid.UUID,
    sprite_set_id: uuid.UUID,
    request: SpriteSetUpdate,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SpriteSetRead:
    if request.visibility is not None:
        _reject_restricted_visibility(request.visibility.value, context)
    try:
        return VisualAssetService(db_session).update_sprite_set(world_id, sprite_set_id, request)
    except VisualNotFoundError as exc:
        raise _not_found() from exc
    except (VisualValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.delete(
    "/sprite-sets/{sprite_set_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_sprite_set(
    world_id: uuid.UUID,
    sprite_set_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        VisualAssetService(db_session).delete_sprite_set(world_id, sprite_set_id)
    except VisualNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/sprite-sets/{sprite_set_id}/variants", response_model=list[SpriteVariantRead])
def list_sprite_variants(
    world_id: uuid.UUID,
    sprite_set_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[SpriteVariantRead]:
    try:
        return VisualAssetService(db_session).list_sprite_variants(
            world_id,
            sprite_set_id,
            include_restricted=context.is_platform_admin,
        )
    except VisualNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/sprite-sets/{sprite_set_id}/variants",
    response_model=SpriteVariantRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_sprite_variant(
    world_id: uuid.UUID,
    sprite_set_id: uuid.UUID,
    request: SpriteVariantCreateRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SpriteVariantRead:
    _reject_restricted_visibility(request.visibility, context)
    try:
        return VisualAssetService(db_session).create_sprite_variant(
            SpriteVariantCreate(
                world_id=world_id,
                sprite_set_id=sprite_set_id,
                **request.model_dump(),
            )
        )
    except (VisualValidationError, VisualNotFoundError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.patch(
    "/sprite-sets/{sprite_set_id}/variants/{variant_id}",
    response_model=SpriteVariantRead,
    dependencies=[Depends(require_csrf)],
)
def update_sprite_variant(
    world_id: uuid.UUID,
    sprite_set_id: uuid.UUID,
    variant_id: uuid.UUID,
    request: SpriteVariantUpdate,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SpriteVariantRead:
    del sprite_set_id
    if request.visibility is not None:
        _reject_restricted_visibility(request.visibility.value, context)
    try:
        return VisualAssetService(db_session).update_sprite_variant(world_id, variant_id, request)
    except VisualNotFoundError as exc:
        raise _not_found() from exc
    except (VisualValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.delete(
    "/sprite-sets/{sprite_set_id}/variants/{variant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_sprite_variant(
    world_id: uuid.UUID,
    sprite_set_id: uuid.UUID,
    variant_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    del sprite_set_id
    try:
        VisualAssetService(db_session).delete_sprite_variant(world_id, variant_id)
    except VisualNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/resolve-sprite", response_model=SpriteResolveResult)
def resolve_sprite(
    world_id: uuid.UUID,
    request: SpriteResolveRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SpriteResolveResult:
    safe_request = request.model_copy(
        update={"include_restricted": request.include_restricted and context.is_platform_admin}
    )
    try:
        return VisualResolver(db_session).resolve_sprite(world_id, safe_request)
    except (VisualValidationError, VisualNotFoundError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/backgrounds", response_model=list[SceneBackgroundRead])
def list_backgrounds(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID,
) -> list[SceneBackgroundRead]:
    return VisualAssetService(db_session).list_backgrounds(
        world_id,
        worldline_id=worldline_id,
        include_restricted=context.is_platform_admin,
    )


@router.post(
    "/backgrounds",
    response_model=SceneBackgroundRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_background(
    world_id: uuid.UUID,
    request: BackgroundCreateRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SceneBackgroundRead:
    _reject_restricted_visibility(request.visibility, context)
    try:
        return VisualAssetService(db_session).create_background(
            SceneBackgroundCreate(world_id=world_id, **request.model_dump())
        )
    except (VisualValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.patch(
    "/backgrounds/{background_id}",
    response_model=SceneBackgroundRead,
    dependencies=[Depends(require_csrf)],
)
def update_background(
    world_id: uuid.UUID,
    background_id: uuid.UUID,
    request: SceneBackgroundUpdate,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SceneBackgroundRead:
    if request.visibility is not None:
        _reject_restricted_visibility(request.visibility.value, context)
    try:
        return VisualAssetService(db_session).update_background(world_id, background_id, request)
    except VisualNotFoundError as exc:
        raise _not_found() from exc
    except (VisualValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.delete(
    "/backgrounds/{background_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_background(
    world_id: uuid.UUID,
    background_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        VisualAssetService(db_session).delete_background(world_id, background_id)
    except VisualNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/resolve-background", response_model=BackgroundResolveResult)
def resolve_background(
    world_id: uuid.UUID,
    request: BackgroundResolveRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> BackgroundResolveResult:
    safe_request = request.model_copy(
        update={"include_restricted": request.include_restricted and context.is_platform_admin}
    )
    try:
        return VisualResolver(db_session).resolve_background(world_id, safe_request)
    except (VisualValidationError, VisualNotFoundError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/compose-scene",
    response_model=SceneComposeResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def compose_scene(
    world_id: uuid.UUID,
    request: SceneComposeRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_visual_storage)],
) -> SceneComposeResult:
    try:
        return VisualCompositionService(db_session, storage).compose_scene(
            world_id,
            request,
            actor_ref=(
                "platform_admin"
                if is_platform_admin(context.subject)
                else f"world_admin:{context.subject.user_id}"
            ),
        )
    except (VisualValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


def _reject_restricted_visibility(visibility: str, context: WorldAccessContext) -> None:
    if visibility in RESTRICTED_VISIBILITIES and not context.is_platform_admin:
        raise _forbidden()


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
