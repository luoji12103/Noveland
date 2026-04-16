from __future__ import annotations


class AuthError(RuntimeError):
    """Base error for auth/session failures."""


class AuthValidationError(ValueError):
    """Raised when auth input does not match the auth contract."""


class InvalidCredentialsError(AuthError):
    """Raised when a credential cannot authenticate a user."""


class InvalidSessionError(AuthError):
    """Raised when an opaque session token cannot authenticate a subject."""
