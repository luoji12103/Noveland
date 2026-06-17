from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from noveland.conversations.models import (
    ConversationSession,
    ConversationTurn,
    ConversationTurnPresentation,
)
from noveland.media.models import MediaAsset, MediaJob
from noveland.player_sessions.contracts import (
    PlayerRecoveryStatus,
    PlayerSessionRead,
    PlayerSessionStatus,
    PlayerSessionUpsert,
)
from noveland.player_sessions.models import PlayerSession
from noveland.worlds.models import PlayerActorProfile, Scene, World, WorldMembership
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
    "invite_token",
    "object_path",
    "password",
    "path",
    "private_key",
    "prompt_snapshot",
    "event_payload",
    "raw_event_payload",
    "raw_output",
    "raw_prompt",
    "secret",
    "storage_uri",
    "token",
}
_LEAKY_KEY_MARKERS = {re.sub(r"[^a-z0-9]+", "", marker.lower()) for marker in _LEAKY_KEYS}
_PLAYER_DELIVERABLE_MEDIA_VISIBILITIES = {
    "world_member",
    "player_visible",
    "reader_visible",
}
_LEAK_PATTERN = re.compile(
    r"(storage[-_ ]?uri|media://|file://|s3://|gs://|/root/|/tmp/|base64,|"
    r"BEGIN PRIVATE KEY|raw[-_ ]?prompt|raw[-_ ]?output|prompt[-_ ]?snapshot|"
    r"file[-_ ]?path|filesystem[-_ ]?path|object[-_ ]?path|sk-[A-Za-z0-9]|bearer\s+)",
    re.IGNORECASE,
)
_JSON_LIMIT = 8_000


class PlayerSessionError(ValueError):
    pass


class PlayerSessionNotFoundError(PlayerSessionError):
    pass


class PlayerSessionValidationError(PlayerSessionError):
    pass


class PlayerSessionService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_resume(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID,
        player_actor_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> PlayerSessionRead:
        self._membership_or_404(world_id, user_id)
        actor = self._player_actor_or_404(world_id, worldline_id, player_actor_id, user_id)
        session = self._session.scalars(
            select(PlayerSession).where(
                PlayerSession.world_id == world_id,
                PlayerSession.worldline_id == worldline_id,
                PlayerSession.user_id == user_id,
                PlayerSession.player_actor_id == actor.id,
            )
        ).one_or_none()
        if session is None:
            raise PlayerSessionNotFoundError("player session not found")
        return self._read(session)

    def upsert_resume(
        self,
        world_id: uuid.UUID,
        session_upsert: PlayerSessionUpsert,
        *,
        user_id: uuid.UUID,
    ) -> PlayerSessionRead:
        self._world_or_404(world_id)
        self._membership_or_404(world_id, user_id)
        worldline = worldline_or_404(self._session, world_id, session_upsert.worldline_id)
        actor = self._player_actor_or_404(
            world_id,
            worldline.id,
            session_upsert.player_actor_id,
            user_id,
        )
        self._validate_scene(world_id, session_upsert.scene_id)
        conversation = self._validate_conversation(
            world_id,
            worldline.id,
            session_upsert.conversation_session_id,
        )
        self._validate_turn(conversation, session_upsert.last_turn_id)
        presentation = self._validate_presentation(
            world_id,
            worldline.id,
            session_upsert.conversation_session_id,
            session_upsert.last_turn_id,
            session_upsert.last_presentation_id,
        )
        route_state = _sanitize_json(session_upsert.route_state)
        resume_state = _sanitize_json(session_upsert.resume_state)
        recovery_status = self._effective_recovery_status(
            world_id=world_id,
            worldline_id=worldline.id,
            requested=session_upsert.recovery_status,
            conversation=conversation,
            presentation=presentation,
        )
        now = datetime.now(UTC)
        player_session = self._session.scalars(
            select(PlayerSession).where(
                PlayerSession.world_id == world_id,
                PlayerSession.worldline_id == worldline.id,
                PlayerSession.user_id == user_id,
                PlayerSession.player_actor_id == actor.id,
            )
        ).one_or_none()
        if player_session is None:
            player_session = PlayerSession(
                world_id=world_id,
                worldline_id=worldline.id,
                user_id=user_id,
                player_actor_id=actor.id,
                last_seen_at=now,
            )
            self._session.add(player_session)
        player_session.conversation_session_id = session_upsert.conversation_session_id
        player_session.scene_id = session_upsert.scene_id
        player_session.last_turn_id = session_upsert.last_turn_id
        player_session.last_presentation_id = session_upsert.last_presentation_id
        player_session.route_state_json = route_state
        player_session.resume_state_json = resume_state
        player_session.recovery_status = recovery_status.value
        player_session.status = session_upsert.status.value
        player_session.last_seen_at = now
        self._session.flush()
        return self._read(player_session)

    def _validate_conversation(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
    ) -> ConversationSession | None:
        if conversation_id is None:
            return None
        conversation = self._session.get(ConversationSession, conversation_id)
        if (
            conversation is None
            or conversation.world_id != world_id
            or conversation.worldline_id != worldline_id
        ):
            raise PlayerSessionValidationError("conversation does not belong to this worldline")
        return conversation

    def _validate_turn(
        self,
        conversation: ConversationSession | None,
        turn_id: uuid.UUID | None,
    ) -> None:
        if turn_id is None:
            return
        if conversation is None:
            raise PlayerSessionValidationError("last_turn_id requires conversation_session_id")
        turn = self._session.get(ConversationTurn, turn_id)
        if turn is None or turn.session_id != conversation.id:
            raise PlayerSessionValidationError("turn does not belong to this conversation")

    def _validate_presentation(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        turn_id: uuid.UUID | None,
        presentation_id: uuid.UUID | None,
    ) -> ConversationTurnPresentation | None:
        if presentation_id is None:
            return None
        if conversation_id is None or turn_id is None:
            raise PlayerSessionValidationError(
                "last_presentation_id requires conversation_session_id and last_turn_id"
            )
        presentation = self._session.get(ConversationTurnPresentation, presentation_id)
        if (
            presentation is None
            or presentation.world_id != world_id
            or presentation.worldline_id != worldline_id
            or presentation.conversation_id != conversation_id
            or presentation.turn_id != turn_id
        ):
            raise PlayerSessionValidationError("presentation does not belong to this turn")
        return presentation

    def _effective_recovery_status(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        requested: PlayerRecoveryStatus,
        conversation: ConversationSession | None,
        presentation: ConversationTurnPresentation | None,
    ) -> PlayerRecoveryStatus:
        if conversation is not None and conversation.status in {"failed", "stopped"}:
            return PlayerRecoveryStatus.PROVIDER_FAILURE
        if presentation is None:
            return requested
        if presentation.render_state == "failed":
            return PlayerRecoveryStatus.PRESENTATION_UNAVAILABLE
        media_ids = [
            presentation.tts_media_asset_id,
            presentation.background_asset_id,
            presentation.composite_scene_asset_id,
        ]
        if any(
            media_id is not None
            and not self._media_asset_player_safe(world_id, worldline_id, media_id)
            for media_id in media_ids
        ):
            return PlayerRecoveryStatus.MISSING_MEDIA
        if any(
            self._media_job_failed(world_id, worldline_id, media_id)
            for media_id in media_ids
            if media_id is not None
        ):
            return PlayerRecoveryStatus.MEDIA_FAILURE
        return requested

    def _media_asset_player_safe(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        media_id: uuid.UUID,
    ) -> bool:
        from noveland.reader_delivery.service import ReaderMediaDeliveryService

        asset = self._session.get(MediaAsset, media_id)
        return (
            asset is not None
            and asset.world_id == world_id
            and asset.worldline_id == worldline_id
            and asset.status == "available"
            and asset.visibility in _PLAYER_DELIVERABLE_MEDIA_VISIBILITIES
            and ReaderMediaDeliveryService(self._session).get_media(
                world_id,
                media_id,
                worldline_id=worldline_id,
            )
            is not None
        )

    def _media_job_failed(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        media_id: uuid.UUID,
    ) -> bool:
        asset = self._session.get(MediaAsset, media_id)
        if (
            asset is None
            or asset.world_id != world_id
            or asset.worldline_id != worldline_id
            or asset.source_job_id is None
        ):
            return False
        job = self._session.get(MediaJob, asset.source_job_id)
        return (
            job is not None
            and job.world_id == world_id
            and job.worldline_id == worldline_id
            and job.status == "failed"
        )

    def _player_actor_or_404(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        player_actor_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> PlayerActorProfile:
        actor = self._session.get(PlayerActorProfile, player_actor_id)
        if (
            actor is None
            or actor.world_id != world_id
            or actor.worldline_id != worldline_id
            or actor.user_id != user_id
            or not actor.is_active
        ):
            raise PlayerSessionNotFoundError("player actor not found")
        return actor

    def _validate_scene(self, world_id: uuid.UUID, scene_id: uuid.UUID | None) -> None:
        if scene_id is None:
            return
        scene = self._session.get(Scene, scene_id)
        if scene is None or scene.world_id != world_id:
            raise PlayerSessionValidationError("scene does not belong to this world")

    def _membership_or_404(self, world_id: uuid.UUID, user_id: uuid.UUID) -> WorldMembership:
        membership = self._session.scalars(
            select(WorldMembership).where(
                WorldMembership.world_id == world_id,
                WorldMembership.user_id == user_id,
            )
        ).one_or_none()
        if membership is None:
            raise PlayerSessionNotFoundError("world membership not found")
        return membership

    def _world_or_404(self, world_id: uuid.UUID) -> World:
        world = self._session.get(World, world_id)
        if world is None:
            raise PlayerSessionNotFoundError("world not found")
        return world

    def _read(self, session: PlayerSession) -> PlayerSessionRead:
        recovery_status = PlayerRecoveryStatus(session.recovery_status)
        return PlayerSessionRead(
            id=session.id,
            world_id=session.world_id,
            worldline_id=session.worldline_id,
            user_id=session.user_id,
            player_actor_id=session.player_actor_id,
            conversation_session_id=session.conversation_session_id,
            scene_id=session.scene_id,
            last_turn_id=session.last_turn_id,
            last_presentation_id=session.last_presentation_id,
            route_state=_sanitize_json(session.route_state_json),
            resume_state=_sanitize_json(session.resume_state_json),
            recovery_status=recovery_status,
            recovery_label=_recovery_label(recovery_status),
            available_actions=_available_actions(recovery_status, session.conversation_session_id),
            status=PlayerSessionStatus(session.status),
            last_seen_at=_aware_datetime(session.last_seen_at),
            created_at=_aware_datetime(session.created_at),
            updated_at=_aware_datetime(session.updated_at),
        )



def _sanitize_json(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PlayerSessionValidationError("state payload must be an object")
    sanitized = _sanitize_mapping(value)
    serialized = str(sanitized)
    if len(serialized) > _JSON_LIMIT:
        raise PlayerSessionValidationError("state payload is too large")
    return sanitized


def _sanitize_mapping(value: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key)
        if _is_leaky_key(key_text):
            continue
        clean_item = _sanitize_value(item)
        if clean_item is not None:
            sanitized[key_text] = clean_item
    return sanitized


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _sanitize_mapping(value)
    if isinstance(value, list):
        return [item for item in (_sanitize_value(item) for item in value[:50]) if item is not None]
    if isinstance(value, str):
        return None if _LEAK_PATTERN.search(value) else value[:500]
    if isinstance(value, int | float | bool) or value is None:
        return value
    return str(value)[:200]


def _is_leaky_key(key: str) -> bool:
    normalized = _normalize_sensitive_key(key)
    return any(marker and marker in normalized for marker in _LEAKY_KEY_MARKERS)


def _normalize_sensitive_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _recovery_label(status: PlayerRecoveryStatus) -> str:
    return {
        PlayerRecoveryStatus.READY: "Ready to resume.",
        PlayerRecoveryStatus.STALE_CONVERSATION: "Conversation needs a fresh player step.",
        PlayerRecoveryStatus.MISSING_MEDIA: "Media is unavailable; text playback can continue.",
        PlayerRecoveryStatus.PROVIDER_FAILURE: "Generation failed; retry is operator-controlled.",
        PlayerRecoveryStatus.MEDIA_FAILURE: "Media job failed; text playback can continue.",
        PlayerRecoveryStatus.PRESENTATION_UNAVAILABLE: (
            "Presentation is unavailable; use text playback."
        ),
    }[status]


def _available_actions(
    status: PlayerRecoveryStatus,
    conversation_id: uuid.UUID | None,
) -> tuple[str, ...]:
    actions = ["open_player_surface"]
    if conversation_id is not None:
        actions.append("open_reader_playback")
    if status != PlayerRecoveryStatus.READY:
        actions.append("report_feedback")
    return tuple(actions)


def _aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
