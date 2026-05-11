from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from noveland.invocations.contracts import (
    CONTAINS_TEXT_MAX_LENGTH,
    InvocationActorKind,
    InvocationKind,
    InvocationProviderKind,
    InvocationRecordCreate,
    InvocationRecordView,
    InvocationRedactionStatus,
    InvocationRedactRequest,
    InvocationRetentionPolicy,
    InvocationSearchFilters,
    InvocationSearchResult,
    InvocationStatus,
    InvocationStatusUpdate,
    InvocationTagCreate,
    InvocationTagRecord,
    InvocationVisibility,
    PromptSnapshotCreate,
    PromptSnapshotRecord,
    PromptTemplateCreate,
    PromptTemplateRecord,
    PromptTemplateScopeKind,
    PromptTemplateStatus,
    PromptTemplateUpdate,
    RedactionMode,
    SortOrder,
)
from noveland.invocations.search import parse_tag_filters
from noveland.invocations.service import (
    InvocationLedgerService,
    InvocationNotFoundError,
    InvocationValidationError,
    PromptSnapshotService,
)
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_db_session,
    get_world_admin_context,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}", tags=["model-invocations"])


class PromptSnapshotCreateRequest(BaseModel):
    template_id: uuid.UUID | None = None
    template_key: str | None = Field(default=None, min_length=1, max_length=120)
    template_version: int | None = Field(default=None, ge=1)
    raw_prompt_text: str | None = None
    raw_messages_json: list[dict[str, Any]] | None = None
    raw_request_json: dict[str, Any] | None = None
    raw_response_json: dict[str, Any] | None = None
    raw_output_text: str | None = None
    normalized_output_json: dict[str, Any] | None = None
    prompt_context_snapshot_json: dict[str, Any] | None = None
    tool_definitions_json: dict[str, Any] | None = None
    context_pack_refs_json: dict[str, Any] | None = None
    input_asset_refs_json: list[dict[str, Any]] | None = None
    visibility: InvocationVisibility = InvocationVisibility.WORLD_ADMIN
    redaction_status: InvocationRedactionStatus = InvocationRedactionStatus.RAW
    contains_sensitive_context: bool = False


class InvocationCreateRequest(BaseModel):
    worldline_id: uuid.UUID | None = None
    trace_id: uuid.UUID | None = None
    parent_invocation_id: uuid.UUID | None = None
    invocation_kind: InvocationKind
    actor_kind: InvocationActorKind
    actor_ref: str | None = Field(default=None, min_length=1, max_length=160)
    agent_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    turn_id: uuid.UUID | None = None
    world_event_id: uuid.UUID | None = None
    media_job_id: uuid.UUID | None = None
    media_asset_id: uuid.UUID | None = None
    memory_write_job_id: uuid.UUID | None = None
    provider_kind: InvocationProviderKind
    provider_profile_id: uuid.UUID | None = None
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    model_version: str | None = Field(default=None, min_length=1, max_length=80)
    prompt_template_key: str | None = Field(default=None, min_length=1, max_length=120)
    prompt_template_version: int | None = Field(default=None, ge=1)
    input_text: str | None = None
    output_text: str | None = None
    input_json: dict[str, Any] | None = None
    output_json: dict[str, Any] | None = None
    request_params_json: dict[str, Any] | None = None
    response_metadata_json: dict[str, Any] | None = None
    usage_json: dict[str, Any] | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    estimated_cost: Decimal | None = Field(default=None, ge=Decimal("0"))
    status: InvocationStatus = InvocationStatus.PENDING
    error_text: str | None = None
    visibility: InvocationVisibility = InvocationVisibility.WORLD_ADMIN
    redaction_status: InvocationRedactionStatus = InvocationRedactionStatus.RAW
    retention_policy: InvocationRetentionPolicy = InvocationRetentionPolicy.LOCAL_DEBUG
    contains_sensitive_context: bool = False
    purge_after: datetime | None = None
    prompt_snapshot: PromptSnapshotCreateRequest | None = None


class InvocationStatusUpdateRequest(BaseModel):
    status: InvocationStatus
    output_text: str | None = None
    output_json: dict[str, Any] | None = None
    response_metadata_json: dict[str, Any] | None = None
    usage_json: dict[str, Any] | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    estimated_cost: Decimal | None = Field(default=None, ge=Decimal("0"))
    error_text: str | None = None


class InvocationRedactRequestBody(BaseModel):
    redaction_status: InvocationRedactionStatus
    reason: str = Field(min_length=1, max_length=200)
    mode: RedactionMode


class InvocationTagCreateRequest(BaseModel):
    worldline_id: uuid.UUID | None = None
    tag_type: str = Field(min_length=1, max_length=40)
    tag_key: str = Field(min_length=1, max_length=80)
    tag_value: str = Field(min_length=1, max_length=220)


class PromptTemplateCreateRequest(BaseModel):
    scope_kind: PromptTemplateScopeKind
    template_key: str = Field(min_length=1, max_length=120)
    version: int = Field(ge=1)
    invocation_kind: InvocationKind
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    input_schema_json: dict[str, Any] | None = None
    output_schema_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None
    status: PromptTemplateStatus = PromptTemplateStatus.DRAFT


class PromptTemplateUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    input_schema_json: dict[str, Any] | None = None
    output_schema_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None
    status: PromptTemplateStatus | None = None


@router.get("/model-invocations", response_model=InvocationSearchResult)
def list_model_invocations(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
    created_after: Annotated[datetime | None, Query()] = None,
    created_before: Annotated[datetime | None, Query()] = None,
    trace_id: Annotated[uuid.UUID | None, Query()] = None,
    parent_invocation_id: Annotated[uuid.UUID | None, Query()] = None,
    agent_id: Annotated[uuid.UUID | None, Query()] = None,
    conversation_id: Annotated[uuid.UUID | None, Query()] = None,
    turn_id: Annotated[uuid.UUID | None, Query()] = None,
    world_event_id: Annotated[uuid.UUID | None, Query()] = None,
    media_job_id: Annotated[uuid.UUID | None, Query()] = None,
    media_asset_id: Annotated[uuid.UUID | None, Query()] = None,
    memory_write_job_id: Annotated[uuid.UUID | None, Query()] = None,
    invocation_kind: Annotated[InvocationKind | None, Query()] = None,
    provider_kind: Annotated[InvocationProviderKind | None, Query()] = None,
    model_name: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    status_filter: Annotated[InvocationStatus | None, Query(alias="status")] = None,
    visibility: Annotated[InvocationVisibility | None, Query()] = None,
    redaction_status: Annotated[InvocationRedactionStatus | None, Query()] = None,
    retention_policy: Annotated[InvocationRetentionPolicy | None, Query()] = None,
    contains_sensitive_context: Annotated[bool | None, Query()] = None,
    contains_text: Annotated[str | None, Query(max_length=CONTAINS_TEXT_MAX_LENGTH)] = None,
    tag: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[datetime | None, Query()] = None,
    order: Annotated[SortOrder, Query()] = SortOrder.DESC,
    include_hidden: Annotated[bool, Query()] = False,
) -> InvocationSearchResult:
    try:
        tags = tuple(parse_tag_filters([] if tag is None else tag))
        return InvocationLedgerService(db_session).list(
            world_id,
            InvocationSearchFilters(
                worldline_id=worldline_id,
                created_after=created_after,
                created_before=created_before,
                trace_id=trace_id,
                parent_invocation_id=parent_invocation_id,
                agent_id=agent_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                world_event_id=world_event_id,
                media_job_id=media_job_id,
                media_asset_id=media_asset_id,
                memory_write_job_id=memory_write_job_id,
                invocation_kind=invocation_kind,
                provider_kind=provider_kind,
                model_name=model_name,
                status=status_filter,
                visibility=visibility,
                redaction_status=redaction_status,
                retention_policy=retention_policy,
                contains_sensitive_context=contains_sensitive_context,
                contains_text=contains_text,
                tags=tags,
                limit=limit,
                cursor=cursor,
                order=order,
            ),
            include_hidden=include_hidden,
            platform_admin=context.is_platform_admin,
        )
    except (InvocationValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/model-invocations",
    response_model=InvocationRecordView,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_model_invocation(
    world_id: uuid.UUID,
    request: InvocationCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> InvocationRecordView:
    try:
        return InvocationLedgerService(db_session).record(_invocation_create(world_id, request))
    except InvocationValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/model-invocations/{invocation_id}", response_model=InvocationRecordView)
def get_model_invocation(
    world_id: uuid.UUID,
    invocation_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    include_hidden: Annotated[bool, Query()] = False,
) -> InvocationRecordView:
    record = InvocationLedgerService(db_session).get(
        world_id,
        invocation_id,
        include_hidden=include_hidden,
        platform_admin=context.is_platform_admin,
    )
    if record is None:
        raise _not_found()
    return record


@router.patch(
    "/model-invocations/{invocation_id}/status",
    response_model=InvocationRecordView,
    dependencies=[Depends(require_csrf)],
)
def update_model_invocation_status(
    world_id: uuid.UUID,
    invocation_id: uuid.UUID,
    request: InvocationStatusUpdateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> InvocationRecordView:
    try:
        return InvocationLedgerService(db_session).update_status(
            world_id,
            invocation_id,
            InvocationStatusUpdate(**request.model_dump()),
        )
    except InvocationNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/model-invocations/{invocation_id}/redact",
    response_model=InvocationRecordView,
    dependencies=[Depends(require_csrf)],
)
def redact_model_invocation(
    world_id: uuid.UUID,
    invocation_id: uuid.UUID,
    request: InvocationRedactRequestBody,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> InvocationRecordView:
    try:
        return InvocationLedgerService(db_session).redact(
            world_id,
            invocation_id,
            InvocationRedactRequest(**request.model_dump()),
        )
    except InvocationNotFoundError as exc:
        raise _not_found() from exc


@router.get("/model-invocations/{invocation_id}/tags", response_model=list[InvocationTagRecord])
def list_model_invocation_tags(
    world_id: uuid.UUID,
    invocation_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[InvocationTagRecord]:
    try:
        return InvocationLedgerService(db_session).list_tags(world_id, invocation_id)
    except InvocationNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/model-invocations/{invocation_id}/tags",
    response_model=InvocationTagRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_model_invocation_tag(
    world_id: uuid.UUID,
    invocation_id: uuid.UUID,
    request: InvocationTagCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> InvocationTagRecord:
    try:
        return InvocationLedgerService(db_session).attach_tag(
            InvocationTagCreate(
                world_id=world_id,
                worldline_id=request.worldline_id,
                invocation_id=invocation_id,
                tag_type=request.tag_type,
                tag_key=request.tag_key,
                tag_value=request.tag_value,
            )
        )
    except (InvocationNotFoundError, InvocationValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.delete(
    "/model-invocations/{invocation_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_model_invocation_tag(
    world_id: uuid.UUID,
    invocation_id: uuid.UUID,
    tag_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        InvocationLedgerService(db_session).delete_tag(world_id, invocation_id, tag_id)
    except InvocationNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/model-invocations/{invocation_id}/prompt-snapshot",
    response_model=PromptSnapshotRecord,
)
def get_model_invocation_prompt_snapshot(
    world_id: uuid.UUID,
    invocation_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PromptSnapshotRecord:
    record = PromptSnapshotService(db_session).get_snapshot(
        world_id,
        invocation_id,
        platform_admin=context.is_platform_admin,
    )
    if record is None:
        raise _not_found()
    return record


@router.get("/prompt-templates", response_model=list[PromptTemplateRecord])
def list_prompt_templates(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    scope_kind: Annotated[PromptTemplateScopeKind | None, Query()] = None,
    template_key: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    status_filter: Annotated[PromptTemplateStatus | None, Query(alias="status")] = None,
    include_global: Annotated[bool, Query()] = True,
) -> list[PromptTemplateRecord]:
    return PromptSnapshotService(db_session).list_templates(
        world_id,
        scope_kind=scope_kind,
        template_key=template_key,
        status=status_filter,
        include_global=include_global,
    )


@router.post(
    "/prompt-templates",
    response_model=PromptTemplateRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_prompt_template(
    world_id: uuid.UUID,
    request: PromptTemplateCreateRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PromptTemplateRecord:
    if request.scope_kind == PromptTemplateScopeKind.GLOBAL and not context.is_platform_admin:
        raise _forbidden()
    try:
        return PromptSnapshotService(db_session).create_template(
            PromptTemplateCreate(
                world_id=None if request.scope_kind == PromptTemplateScopeKind.GLOBAL else world_id,
                **request.model_dump(),
            )
        )
    except (InvocationValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/prompt-templates/{template_id}", response_model=PromptTemplateRecord)
def get_prompt_template(
    world_id: uuid.UUID,
    template_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PromptTemplateRecord:
    record = PromptSnapshotService(db_session).get_template(
        world_id,
        template_id,
        platform_admin=context.is_platform_admin,
    )
    if record is None:
        raise _not_found()
    return record


@router.patch(
    "/prompt-templates/{template_id}",
    response_model=PromptTemplateRecord,
    dependencies=[Depends(require_csrf)],
)
def update_prompt_template(
    world_id: uuid.UUID,
    template_id: uuid.UUID,
    request: PromptTemplateUpdateRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PromptTemplateRecord:
    try:
        return PromptSnapshotService(db_session).update_template(
            world_id,
            template_id,
            PromptTemplateUpdate(**request.model_dump(exclude_unset=True)),
            platform_admin=context.is_platform_admin,
        )
    except InvocationNotFoundError as exc:
        raise _not_found() from exc


def _invocation_create(
    world_id: uuid.UUID,
    request: InvocationCreateRequest,
) -> InvocationRecordCreate:
    snapshot = (
        None
        if request.prompt_snapshot is None
        else PromptSnapshotCreate(**request.prompt_snapshot.model_dump())
    )
    return InvocationRecordCreate(
        world_id=world_id,
        prompt_snapshot=snapshot,
        **request.model_dump(exclude={"prompt_snapshot"}),
    )


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
