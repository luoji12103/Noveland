from __future__ import annotations

import hashlib
import secrets
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from noveland.auth.contracts import (
    AuthenticatedSubject,
    AuthRole,
    AuthSessionCreate,
    AuthSessionRecord,
    AuthSessionStatus,
    CreatedAuthSession,
    PasswordCredentialRecord,
    PasswordCredentialSet,
)
from noveland.auth.errors import (
    AuthValidationError,
    InvalidCredentialsError,
    InvalidSessionError,
)
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User, UserCredential
from noveland.core.database import import_model_modules
from pwdlib import PasswordHash
from pydantic import SecretStr, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

PasswordCredentialInput = PasswordCredentialSet | Mapping[str, Any]
AuthSessionCreateInput = AuthSessionCreate | Mapping[str, Any]


class PasswordCredentialService:
    def __init__(self, session: Session, password_hash: PasswordHash | None = None) -> None:
        import_model_modules()
        self._session = session
        self._password_hash = password_hash or PasswordHash.recommended()

    def set_password(self, credential: PasswordCredentialInput) -> PasswordCredentialRecord:
        credential_input = _coerce_password_credential(credential)
        user = self._active_user_or_none(credential_input.user_id)
        if user is None:
            raise AuthValidationError("user does not exist or is inactive")

        now = datetime.now(UTC)
        password_hash = self._password_hash.hash(
            credential_input.password.get_secret_value(),
        )
        credential_model = self._credential_for_user(credential_input.user_id)
        try:
            if credential_model is None:
                credential_model = UserCredential(
                    user_id=credential_input.user_id,
                    password_hash=password_hash,
                    password_set_at=now,
                    password_updated_at=now,
                )
                self._session.add(credential_model)
            else:
                credential_model.password_hash = password_hash
                credential_model.password_updated_at = now
                credential_model.disabled_at = None
            self._session.flush()
            self._session.refresh(credential_model)
        except SQLAlchemyError as exc:
            raise AuthValidationError("failed to set password credential") from exc

        return _credential_record_from_model(credential_model)

    def verify_password(
        self,
        user_id: uuid.UUID,
        password: SecretStr | str,
    ) -> PasswordCredentialRecord:
        user = self._active_user_or_none(user_id)
        credential_model = self._credential_for_user(user_id)
        if user is None or credential_model is None or credential_model.disabled_at is not None:
            raise InvalidCredentialsError("invalid credentials")

        plain_password = (
            password.get_secret_value()
            if isinstance(password, SecretStr)
            else password
        )
        try:
            verified, updated_hash = self._password_hash.verify_and_update(
                plain_password,
                credential_model.password_hash,
            )
        except Exception as exc:
            raise InvalidCredentialsError("invalid credentials") from exc

        if not verified:
            raise InvalidCredentialsError("invalid credentials")

        if updated_hash is not None:
            credential_model.password_hash = updated_hash
            credential_model.password_updated_at = datetime.now(UTC)
            self._session.flush()
            self._session.refresh(credential_model)

        return _credential_record_from_model(credential_model)

    def _active_user_or_none(self, user_id: uuid.UUID) -> User | None:
        return self._session.scalars(
            select(User).where(User.id == user_id, User.is_active.is_(True)),
        ).one_or_none()

    def _credential_for_user(self, user_id: uuid.UUID) -> UserCredential | None:
        return self._session.scalars(
            select(UserCredential).where(UserCredential.user_id == user_id),
        ).one_or_none()


class AuthSessionService:
    def __init__(self, session: Session) -> None:
        import_model_modules()
        self._session = session

    def create_session(self, session_create: AuthSessionCreateInput) -> CreatedAuthSession:
        session_input = _coerce_session_create(session_create)
        now = datetime.now(UTC)
        if session_input.expires_at <= now:
            raise AuthValidationError("session expires_at must be in the future")

        user = self._active_user_or_none(session_input.user_id)
        if user is None:
            raise AuthValidationError("user does not exist or is inactive")

        token = secrets.token_urlsafe(48)
        session_model = AuthSession(
            user_id=session_input.user_id,
            token_hash=hash_session_token(token),
            status=AuthSessionStatus.ACTIVE.value,
            expires_at=session_input.expires_at,
            user_agent=session_input.user_agent,
            ip_address=session_input.ip_address,
        )
        try:
            self._session.add(session_model)
            self._session.flush()
            self._session.refresh(session_model)
        except SQLAlchemyError as exc:
            raise AuthValidationError("failed to create auth session") from exc

        return CreatedAuthSession(
            token=token,
            session=_session_record_from_model(session_model),
        )

    def authenticate_session(self, token: str) -> AuthenticatedSubject:
        now = datetime.now(UTC)
        session_model = self._session_for_token(token)
        if session_model is None:
            raise InvalidSessionError("invalid session")

        if session_model.status == AuthSessionStatus.REVOKED.value:
            raise InvalidSessionError("invalid session")

        if (
            session_model.status == AuthSessionStatus.EXPIRED.value
            or session_model.expires_at <= now
        ):
            self._expire_session_model(session_model, now)
            raise InvalidSessionError("invalid session")

        user = self._active_user_or_none(session_model.user_id)
        if user is None:
            raise InvalidSessionError("invalid session")

        session_model.last_seen_at = now
        self._session.flush()
        return AuthenticatedSubject(
            user_id=session_model.user_id,
            session_id=session_model.id,
            roles=self._platform_roles_for_user(session_model.user_id),
            authenticated_at=now,
        )

    def revoke_session(self, token: str, revoked_at: datetime | None = None) -> AuthSessionRecord:
        session_model = self._session_for_token(token)
        if session_model is None:
            raise InvalidSessionError("invalid session")

        revoked_time = _normalize_datetime(revoked_at or datetime.now(UTC))
        if session_model.status != AuthSessionStatus.REVOKED.value:
            session_model.status = AuthSessionStatus.REVOKED.value
            session_model.revoked_at = revoked_time
            self._session.flush()
            self._session.refresh(session_model)
        return _session_record_from_model(session_model)

    def expire_session(self, token: str, expired_at: datetime | None = None) -> AuthSessionRecord:
        session_model = self._session_for_token(token)
        if session_model is None:
            raise InvalidSessionError("invalid session")

        expired_time = _normalize_datetime(expired_at or datetime.now(UTC))
        self._expire_session_model(session_model, expired_time)
        self._session.refresh(session_model)
        return _session_record_from_model(session_model)

    def _active_user_or_none(self, user_id: uuid.UUID) -> User | None:
        return self._session.scalars(
            select(User).where(User.id == user_id, User.is_active.is_(True)),
        ).one_or_none()

    def _session_for_token(self, token: str) -> AuthSession | None:
        if not token:
            return None
        return self._session.scalars(
            select(AuthSession).where(AuthSession.token_hash == hash_session_token(token)),
        ).one_or_none()

    def _platform_roles_for_user(self, user_id: uuid.UUID) -> frozenset[AuthRole]:
        role_values = self._session.scalars(
            select(PlatformRoleAssignment.role).where(
                PlatformRoleAssignment.user_id == user_id,
            ),
        ).all()
        return frozenset(AuthRole(role_value) for role_value in role_values)

    def _expire_session_model(self, session_model: AuthSession, expired_at: datetime) -> None:
        if session_model.status == AuthSessionStatus.REVOKED.value:
            return
        session_model.status = AuthSessionStatus.EXPIRED.value
        session_model.last_seen_at = expired_at
        self._session.flush()


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _coerce_password_credential(credential: PasswordCredentialInput) -> PasswordCredentialSet:
    if isinstance(credential, PasswordCredentialSet):
        return credential
    try:
        return PasswordCredentialSet.model_validate(credential)
    except ValidationError as exc:
        raise AuthValidationError("invalid password credential input") from exc


def _coerce_session_create(session_create: AuthSessionCreateInput) -> AuthSessionCreate:
    if isinstance(session_create, AuthSessionCreate):
        return session_create
    try:
        return AuthSessionCreate.model_validate(session_create)
    except ValidationError as exc:
        raise AuthValidationError("invalid session input") from exc


def _credential_record_from_model(credential_model: UserCredential) -> PasswordCredentialRecord:
    return PasswordCredentialRecord(
        id=credential_model.id,
        user_id=credential_model.user_id,
        password_hash=credential_model.password_hash,
        password_set_at=credential_model.password_set_at,
        password_updated_at=credential_model.password_updated_at,
        disabled_at=credential_model.disabled_at,
    )


def _session_record_from_model(session_model: AuthSession) -> AuthSessionRecord:
    return AuthSessionRecord(
        id=session_model.id,
        user_id=session_model.user_id,
        token_hash=session_model.token_hash,
        status=AuthSessionStatus(session_model.status),
        expires_at=session_model.expires_at,
        revoked_at=session_model.revoked_at,
        last_seen_at=session_model.last_seen_at,
        user_agent=session_model.user_agent,
        ip_address=session_model.ip_address,
        created_at=session_model.created_at,
    )


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AuthValidationError("datetimes must be timezone-aware")
    return value.astimezone(UTC)
