from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from noveland.auth import AuthenticatedSubject
from noveland.core.settings import load_settings
from noveland.invocations.contracts import InvocationRecordView
from noveland.media.storage import LocalMediaObjectStorage
from noveland.providers.budget import ProviderBudgetService
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderBudgetPolicyCreate,
    ProviderBudgetPolicyRead,
    ProviderBudgetPolicyStatus,
    ProviderBudgetPolicyUpdate,
    ProviderCapabilityCreate,
    ProviderCapabilityRead,
    ProviderExecutionRequest,
    ProviderExecutionResult,
    ProviderHealthCheckRead,
    ProviderHealthStatus,
    ProviderIntegrationCreate,
    ProviderIntegrationListFilters,
    ProviderIntegrationRead,
    ProviderIntegrationStatus,
    ProviderIntegrationUpdate,
    ProviderKind,
    ProviderModelDiscoveryRead,
    ProviderModelDiscoveryRequest,
    ProviderQuotaStatusRead,
    ProviderScopeKind,
    ProviderSmokeTestResult,
    ProviderTemplateRead,
    ProviderTestInvocationRequest,
    ProviderTestInvocationResult,
    ProviderVisibility,
)
from noveland.providers.health import ProviderHealthService
from noveland.providers.model_discovery import ProviderModelDiscoveryService
from noveland.providers.registry import (
    ProviderNotFoundError,
    ProviderRegistryService,
    ProviderValidationError,
)
from noveland.providers.secrets import reject_sensitive_config
from noveland.providers.service import ProviderExecutionError, ProviderExecutionService
from noveland.providers.templates import provider_templates
from noveland.services.api.authorization import is_platform_admin
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_current_subject,
    get_db_session,
    get_world_admin_context,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/providers", tags=["providers"])


def _media_storage() -> LocalMediaObjectStorage:
    return LocalMediaObjectStorage(load_settings().object_storage_root / "media")


class ProviderCapabilityCreateRequest(BaseModel):
    capability_key: str = Field(min_length=1, max_length=120)
    capability_json: dict[str, Any] = Field(default_factory=dict)


class ProviderIntegrationCreateRequest(BaseModel):
    scope_kind: ProviderScopeKind = ProviderScopeKind.WORLD
    provider_kind: ProviderKind
    adapter_kind: ProviderAdapterKind
    provider_key: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=200)
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    auth_ref: str | None = Field(default=None, min_length=1, max_length=200)
    config_json: dict[str, Any] = Field(default_factory=dict)
    default_params_json: dict[str, Any] = Field(default_factory=dict)
    status: ProviderIntegrationStatus = ProviderIntegrationStatus.ACTIVE
    visibility: ProviderVisibility = ProviderVisibility.WORLD_ADMIN
    capabilities: list[ProviderCapabilityCreateRequest] = Field(default_factory=list)


class ProviderIntegrationUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    auth_ref: str | None = Field(default=None, min_length=1, max_length=200)
    config_json: dict[str, Any] | None = None
    default_params_json: dict[str, Any] | None = None
    status: ProviderIntegrationStatus | None = None
    visibility: ProviderVisibility | None = None
    capabilities: list[ProviderCapabilityCreateRequest] | None = None


class ProviderSmokeTestRequestBody(BaseModel):
    worldline_id: uuid.UUID | None = None
    capability_key: str | None = Field(default=None, min_length=1, max_length=120)
    input_text: str | None = None
    input_json: dict[str, Any] = Field(default_factory=dict)
    request_json: dict[str, Any] = Field(default_factory=dict)
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    media_job_id: uuid.UUID | None = None
    media_asset_id: uuid.UUID | None = None
    player_actor_id: uuid.UUID | None = None


class ProviderBudgetPolicyCreateRequest(BaseModel):
    provider_id: uuid.UUID | None = None
    policy_key: str = Field(min_length=1, max_length=120)
    status: ProviderBudgetPolicyStatus = ProviderBudgetPolicyStatus.ACTIVE
    emergency_stop_enabled: bool = False
    limits_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ProviderBudgetPolicyUpdateRequest(BaseModel):
    status: ProviderBudgetPolicyStatus | None = None
    emergency_stop_enabled: bool | None = None
    limits_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None


@router.get("/templates", response_model=list[ProviderTemplateRead])
def list_provider_templates(
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
) -> list[ProviderTemplateRead]:
    return provider_templates()


class ProviderModelDiscoveryRequestBody(BaseModel):
    provider_id: uuid.UUID | None = None
    provider_kind: ProviderKind | None = None
    adapter_kind: ProviderAdapterKind | None = None
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    auth_ref: str | None = Field(default=None, min_length=1, max_length=200)
    config_json: dict[str, Any] = Field(default_factory=dict)
    default_params_json: dict[str, Any] = Field(default_factory=dict)


@router.post(
    "/model-discovery",
    response_model=ProviderModelDiscoveryRead,
    dependencies=[Depends(require_csrf)],
)
def discover_provider_models(
    world_id: uuid.UUID,
    request: ProviderModelDiscoveryRequestBody,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ProviderModelDiscoveryRead:
    try:
        reject_sensitive_config(request.config_json, field_name="config_json")
        reject_sensitive_config(request.default_params_json, field_name="default_params_json")
        return ProviderModelDiscoveryService(db_session).discover(
            world_id,
            ProviderModelDiscoveryRequest(**request.model_dump()),
            platform_admin=context.is_platform_admin,
        )
    except (ProviderNotFoundError, ProviderValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("", response_model=list[ProviderIntegrationRead])
def list_providers(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    scope_kind: Annotated[ProviderScopeKind | None, Query()] = None,
    provider_kind: Annotated[ProviderKind | None, Query()] = None,
    adapter_kind: Annotated[ProviderAdapterKind | None, Query()] = None,
    status_filter: Annotated[ProviderIntegrationStatus | None, Query(alias="status")] = None,
    visibility: Annotated[ProviderVisibility | None, Query()] = None,
    capability_key: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    include_global: Annotated[bool, Query()] = True,
    include_hidden: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[ProviderIntegrationRead]:
    return ProviderRegistryService(db_session).list_providers(
        world_id,
        ProviderIntegrationListFilters(
            scope_kind=scope_kind,
            provider_kind=provider_kind,
            adapter_kind=adapter_kind,
            status=status_filter,
            visibility=visibility,
            capability_key=capability_key,
            include_global=include_global,
            include_hidden=include_hidden,
            limit=limit,
        ),
        platform_admin=context.is_platform_admin,
    )


@router.post(
    "",
    response_model=ProviderIntegrationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_provider(
    world_id: uuid.UUID,
    request: ProviderIntegrationCreateRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ProviderIntegrationRead:
    if request.scope_kind == ProviderScopeKind.GLOBAL and not context.is_platform_admin:
        raise _forbidden()
    if _restricted_visibility(request.visibility) and not context.is_platform_admin:
        raise _forbidden()
    try:
        return ProviderRegistryService(db_session).create_provider(
            ProviderIntegrationCreate(
                world_id=None if request.scope_kind == ProviderScopeKind.GLOBAL else world_id,
                scope_kind=request.scope_kind,
                provider_kind=request.provider_kind,
                adapter_kind=request.adapter_kind,
                provider_key=request.provider_key,
                display_name=request.display_name,
                base_url=request.base_url,
                auth_ref=request.auth_ref,
                config_json=dict(request.config_json),
                default_params_json=dict(request.default_params_json),
                status=request.status,
                visibility=request.visibility,
                capabilities=tuple(_capability_create(item) for item in request.capabilities),
            )
        )
    except (ProviderValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/budget-policies", response_model=list[ProviderBudgetPolicyRead])
def list_provider_budget_policies(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    provider_id: Annotated[uuid.UUID | None, Query()] = None,
    include_inactive: Annotated[bool, Query()] = False,
) -> list[ProviderBudgetPolicyRead]:
    return ProviderBudgetService(db_session).list_policies(
        world_id,
        provider_id=provider_id,
        include_inactive=include_inactive,
    )


@router.post(
    "/budget-policies",
    response_model=ProviderBudgetPolicyRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_provider_budget_policy(
    world_id: uuid.UUID,
    request: ProviderBudgetPolicyCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ProviderBudgetPolicyRead:
    try:
        return ProviderBudgetService(db_session).create_policy(
            ProviderBudgetPolicyCreate(
                world_id=world_id,
                provider_id=request.provider_id,
                policy_key=request.policy_key,
                status=request.status,
                emergency_stop_enabled=request.emergency_stop_enabled,
                limits_json=dict(request.limits_json),
                metadata_json=dict(request.metadata_json),
            )
        )
    except (ProviderNotFoundError, ProviderValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.patch(
    "/budget-policies/{policy_id}",
    response_model=ProviderBudgetPolicyRead,
    dependencies=[Depends(require_csrf)],
)
def update_provider_budget_policy(
    world_id: uuid.UUID,
    policy_id: uuid.UUID,
    request: ProviderBudgetPolicyUpdateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ProviderBudgetPolicyRead:
    try:
        return ProviderBudgetService(db_session).update_policy(
            world_id,
            policy_id,
            ProviderBudgetPolicyUpdate(
                status=request.status,
                emergency_stop_enabled=request.emergency_stop_enabled,
                limits_json=None if request.limits_json is None else dict(request.limits_json),
                metadata_json=(
                    None if request.metadata_json is None else dict(request.metadata_json)
                ),
            ),
        )
    except ProviderNotFoundError as exc:
        raise _not_found() from exc
    except (ProviderValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/quota-status", response_model=ProviderQuotaStatusRead)
def get_provider_quota_status(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    provider_id: Annotated[uuid.UUID | None, Query()] = None,
    player_actor_id: Annotated[uuid.UUID | None, Query()] = None,
    capability_key: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
) -> ProviderQuotaStatusRead:
    return ProviderBudgetService(db_session).quota_status(
        world_id,
        provider_id=provider_id,
        player_actor_id=player_actor_id,
        capability_key=capability_key,
    )


@router.get("/{provider_id}", response_model=ProviderIntegrationRead)
def get_provider(
    world_id: uuid.UUID,
    provider_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    include_hidden: Annotated[bool, Query()] = False,
) -> ProviderIntegrationRead:
    record = ProviderRegistryService(db_session).get_provider(
        world_id,
        provider_id,
        include_hidden=include_hidden,
        platform_admin=context.is_platform_admin,
    )
    if record is None:
        raise _not_found()
    return record


@router.patch(
    "/{provider_id}",
    response_model=ProviderIntegrationRead,
    dependencies=[Depends(require_csrf)],
)
def update_provider(
    world_id: uuid.UUID,
    provider_id: uuid.UUID,
    request: ProviderIntegrationUpdateRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ProviderIntegrationRead:
    if (
        request.visibility is not None
        and _restricted_visibility(request.visibility)
        and not context.is_platform_admin
    ):
        raise _forbidden()
    try:
        return ProviderRegistryService(db_session).update_provider(
            world_id,
            provider_id,
            ProviderIntegrationUpdate(
                display_name=request.display_name,
                base_url=request.base_url,
                auth_ref=request.auth_ref,
                config_json=None if request.config_json is None else dict(request.config_json),
                default_params_json=(
                    None
                    if request.default_params_json is None
                    else dict(request.default_params_json)
                ),
                status=request.status,
                visibility=request.visibility,
                capabilities=(
                    None
                    if request.capabilities is None
                    else tuple(_capability_create(item) for item in request.capabilities)
                ),
            ),
            platform_admin=context.is_platform_admin,
        )
    except ProviderNotFoundError as exc:
        raise _not_found() from exc
    except (ProviderValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.delete(
    "/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_provider(
    world_id: uuid.UUID,
    provider_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        ProviderRegistryService(db_session).delete_provider(
            world_id,
            provider_id,
            platform_admin=context.is_platform_admin,
        )
    except ProviderNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{provider_id}/capabilities", response_model=list[ProviderCapabilityRead])
def list_provider_capabilities(
    world_id: uuid.UUID,
    provider_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[ProviderCapabilityRead]:
    try:
        return ProviderRegistryService(db_session).list_capabilities(
            world_id,
            provider_id,
            platform_admin=context.is_platform_admin,
        )
    except ProviderNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/{provider_id}/health-check",
    response_model=ProviderHealthCheckRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def run_provider_health_check(
    world_id: uuid.UUID,
    provider_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ProviderHealthCheckRead:
    try:
        return ProviderHealthService(db_session).run_health_check(
            world_id,
            provider_id,
            platform_admin=context.is_platform_admin,
        )
    except ProviderNotFoundError as exc:
        raise _not_found() from exc


@router.get("/{provider_id}/health-checks", response_model=list[ProviderHealthCheckRead])
def list_provider_health_checks(
    world_id: uuid.UUID,
    provider_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[ProviderHealthCheckRead]:
    try:
        return ProviderHealthService(db_session).list_health_checks(
            world_id,
            provider_id,
            platform_admin=context.is_platform_admin,
            limit=limit,
        )
    except ProviderNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/{provider_id}/smoke-test",
    response_model=ProviderSmokeTestResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def run_provider_smoke_test(
    world_id: uuid.UUID,
    provider_id: uuid.UUID,
    request: ProviderSmokeTestRequestBody,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ProviderSmokeTestResult:
    try:
        reject_sensitive_config(request.input_json, field_name="input_json")
        reject_sensitive_config(request.request_json, field_name="request_json")
        provider = ProviderRegistryService(db_session).get_provider(
            world_id,
            provider_id,
            platform_admin=True,
            include_hidden=True,
        )
        if provider is None:
            raise ProviderNotFoundError("provider integration not found")
        result = ProviderExecutionService(db_session, _media_storage()).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=request.worldline_id,
                provider_id=provider_id,
                provider_kind=provider.provider_kind,
                capability_key=request.capability_key,
                input_text=request.input_text,
                input_json=dict(request.input_json),
                request_json=dict(request.request_json),
                model_name=request.model_name,
                media_job_id=request.media_job_id,
                media_asset_id=request.media_asset_id,
                player_actor_id=request.player_actor_id,
                actor_ref=(
                    "platform_admin"
                    if is_platform_admin(subject)
                    else f"world_admin:{subject.user_id}"
                ),
            )
        )
        ProviderHealthService(db_session).record_health_check(
            provider_id,
            status=ProviderHealthStatus.HEALTHY,
            latency_ms=result.invocation.latency_ms,
            metadata_json={"smoke_test": True, "status": "succeeded"},
        )
    except ProviderNotFoundError as exc:
        raise _not_found() from exc
    except (ProviderValidationError, ProviderExecutionError, ValueError) as exc:
        ProviderHealthService(db_session).record_health_check(
            provider_id,
            status=ProviderHealthStatus.UNHEALTHY,
            error_text=str(exc),
            metadata_json={"smoke_test": True, "status": "failed"},
        )
        failed_invocation = _latest_failed_invocation(db_session, world_id, provider_id)
        if failed_invocation is None:
            raise _unprocessable(str(exc)) from exc
        result = ProviderExecutionResult(
            provider=failed_invocation.provider,
            invocation=failed_invocation.invocation,
            output_text=None,
            output_json={"error": "provider smoke test failed"},
            media_job=None,
            output_asset=None,
            output_objects=[],
        )
        return ProviderSmokeTestResult(**result.model_dump(), smoke_status="failed")
    return ProviderSmokeTestResult(**result.model_dump(), smoke_status="succeeded")


@router.post(
    "/test-invocation",
    response_model=ProviderTestInvocationResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def run_provider_test_invocation(
    world_id: uuid.UUID,
    request: ProviderTestInvocationRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ProviderTestInvocationResult:
    try:
        reject_sensitive_config(request.input_json, field_name="input_json")
        reject_sensitive_config(request.request_json, field_name="request_json")
        result = ProviderExecutionService(db_session, _media_storage()).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=request.worldline_id,
                provider_id=request.provider_id,
                provider_kind=request.provider_kind,
                capability_key=request.capability_key,
                input_text=request.input_text,
                input_json=dict(request.input_json),
                request_json=dict(request.request_json),
                model_name=request.model_name,
                media_job_id=request.media_job_id,
                media_asset_id=request.media_asset_id,
                player_actor_id=request.player_actor_id,
                actor_ref=(
                    "platform_admin"
                    if is_platform_admin(subject)
                    else f"world_admin:{subject.user_id}"
                ),
            )
        )
    except ProviderNotFoundError as exc:
        raise _not_found() from exc
    except (ProviderValidationError, ProviderExecutionError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc
    return ProviderTestInvocationResult(**result.model_dump())


def _capability_create(request: ProviderCapabilityCreateRequest) -> ProviderCapabilityCreate:
    return ProviderCapabilityCreate(
        capability_key=request.capability_key,
        capability_json=dict(request.capability_json),
    )


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


def _restricted_visibility(visibility: ProviderVisibility) -> bool:
    return visibility in {ProviderVisibility.DEVELOPER_ONLY, ProviderVisibility.HIDDEN}


@dataclass(frozen=True, slots=True)
class _FailedInvocationBundle:
    provider: ProviderIntegrationRead
    invocation: InvocationRecordView


def _latest_failed_invocation(
    db_session: Session,
    world_id: uuid.UUID,
    provider_id: uuid.UUID,
) -> _FailedInvocationBundle | None:
    from noveland.invocations.models import ModelInvocation
    from noveland.invocations.service import InvocationLedgerService
    from sqlalchemy import select

    candidates = db_session.scalars(
        select(ModelInvocation)
        .where(ModelInvocation.world_id == world_id, ModelInvocation.status == "failed")
        .order_by(ModelInvocation.created_at.desc())
        .limit(10)
    ).all()
    model = next(
        (
            item
            for item in candidates
            if isinstance(item.request_params_json, dict)
            and item.request_params_json.get("provider_id") == str(provider_id)
        ),
        None,
    )
    if model is None:
        return None
    provider = None
    if isinstance(model.request_params_json, dict) and model.request_params_json.get(
        "provider_id"
    ):
        provider = ProviderRegistryService(db_session).get_provider(
            world_id,
            uuid.UUID(str(model.request_params_json.get("provider_id"))),
            platform_admin=True,
            include_hidden=True,
        )
    if provider is None:
        return None
    invocation = InvocationLedgerService(db_session).get(world_id, model.id, platform_admin=True)
    if invocation is None:
        return None
    return _FailedInvocationBundle(provider=provider, invocation=invocation)
