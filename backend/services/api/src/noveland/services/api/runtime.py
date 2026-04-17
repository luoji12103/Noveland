from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from noveland.adapters import (
    ProviderProfileCreate,
    ProviderProfileRecord,
    ProviderProfileService,
    ProviderProfileUpdate,
    ProviderType,
)
from noveland.adapters.models import ProviderProfile
from noveland.auth import AuthenticatedSubject
from noveland.core.settings import load_settings
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


class ProviderProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    capabilities: dict[str, Any] | None = None
    api_key_ref: str | None = Field(default=None, min_length=1, max_length=120)
    is_enabled: bool | None = None


class ProviderProfileResponse(BaseModel):
    id: uuid.UUID
    profile_key: str
    name: str
    provider_type: ProviderType
    base_url: str
    model_name: str
    capabilities: dict[str, Any]
    api_key_ref: str
    is_enabled: bool


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
            is_enabled=profile_update.is_enabled,
        ),
    )
    return _provider_profile_response(profile)


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


def _runtime_control_response(view: Any) -> RuntimeControlResponse:
    return RuntimeControlResponse(
        desired_state=view.desired_state,
        last_heartbeat_at=view.last_heartbeat_at,
        last_run_started_at=view.last_run_started_at,
        last_run_finished_at=view.last_run_finished_at,
        last_error=view.last_error,
    )
