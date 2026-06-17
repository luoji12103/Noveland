from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from noveland.auth.contracts import AuthRole
from noveland.auth.models import User
from noveland.private_beta.contracts import (
    PrivateBetaAccessRead,
    PrivateBetaInviteCreate,
    PrivateBetaInviteCreated,
    PrivateBetaInviteRead,
    PrivateBetaInviteRevoke,
    PrivateBetaInviteStatus,
    PrivateBetaOnboardingStatus,
    PrivateBetaPlayerProfileCreate,
    PrivateBetaPlayerProfileRead,
    PrivateBetaPlayerProfileResult,
    PrivateBetaRedeemResult,
    PrivateBetaRole,
)
from noveland.private_beta.models import PrivateBetaInvite
from noveland.private_beta.tokens import generate_invite_token, hash_invite_token
from noveland.worlds.gm import LivingWorldGMService
from noveland.worlds.models import PlayerActorProfile, Scene, World, Worldline, WorldMembership
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import select
from sqlalchemy.orm import Session

_LEAKY_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "base64",
    "bearer_token",
    "bytes",
    "client_secret",
    "file_path",
    "filesystem_path",
    "object_path",
    "password",
    "path",
    "private_key",
    "prompt_snapshot",
    "raw_output",
    "raw_prompt",
    "secret",
    "storage_uri",
    "token",
}
_LEAKY_KEY_MARKERS = {
    re.sub(r"[^a-z0-9]+", "", marker.lower()) for marker in _LEAKY_KEYS
}
_LEAK_PATTERN = re.compile(
    r"(storage[-_ ]?uri|media://|file://|s3://|gs://|/root/|/tmp/|base64,|"
    r"BEGIN PRIVATE KEY|raw[-_ ]?prompt|raw[-_ ]?output|prompt[-_ ]?snapshot|"
    r"file[-_ ]?path|filesystem[-_ ]?path|object[-_ ]?path|sk-[A-Za-z0-9]|bearer\s+)",
    re.IGNORECASE,
)


class PrivateBetaError(ValueError):
    pass


class PrivateBetaNotFoundError(PrivateBetaError):
    pass


class PrivateBetaValidationError(PrivateBetaError):
    pass


class PrivateBetaService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_invite(
        self,
        world_id: uuid.UUID,
        invite_create: PrivateBetaInviteCreate,
        *,
        actor_ref: str,
    ) -> PrivateBetaInviteCreated:
        now = datetime.now(UTC)
        if invite_create.expires_at <= now:
            raise PrivateBetaValidationError("invite expires_at must be in the future")
        self._world_or_404(world_id)
        if invite_create.worldline_id is not None:
            try:
                worldline_or_404(self._session, world_id, invite_create.worldline_id)
            except ValueError as exc:
                raise PrivateBetaNotFoundError("worldline not found") from exc
        if invite_create.invited_user_id is not None:
            self._active_user_or_404(invite_create.invited_user_id)
        _validate_safe_json(invite_create.metadata)
        token = generate_invite_token()
        status = invite_create.status.value
        if status == PrivateBetaInviteStatus.REDEEMED.value:
            raise PrivateBetaValidationError("new invites cannot start redeemed")
        if status in {
            PrivateBetaInviteStatus.EXPIRED.value,
            PrivateBetaInviteStatus.REVOKED.value,
        }:
            raise PrivateBetaValidationError("new invites must start redeemable or waitlisted")
        invite = PrivateBetaInvite(
            world_id=world_id,
            worldline_id=invite_create.worldline_id,
            invited_email=invite_create.invited_email,
            invited_user_id=invite_create.invited_user_id,
            token_hash=hash_invite_token(token),
            status=status,
            intended_world_role=AuthRole.HUMAN_USER.value,
            beta_role=invite_create.beta_role.value,
            expires_at=invite_create.expires_at,
            accepted_at=now if status == PrivateBetaInviteStatus.ACCEPTED.value else None,
            created_by_actor_ref=actor_ref,
            metadata_json=_sanitize_json(invite_create.metadata),
        )
        self._session.add(invite)
        self._session.flush()
        return PrivateBetaInviteCreated(invite=self._invite_read(invite), token=token)

    def list_invites(
        self,
        world_id: uuid.UUID,
        *,
        status: PrivateBetaInviteStatus | None = None,
        limit: int = 100,
    ) -> list[PrivateBetaInviteRead]:
        self._world_or_404(world_id)
        statement = (
            select(PrivateBetaInvite)
            .where(PrivateBetaInvite.world_id == world_id)
            .order_by(PrivateBetaInvite.created_at.desc())
            .limit(max(1, min(limit, 200)))
        )
        if status is not None:
            statement = statement.where(PrivateBetaInvite.status == status.value)
        return [self._invite_read(invite) for invite in self._session.scalars(statement).all()]

    def get_invite(self, world_id: uuid.UUID, invite_id: uuid.UUID) -> PrivateBetaInviteRead:
        return self._invite_read(self._invite_or_404(world_id, invite_id))

    def revoke_invite(
        self,
        world_id: uuid.UUID,
        invite_id: uuid.UUID,
        revoke: PrivateBetaInviteRevoke,
        *,
        actor_ref: str,
    ) -> PrivateBetaInviteRead:
        _validate_safe_text(revoke.reason, "reason")
        invite = self._invite_or_404(world_id, invite_id)
        if invite.status == PrivateBetaInviteStatus.REDEEMED.value:
            raise PrivateBetaValidationError("redeemed invites cannot be revoked")
        now = datetime.now(UTC)
        invite.status = PrivateBetaInviteStatus.REVOKED.value
        invite.revoked_at = now
        invite.revoked_by_actor_ref = actor_ref
        invite.revocation_reason = revoke.reason
        self._session.flush()
        return self._invite_read(invite)

    def redeem_invite(
        self,
        token: str,
        *,
        user_id: uuid.UUID,
    ) -> PrivateBetaRedeemResult:
        invite = self._invite_for_token(token)
        if invite is None:
            raise PrivateBetaNotFoundError("private beta invite not found")
        now = datetime.now(UTC)
        if invite.status == PrivateBetaInviteStatus.REDEEMED.value:
            if invite.redeemed_by_user_id == user_id:
                return PrivateBetaRedeemResult(
                    access=self._access_read(invite),
                    membership_role=AuthRole.HUMAN_USER.value,
                    idempotent=True,
                )
            raise PrivateBetaValidationError("invite has already been redeemed")
        if invite.status in {
            PrivateBetaInviteStatus.REVOKED.value,
            PrivateBetaInviteStatus.WAITLISTED.value,
            PrivateBetaInviteStatus.EXPIRED.value,
        }:
            raise PrivateBetaValidationError("invite is not redeemable")
        if _database_datetime(invite.expires_at) <= now:
            invite.status = PrivateBetaInviteStatus.EXPIRED.value
            self._session.flush()
            raise PrivateBetaValidationError("invite has expired")
        if invite.invited_user_id is not None and invite.invited_user_id != user_id:
            raise PrivateBetaValidationError("invite is assigned to another user")
        if invite.invited_email is not None:
            user = self._active_user_or_404(user_id)
            if user.email.strip().lower() != invite.invited_email.strip().lower():
                raise PrivateBetaValidationError("invite email does not match current user")
        self._upsert_least_privilege_membership(invite.world_id, user_id)
        invite.status = PrivateBetaInviteStatus.REDEEMED.value
        invite.redeemed_at = now
        invite.redeemed_by_user_id = user_id
        self._session.flush()
        return PrivateBetaRedeemResult(
            access=self._access_read(invite),
            membership_role=AuthRole.HUMAN_USER.value,
            idempotent=False,
        )

    def onboarding_status(self, *, user_id: uuid.UUID) -> PrivateBetaOnboardingStatus:
        invites = self._session.scalars(
            select(PrivateBetaInvite)
            .where(
                PrivateBetaInvite.redeemed_by_user_id == user_id,
                PrivateBetaInvite.status == PrivateBetaInviteStatus.REDEEMED.value,
            )
            .order_by(PrivateBetaInvite.redeemed_at.desc(), PrivateBetaInvite.created_at.desc())
        ).all()
        return PrivateBetaOnboardingStatus(
            access=tuple(self._access_read(invite) for invite in invites),
            guidance=(
                "Choose an invited world and create a player identity before play.",
                "Use only the player and reader surfaces unless an admin grants additional access.",
                "If playback or generation fails, keep the session and report the issue.",
            ),
        )

    def bootstrap_player_profile(
        self,
        world_id: uuid.UUID,
        user_id: uuid.UUID,
        profile_create: PrivateBetaPlayerProfileCreate,
    ) -> PrivateBetaPlayerProfileResult:
        invite = self._redeemed_invite_for_user(world_id, user_id)
        requested_worldline_id = profile_create.worldline_id or invite.worldline_id
        if invite.worldline_id is not None and requested_worldline_id != invite.worldline_id:
            raise PrivateBetaValidationError("invite is restricted to another worldline")
        worldline = worldline_or_404(self._session, world_id, requested_worldline_id)
        if profile_create.current_scene_id is not None:
            scene = self._session.get(Scene, profile_create.current_scene_id)
            if scene is None or scene.world_id != world_id:
                raise PrivateBetaNotFoundError("scene not found")
        _validate_safe_json(profile_create.profile)
        self._membership_or_404(world_id, user_id)
        actor = LivingWorldGMService(self._session).bind_player_actor(
            world_id=world_id,
            worldline_id=worldline.id,
            user_id=user_id,
            display_name=profile_create.display_name,
            current_scene_id=profile_create.current_scene_id,
            profile=_sanitize_json(profile_create.profile),
        )
        self._session.flush()
        return PrivateBetaPlayerProfileResult(
            access=self._access_read(invite),
            player_profile=self._profile_read(actor),
        )

    def _invite_for_token(self, token: str) -> PrivateBetaInvite | None:
        if not token:
            return None
        return self._session.scalars(
            select(PrivateBetaInvite).where(
                PrivateBetaInvite.token_hash == hash_invite_token(token),
            )
        ).one_or_none()

    def _invite_or_404(self, world_id: uuid.UUID, invite_id: uuid.UUID) -> PrivateBetaInvite:
        invite = self._session.get(PrivateBetaInvite, invite_id)
        if invite is None or invite.world_id != world_id:
            raise PrivateBetaNotFoundError("private beta invite not found")
        return invite

    def _redeemed_invite_for_user(
        self,
        world_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> PrivateBetaInvite:
        invite = self._session.scalars(
            select(PrivateBetaInvite)
            .where(
                PrivateBetaInvite.world_id == world_id,
                PrivateBetaInvite.redeemed_by_user_id == user_id,
                PrivateBetaInvite.status == PrivateBetaInviteStatus.REDEEMED.value,
            )
            .order_by(PrivateBetaInvite.redeemed_at.desc(), PrivateBetaInvite.created_at.desc())
            .limit(1)
        ).one_or_none()
        if invite is None:
            raise PrivateBetaNotFoundError("private beta access not found")
        return invite

    def _upsert_least_privilege_membership(self, world_id: uuid.UUID, user_id: uuid.UUID) -> None:
        membership = self._session.scalars(
            select(WorldMembership).where(
                WorldMembership.world_id == world_id,
                WorldMembership.user_id == user_id,
            )
        ).one_or_none()
        if membership is None:
            self._session.add(
                WorldMembership(
                    world_id=world_id,
                    user_id=user_id,
                    role=AuthRole.HUMAN_USER.value,
                )
            )
        elif membership.role != AuthRole.WORLD_ADMIN.value:
            membership.role = AuthRole.HUMAN_USER.value

    def _membership_or_404(self, world_id: uuid.UUID, user_id: uuid.UUID) -> WorldMembership:
        membership = self._session.scalars(
            select(WorldMembership).where(
                WorldMembership.world_id == world_id,
                WorldMembership.user_id == user_id,
            )
        ).one_or_none()
        if membership is None:
            raise PrivateBetaNotFoundError("world membership not found")
        return membership

    def _world_or_404(self, world_id: uuid.UUID) -> World:
        world = self._session.get(World, world_id)
        if world is None:
            raise PrivateBetaNotFoundError("world not found")
        return world

    def _active_user_or_404(self, user_id: uuid.UUID) -> User:
        user = self._session.get(User, user_id)
        if user is None or not user.is_active:
            raise PrivateBetaNotFoundError("user not found")
        return user

    def _invite_read(self, invite: PrivateBetaInvite) -> PrivateBetaInviteRead:
        return PrivateBetaInviteRead(
            id=invite.id,
            world_id=invite.world_id,
            worldline_id=invite.worldline_id,
            invited_email=invite.invited_email,
            invited_user_id=invite.invited_user_id,
            status=PrivateBetaInviteStatus(invite.status),
            intended_world_role=invite.intended_world_role,
            beta_role=PrivateBetaRole(invite.beta_role),
            expires_at=_database_datetime(invite.expires_at),
            accepted_at=_optional_database_datetime(invite.accepted_at),
            redeemed_at=_optional_database_datetime(invite.redeemed_at),
            redeemed_by_user_id=invite.redeemed_by_user_id,
            revoked_at=_optional_database_datetime(invite.revoked_at),
            revoked_by_actor_ref=invite.revoked_by_actor_ref,
            revocation_reason=invite.revocation_reason,
            created_by_actor_ref=invite.created_by_actor_ref,
            metadata=_sanitize_json(invite.metadata_json),
            created_at=_database_datetime(invite.created_at),
            updated_at=_database_datetime(invite.updated_at),
        )

    def _access_read(self, invite: PrivateBetaInvite) -> PrivateBetaAccessRead:
        world = self._world_or_404(invite.world_id)
        worldline = (
            self._session.get(Worldline, invite.worldline_id)
            if invite.worldline_id
            else None
        )
        player_profile = None
        if invite.redeemed_by_user_id is not None:
            actor_statement = select(PlayerActorProfile).where(
                PlayerActorProfile.world_id == invite.world_id,
                PlayerActorProfile.user_id == invite.redeemed_by_user_id,
            )
            if invite.worldline_id is not None:
                actor_statement = actor_statement.where(
                    PlayerActorProfile.worldline_id == invite.worldline_id,
                )
            actor = self._session.scalars(
                actor_statement.order_by(PlayerActorProfile.updated_at.desc()).limit(1)
            ).one_or_none()
            if actor is not None:
                player_profile = self._profile_read(actor)
        return PrivateBetaAccessRead(
            invite_id=invite.id,
            world_id=invite.world_id,
            world_name=world.name,
            worldline_id=invite.worldline_id,
            worldline_name=None if worldline is None else worldline.name,
            status=PrivateBetaInviteStatus(invite.status),
            beta_role=PrivateBetaRole(invite.beta_role),
            expires_at=_database_datetime(invite.expires_at),
            redeemed_at=_optional_database_datetime(invite.redeemed_at),
            player_profile=player_profile,
        )

    def _profile_read(self, actor: PlayerActorProfile) -> PrivateBetaPlayerProfileRead:
        return PrivateBetaPlayerProfileRead(
            id=actor.id,
            world_id=actor.world_id,
            worldline_id=actor.worldline_id,
            user_id=actor.user_id,
            actor_ref=actor.actor_ref,
            display_name=actor.display_name,
            current_scene_id=actor.current_scene_id,
            profile=_sanitize_json(actor.profile_json),
            is_active=actor.is_active,
            created_at=_database_datetime(actor.created_at),
            updated_at=_database_datetime(actor.updated_at),
        )


def _database_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _optional_database_datetime(value: datetime | None) -> datetime | None:
    return None if value is None else _database_datetime(value)


def _validate_safe_json(value: object) -> None:
    try:
        sanitized = _sanitize_json(value)
    except TypeError as exc:
        raise PrivateBetaValidationError("metadata must be JSON-compatible") from exc
    if _contains_forbidden_marker(sanitized):
        raise PrivateBetaValidationError("metadata contains unsafe content")


def _validate_safe_text(value: str | None, field_name: str) -> None:
    if value is not None and _LEAK_PATTERN.search(value):
        raise PrivateBetaValidationError(f"{field_name} contains unsafe content")


def _sanitize_json(value: object) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_leaky_key(key_text):
                continue
            sanitized[key_text] = _sanitize_json(item)
        return sanitized
    if isinstance(value, list | tuple | set):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, str):
        if _LEAK_PATTERN.search(value):
            return "[REDACTED]"
        return value
    if value is None or isinstance(value, bool | int | float):
        return value
    return str(value)


def _contains_forbidden_marker(value: object) -> bool:
    return _LEAK_PATTERN.search(str(value)) is not None


def _is_leaky_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "", key.lower())
    return any(marker and marker in normalized for marker in _LEAKY_KEY_MARKERS)
