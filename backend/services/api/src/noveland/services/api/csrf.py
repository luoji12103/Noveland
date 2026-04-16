from __future__ import annotations

import secrets
from typing import Literal

from fastapi import HTTPException, Request, Response, status

SESSION_COOKIE_NAME = "noveland_session"
CSRF_COOKIE_NAME = "noveland_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"
COOKIE_PATH = "/"
COOKIE_SAMESITE: Literal["lax"] = "lax"
COOKIE_SECURE = False
SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
    )


def set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=False,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path=COOKIE_PATH, samesite=COOKIE_SAMESITE)
    response.delete_cookie(key=CSRF_COOKIE_NAME, path=COOKIE_PATH, samesite=COOKIE_SAMESITE)


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
