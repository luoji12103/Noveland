from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from noveland.auth import (
    AuthenticatedSubject,
    AuthSessionCreate,
    AuthSessionService,
    InvalidCredentialsError,
)
from noveland.auth.models import User
from noveland.auth.services import PasswordCredentialService
from noveland.core.settings import AppSettings, load_settings
from noveland.services.api.csrf import (
    SESSION_COOKIE_NAME,
    CookiePolicy,
    clear_auth_cookies,
    create_csrf_token,
    require_csrf,
    set_csrf_cookie,
    set_session_cookie,
)
from noveland.services.api.dependencies import get_current_subject, get_db_session
from pydantic import BaseModel, Field, SecretStr, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth", tags=["auth"])


class CsrfResponse(BaseModel):
    csrf_token: str


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: SecretStr

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("email must be an email address")
        return normalized


class SubjectResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    display_name: str
    roles: list[str]


@router.get("/csrf", response_model=CsrfResponse)
def csrf(response: Response) -> CsrfResponse:
    settings = load_settings()
    csrf_token = create_csrf_token()
    set_csrf_cookie(response, csrf_token, policy=_cookie_policy(settings))
    return CsrfResponse(csrf_token=csrf_token)


@router.post("/login", response_model=SubjectResponse)
def login(
    login_request: LoginRequest,
    request: Request,
    response: Response,
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SubjectResponse:
    require_csrf(request)
    settings = load_settings()
    user = _user_by_email(db_session, login_request.email)
    if user is None or not user.is_active:
        raise _invalid_credentials_http_error()

    try:
        PasswordCredentialService(db_session).verify_password(
            user.id,
            login_request.password,
        )
    except InvalidCredentialsError as exc:
        raise _invalid_credentials_http_error() from exc

    created_session = AuthSessionService(db_session).create_session(
        AuthSessionCreate(
            user_id=user.id,
            expires_at=datetime.now(UTC) + _session_ttl(settings),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client is not None else None,
        ),
    )
    subject = AuthSessionService(db_session).authenticate_session(created_session.token)
    csrf_token = create_csrf_token()
    cookie_policy = _cookie_policy(settings)
    set_session_cookie(response, created_session.token, policy=cookie_policy)
    set_csrf_cookie(response, csrf_token, policy=cookie_policy)
    return _subject_response(user, subject)


@router.get("/me", response_model=SubjectResponse)
def me(
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SubjectResponse:
    user = db_session.get(User, subject.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing session",
        )
    return _subject_response(user, subject)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> None:
    settings = load_settings()
    del subject
    require_csrf(request)
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing session",
        )
    AuthSessionService(db_session).revoke_session(token)
    clear_auth_cookies(response, policy=_cookie_policy(settings))


def _user_by_email(db_session: Session, email: str) -> User | None:
    return db_session.scalars(select(User).where(User.email == email)).one_or_none()


def _subject_response(user: User, subject: AuthenticatedSubject) -> SubjectResponse:
    return SubjectResponse(
        user_id=subject.user_id,
        email=user.email,
        display_name=user.display_name,
        roles=sorted(role.value for role in subject.roles),
    )


def _invalid_credentials_http_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
    )


def _cookie_policy(settings: AppSettings) -> CookiePolicy:
    return CookiePolicy(
        max_age_seconds=settings.auth_session_ttl_seconds,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )


def _session_ttl(settings: AppSettings) -> timedelta:
    return timedelta(seconds=settings.auth_session_ttl_seconds)
