from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_db_session,
    get_world_admin_context,
)
from noveland.visual_generation.contracts import (
    CharacterVisualGenerationProfileCreate,
    CharacterVisualGenerationProfileRead,
    CharacterVisualGenerationProfileUpdate,
    VisualGenerationDryRunResult,
    VisualGenerationPlanCreate,
    VisualGenerationPlanRead,
    VisualGenerationPlanStatus,
    VisualGenerationPlanValidationResult,
    VisualModelAssetCreate,
    VisualModelAssetRead,
    VisualModelAssetUpdate,
    VisualModelInventoryKind,
    WorkflowTemplateCreate,
    WorkflowTemplateRead,
    WorkflowTemplateUpdate,
    WorkflowTemplateVersionCreate,
    WorkflowTemplateVersionRead,
)
from noveland.visual_generation.service import (
    VisualGenerationNotFoundError,
    VisualGenerationService,
    VisualGenerationValidationError,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/visual-generation", tags=["visual-generation"])


@router.get("/workflow-templates", response_model=list[WorkflowTemplateRead])
def list_workflow_templates(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[WorkflowTemplateRead]:
    return VisualGenerationService(db_session).list_workflow_templates(
        world_id,
        include_restricted=context.is_platform_admin,
    )


@router.post(
    "/workflow-templates",
    response_model=WorkflowTemplateRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_workflow_template(
    world_id: uuid.UUID,
    request: WorkflowTemplateCreate,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorkflowTemplateRead:
    _require_route_world(world_id, request.world_id)
    _reject_restricted_visibility(request.visibility.value, context)
    try:
        return VisualGenerationService(db_session).create_workflow_template(request)
    except VisualGenerationValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/workflow-templates/{template_id}", response_model=WorkflowTemplateRead)
def get_workflow_template(
    world_id: uuid.UUID,
    template_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorkflowTemplateRead:
    try:
        return VisualGenerationService(db_session).get_workflow_template(
            world_id,
            template_id,
            include_restricted=context.is_platform_admin,
        )
    except VisualGenerationNotFoundError as exc:
        raise _not_found() from exc


@router.patch(
    "/workflow-templates/{template_id}",
    response_model=WorkflowTemplateRead,
    dependencies=[Depends(require_csrf)],
)
def update_workflow_template(
    world_id: uuid.UUID,
    template_id: uuid.UUID,
    request: WorkflowTemplateUpdate,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorkflowTemplateRead:
    if request.visibility is not None:
        _reject_restricted_visibility(request.visibility.value, context)
    try:
        return VisualGenerationService(db_session).update_workflow_template(
            world_id,
            template_id,
            request,
        )
    except VisualGenerationNotFoundError as exc:
        raise _not_found() from exc
    except VisualGenerationValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.delete(
    "/workflow-templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_workflow_template(
    world_id: uuid.UUID,
    template_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        VisualGenerationService(db_session).delete_workflow_template(world_id, template_id)
    except VisualGenerationNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/workflow-templates/{template_id}/versions",
    response_model=WorkflowTemplateVersionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_workflow_template_version(
    world_id: uuid.UUID,
    template_id: uuid.UUID,
    request: WorkflowTemplateVersionCreate,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorkflowTemplateVersionRead:
    if request.template_id != template_id:
        raise _unprocessable("template_id must match route template_id")
    try:
        return VisualGenerationService(db_session).create_workflow_template_version(
            world_id,
            request,
        )
    except VisualGenerationNotFoundError as exc:
        raise _not_found() from exc
    except VisualGenerationValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.get(
    "/workflow-templates/{template_id}/versions",
    response_model=list[WorkflowTemplateVersionRead],
)
def list_workflow_template_versions(
    world_id: uuid.UUID,
    template_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[WorkflowTemplateVersionRead]:
    try:
        return VisualGenerationService(db_session).list_workflow_template_versions(
            world_id,
            template_id,
        )
    except VisualGenerationNotFoundError as exc:
        raise _not_found() from exc


@router.get("/model-assets", response_model=list[VisualModelAssetRead])
def list_model_assets(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    provider_id: uuid.UUID | None = None,
    inventory_kind: Annotated[VisualModelInventoryKind | None, Query()] = None,
) -> list[VisualModelAssetRead]:
    return VisualGenerationService(db_session).list_model_assets(
        world_id,
        worldline_id=worldline_id,
        provider_id=provider_id,
        inventory_kind=inventory_kind,
        include_restricted=context.is_platform_admin,
    )


@router.post(
    "/model-assets",
    response_model=VisualModelAssetRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_model_asset(
    world_id: uuid.UUID,
    request: VisualModelAssetCreate,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VisualModelAssetRead:
    _require_route_world(world_id, request.world_id)
    _reject_restricted_visibility(request.visibility.value, context)
    try:
        return VisualGenerationService(db_session).create_model_asset(
            request,
            include_restricted=context.is_platform_admin,
        )
    except VisualGenerationValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/model-assets/{model_asset_id}", response_model=VisualModelAssetRead)
def get_model_asset(
    world_id: uuid.UUID,
    model_asset_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VisualModelAssetRead:
    try:
        return VisualGenerationService(db_session).get_model_asset(
            world_id,
            model_asset_id,
            include_restricted=context.is_platform_admin,
        )
    except VisualGenerationNotFoundError as exc:
        raise _not_found() from exc


@router.patch(
    "/model-assets/{model_asset_id}",
    response_model=VisualModelAssetRead,
    dependencies=[Depends(require_csrf)],
)
def update_model_asset(
    world_id: uuid.UUID,
    model_asset_id: uuid.UUID,
    request: VisualModelAssetUpdate,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VisualModelAssetRead:
    if request.visibility is not None:
        _reject_restricted_visibility(request.visibility.value, context)
    try:
        return VisualGenerationService(db_session).update_model_asset(
            world_id,
            model_asset_id,
            request,
            include_restricted=context.is_platform_admin,
        )
    except VisualGenerationNotFoundError as exc:
        raise _not_found() from exc
    except VisualGenerationValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.delete(
    "/model-assets/{model_asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_model_asset(
    world_id: uuid.UUID,
    model_asset_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        VisualGenerationService(db_session).delete_model_asset(world_id, model_asset_id)
    except VisualGenerationNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/character-profiles", response_model=list[CharacterVisualGenerationProfileRead])
def list_character_profiles(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID,
    agent_id: uuid.UUID | None = None,
) -> list[CharacterVisualGenerationProfileRead]:
    try:
        return VisualGenerationService(db_session).list_character_profiles(
            world_id,
            worldline_id=worldline_id,
            agent_id=agent_id,
            include_restricted=context.is_platform_admin,
        )
    except VisualGenerationValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/character-profiles",
    response_model=CharacterVisualGenerationProfileRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_character_profile(
    world_id: uuid.UUID,
    request: CharacterVisualGenerationProfileCreate,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> CharacterVisualGenerationProfileRead:
    _require_route_world(world_id, request.world_id)
    _reject_restricted_visibility(request.visibility.value, context)
    try:
        return VisualGenerationService(db_session).create_character_profile(
            request,
            include_restricted=context.is_platform_admin,
        )
    except VisualGenerationValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.get(
    "/character-profiles/{profile_id}",
    response_model=CharacterVisualGenerationProfileRead,
)
def get_character_profile(
    world_id: uuid.UUID,
    profile_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> CharacterVisualGenerationProfileRead:
    try:
        return VisualGenerationService(db_session).get_character_profile(
            world_id,
            profile_id,
            include_restricted=context.is_platform_admin,
        )
    except VisualGenerationNotFoundError as exc:
        raise _not_found() from exc


@router.patch(
    "/character-profiles/{profile_id}",
    response_model=CharacterVisualGenerationProfileRead,
    dependencies=[Depends(require_csrf)],
)
def update_character_profile(
    world_id: uuid.UUID,
    profile_id: uuid.UUID,
    request: CharacterVisualGenerationProfileUpdate,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> CharacterVisualGenerationProfileRead:
    if request.visibility is not None:
        _reject_restricted_visibility(request.visibility.value, context)
    try:
        return VisualGenerationService(db_session).update_character_profile(
            world_id,
            profile_id,
            request,
            include_restricted=context.is_platform_admin,
        )
    except VisualGenerationNotFoundError as exc:
        raise _not_found() from exc
    except VisualGenerationValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.delete(
    "/character-profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_character_profile(
    world_id: uuid.UUID,
    profile_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        VisualGenerationService(db_session).delete_character_profile(world_id, profile_id)
    except VisualGenerationNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/plans",
    response_model=VisualGenerationPlanRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_plan(
    world_id: uuid.UUID,
    request: VisualGenerationPlanCreate,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VisualGenerationPlanRead:
    _require_route_world(world_id, request.world_id)
    try:
        return VisualGenerationService(db_session).create_plan(
            request,
            include_restricted=context.is_platform_admin,
        )
    except VisualGenerationValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/plans", response_model=list[VisualGenerationPlanRead])
def list_plans(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    plan_status: Annotated[VisualGenerationPlanStatus | None, Query(alias="status")] = None,
) -> list[VisualGenerationPlanRead]:
    try:
        return VisualGenerationService(db_session).list_plans(
            world_id,
            worldline_id=worldline_id,
            status=plan_status,
        )
    except VisualGenerationValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/plans/{plan_id}", response_model=VisualGenerationPlanRead)
def get_plan(
    world_id: uuid.UUID,
    plan_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VisualGenerationPlanRead:
    try:
        return VisualGenerationService(db_session).get_plan(world_id, plan_id)
    except VisualGenerationNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/plans/{plan_id}/validate",
    response_model=VisualGenerationPlanValidationResult,
    dependencies=[Depends(require_csrf)],
)
def validate_plan(
    world_id: uuid.UUID,
    plan_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VisualGenerationPlanValidationResult:
    try:
        return VisualGenerationService(db_session).validate_plan(
            world_id,
            plan_id,
            include_restricted=context.is_platform_admin,
        )
    except VisualGenerationNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/plans/{plan_id}/dry-run",
    response_model=VisualGenerationDryRunResult,
    dependencies=[Depends(require_csrf)],
)
def dry_run_plan(
    world_id: uuid.UUID,
    plan_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VisualGenerationDryRunResult:
    try:
        return VisualGenerationService(db_session).dry_run_plan(
            world_id,
            plan_id,
            include_restricted=context.is_platform_admin,
        )
    except VisualGenerationNotFoundError as exc:
        raise _not_found() from exc


def _require_route_world(route_world_id: uuid.UUID, body_world_id: uuid.UUID) -> None:
    if route_world_id != body_world_id:
        raise _unprocessable("body world_id must match route world_id")


def _reject_restricted_visibility(value: str, context: WorldAccessContext) -> None:
    if value in {"developer_only", "hidden"} and not context.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="restricted visibility requires platform admin",
        )


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
