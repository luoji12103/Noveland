from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from noveland.adapters import (
    ProviderInvocationResult,
    ProviderProfileCreate,
    ProviderProfileRecord,
    ProviderProfileService,
    ProviderProfileUpdate,
    ProviderType,
)
from noveland.adapters.models import ProviderProfile
from noveland.auth import AuthenticatedSubject
from noveland.core.settings import load_settings
from noveland.observability import (
    DiagnosticComponent,
    DiagnosticSeverity,
    RuntimeDiagnosticCreate,
    RuntimeDiagnosticRecord,
    RuntimeDiagnosticsService,
)
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import get_db_session, get_platform_admin_subject
from noveland.services.runtime.daemon import get_runtime_control_view, set_runtime_desired_state
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="", tags=["runtime"])


class RuntimeControlResponse(BaseModel):
    desired_state: Literal["running", "stopped"]
    last_heartbeat_at: datetime | None
    last_run_started_at: datetime | None
    last_run_finished_at: datetime | None
    last_error: str | None


class RuntimeStatusResponse(RuntimeControlResponse):
    runtime_loop_interval_seconds: int
    runtime_batch_limit: int


class RuntimeControlUpdateRequest(BaseModel):
    desired_state: Literal["running", "stopped"]


class ProviderProfileCreateRequest(BaseModel):
    profile_key: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$", max_length=80)
    name: str = Field(min_length=1, max_length=160)
    provider_type: ProviderType
    base_url: str = Field(min_length=1, max_length=500)
    model_name: str = Field(min_length=1, max_length=200)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    api_key_ref: str = Field(min_length=1, max_length=120)
    timeout_seconds: int = Field(default=20, ge=1, le=120)
    retry_attempts: int = Field(default=1, ge=0, le=5)
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=600)


class ProviderProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    capabilities: dict[str, Any] | None = None
    api_key_ref: str | None = Field(default=None, min_length=1, max_length=120)
    timeout_seconds: int | None = Field(default=None, ge=1, le=120)
    retry_attempts: int | None = Field(default=None, ge=0, le=5)
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=600)
    is_enabled: bool | None = None


class ProviderTestCallRequest(BaseModel):
    prompt: str = Field(default="Reply with OK.", min_length=1, max_length=1000)


class ProviderProfileResponse(BaseModel):
    id: uuid.UUID
    profile_key: str
    name: str
    provider_type: ProviderType
    base_url: str
    model_name: str
    capabilities: dict[str, Any]
    api_key_ref: str
    timeout_seconds: int
    retry_attempts: int
    rate_limit_per_minute: int | None
    last_tested_at: datetime | None
    last_test_status: str | None
    last_test_error: str | None
    is_enabled: bool


class ProviderTestCallResponse(BaseModel):
    status: str
    latency_ms: int
    text_preview: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class RuntimeDiagnosticResponse(BaseModel):
    id: uuid.UUID
    severity: DiagnosticSeverity
    component: DiagnosticComponent
    event_type: str
    message: str
    details: dict[str, Any]
    occurred_at: datetime
    world_id: uuid.UUID | None
    agent_id: uuid.UUID | None
    run_id: uuid.UUID | None
    provider_profile_id: uuid.UUID | None
    created_at: datetime


@router.get("/runtime/control", response_model=RuntimeControlResponse)
def get_runtime_control(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RuntimeControlResponse:
    del subject
    return _runtime_control_response(get_runtime_control_view(db_session))


@router.patch("/runtime/control", response_model=RuntimeControlResponse)
def update_runtime_control(
    control_update: RuntimeControlUpdateRequest,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RuntimeControlResponse:
    del subject
    require_csrf(request)
    return _runtime_control_response(
        set_runtime_desired_state(db_session, control_update.desired_state),
    )


@router.get("/runtime/status", response_model=RuntimeStatusResponse)
def get_runtime_status(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RuntimeStatusResponse:
    del subject
    settings = load_settings()
    view = get_runtime_control_view(db_session)
    return RuntimeStatusResponse(
        runtime_loop_interval_seconds=settings.runtime_loop_interval_seconds,
        runtime_batch_limit=settings.runtime_batch_limit,
        **_runtime_control_response(view).model_dump(),
    )


@router.get("/runtime/diagnostics", response_model=list[RuntimeDiagnosticResponse])
def list_runtime_diagnostics(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    severity: DiagnosticSeverity | None = None,
    component: DiagnosticComponent | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[RuntimeDiagnosticResponse]:
    del subject
    return [
        _diagnostic_response(record)
        for record in RuntimeDiagnosticsService(db_session).list(
            severity=severity,
            component=component,
            limit=limit,
        )
    ]


@router.get("/provider-profiles", response_model=list[ProviderProfileResponse])
def list_provider_profiles(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[ProviderProfileResponse]:
    del subject
    service = ProviderProfileService(db_session, load_settings())
    return [_provider_profile_response(profile) for profile in service.list_profiles()]


@router.post(
    "/provider-profiles",
    response_model=ProviderProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_provider_profile(
    profile_create: ProviderProfileCreateRequest,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ProviderProfileResponse:
    del subject
    require_csrf(request)
    profile = ProviderProfileService(db_session, load_settings()).create_profile(
        ProviderProfileCreate(
            profile_key=profile_create.profile_key,
            name=profile_create.name,
            provider_type=profile_create.provider_type,
            base_url=profile_create.base_url,
            model_name=profile_create.model_name,
            capabilities=profile_create.capabilities,
            api_key_ref=profile_create.api_key_ref,
            timeout_seconds=profile_create.timeout_seconds,
            retry_attempts=profile_create.retry_attempts,
            rate_limit_per_minute=profile_create.rate_limit_per_minute,
        ),
    )
    return _provider_profile_response(profile)


@router.patch("/provider-profiles/{profile_id}", response_model=ProviderProfileResponse)
def update_provider_profile(
    profile_id: uuid.UUID,
    profile_update: ProviderProfileUpdateRequest,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ProviderProfileResponse:
    del subject
    require_csrf(request)
    model = _provider_profile_or_404(db_session, profile_id)
    profile = ProviderProfileService(db_session, load_settings()).update_profile(
        model,
        ProviderProfileUpdate(
            name=profile_update.name,
            base_url=profile_update.base_url,
            model_name=profile_update.model_name,
            capabilities=profile_update.capabilities,
            api_key_ref=profile_update.api_key_ref,
            timeout_seconds=profile_update.timeout_seconds,
            retry_attempts=profile_update.retry_attempts,
            rate_limit_per_minute=profile_update.rate_limit_per_minute,
            is_enabled=profile_update.is_enabled,
        ),
    )
    return _provider_profile_response(profile)


@router.post(
    "/provider-profiles/{profile_id}/test-call",
    response_model=ProviderTestCallResponse,
)
def test_provider_profile(
    profile_id: uuid.UUID,
    test_request: ProviderTestCallRequest,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ProviderTestCallResponse:
    del subject
    require_csrf(request)
    model = _provider_profile_or_404(db_session, profile_id)
    result = ProviderProfileService(db_session, load_settings()).test_profile(
        model,
        test_request.prompt,
    )
    RuntimeDiagnosticsService(db_session).record(
        RuntimeDiagnosticCreate(
            severity=DiagnosticSeverity.INFO
            if result.status.value == "success"
            else DiagnosticSeverity.ERROR,
            component=DiagnosticComponent.PROVIDER,
            event_type="provider.test_call_completed",
            message="Provider test call completed.",
            details={
                "status": result.status.value,
                "latency_ms": result.latency_ms,
                "error_code": None if result.error_code is None else result.error_code.value,
                "error_message": result.error_message,
            },
            provider_profile_id=model.id,
        ),
    )
    return _provider_test_call_response(result)


@router.delete("/provider-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def disable_provider_profile(
    profile_id: uuid.UUID,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    del subject
    require_csrf(request)
    ProviderProfileService(db_session, load_settings()).disable_profile(
        _provider_profile_or_404(db_session, profile_id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _provider_profile_or_404(db_session: Session, profile_id: uuid.UUID) -> ProviderProfile:
    profile = db_session.get(ProviderProfile, profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider profile not found",
        )
    return profile


def _provider_profile_response(profile: ProviderProfileRecord) -> ProviderProfileResponse:
    return ProviderProfileResponse(**profile.model_dump())


def _provider_test_call_response(result: ProviderInvocationResult) -> ProviderTestCallResponse:
    return ProviderTestCallResponse(
        status=result.status.value,
        latency_ms=result.latency_ms,
        text_preview=result.text_preview,
        error_code=None if result.error_code is None else result.error_code.value,
        error_message=result.error_message,
    )


def _runtime_control_response(view: Any) -> RuntimeControlResponse:
    return RuntimeControlResponse(
        desired_state=view.desired_state,
        last_heartbeat_at=view.last_heartbeat_at,
        last_run_started_at=view.last_run_started_at,
        last_run_finished_at=view.last_run_finished_at,
        last_error=view.last_error,
    )


def _diagnostic_response(record: RuntimeDiagnosticRecord) -> RuntimeDiagnosticResponse:
    return RuntimeDiagnosticResponse(**record.model_dump())
