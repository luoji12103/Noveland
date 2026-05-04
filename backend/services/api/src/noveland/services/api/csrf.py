from __future__ import annotations

import secrets
from typing import Literal

from fastapi import HTTPException, Request, Response, status

SESSION_COOKIE_NAME = "noveland_session"
CSRF_COOKIE_NAME = "noveland_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"
COOKIE_PATH = "/"
COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
COOKIE_SECURE = False
SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


class CookiePolicy:
    def __init__(
        self,
        *,
        max_age_seconds: int = SESSION_MAX_AGE_SECONDS,
        secure: bool = COOKIE_SECURE,
        samesite: Literal["lax", "strict", "none"] = COOKIE_SAMESITE,
    ) -> None:
        self.max_age_seconds = max_age_seconds
        self.secure = secure
        self.samesite = samesite


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_session_cookie(
    response: Response,
    token: str,
    *,
    policy: CookiePolicy | None = None,
) -> None:
    cookie_policy = policy or CookiePolicy()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=cookie_policy.max_age_seconds,
        httponly=True,
        secure=cookie_policy.secure,
        samesite=cookie_policy.samesite,
        path=COOKIE_PATH,
    )


def set_csrf_cookie(
    response: Response,
    token: str,
    *,
    policy: CookiePolicy | None = None,
) -> None:
    cookie_policy = policy or CookiePolicy()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        max_age=cookie_policy.max_age_seconds,
        httponly=False,
        secure=cookie_policy.secure,
        samesite=cookie_policy.samesite,
        path=COOKIE_PATH,
    )


def clear_auth_cookies(response: Response, *, policy: CookiePolicy | None = None) -> None:
    cookie_policy = policy or CookiePolicy()
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path=COOKIE_PATH,
        secure=cookie_policy.secure,
        samesite=cookie_policy.samesite,
    )
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path=COOKIE_PATH,
        secure=cookie_policy.secure,
        samesite=cookie_policy.samesite,
    )


def require_csrf(request: Request) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if (
        cookie_token is None
        or header_token is None
        or not secrets.compare_digest(cookie_token, header_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token is missing or invalid",
        )
