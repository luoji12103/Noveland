from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from noveland.auth.models import User
from noveland.conversations.models import ConversationSession
from noveland.player_privacy.contracts import (
    PlayerPrivacyActorExport,
    PlayerPrivacyChoiceExport,
    PlayerPrivacyConversationReference,
    PlayerPrivacyExport,
    PlayerPrivacyInterventionExport,
    PlayerPrivacyJournalExport,
    PlayerPrivacyNotificationExport,
    PlayerPrivacyProfile,
    PlayerPrivacyRequestCreate,
    PlayerPrivacyRequestKind,
    PlayerPrivacyRequestRead,
    PlayerPrivacyRequestReview,
    PlayerPrivacyRequestStatus,
)
from noveland.player_privacy.models import PlayerPrivacyRequest
from noveland.worlds.models import (
    InWorldNotification,
    PlayerActorProfile,
    PlayerChoiceRecord,
    PlayerInterventionRecord,
    PlayerJournalEntry,
    Worldline,
    WorldMembership,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

_LEAKY_KEYS = {
    "api_key",
    "apikey",
    "token",
    "bearer_token",
    "authorization",
    "secret",
    "client_secret",
    "access_key",
    "password",
    "private_key",
    "storage_uri",
    "preview_uri",
    "thumbnail_uri",
    "base64",
    "bytes",
    "path",
    "file_path",
    "filesystem_path",
    "raw_prompt",
    "raw_output",
    "prompt_snapshot",
}
_LEAK_PATTERN = re.compile(
    r"(storage_uri|media://|file://|s3://|gs://|/root/|/tmp/|base64,|BEGIN PRIVATE KEY|"
    r"sk-[A-Za-z0-9]|raw_prompt|raw_output)",
    re.IGNORECASE,
)
_REDACTED = "[REDACTED]"


class PlayerPrivacyError(ValueError):
    pass


class PlayerPrivacyNotFoundError(PlayerPrivacyError):
    pass


class PlayerPrivacyValidationError(PlayerPrivacyError):
    pass


class PlayerPrivacyService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def build_export(
        self,
        world_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
        persist_request: bool = False,
        actor_ref: str | None = None,
    ) -> PlayerPrivacyExport:
        resolved_worldline_id = self._resolve_worldline_id(world_id, worldline_id)
        export = self._build_export_payload(world_id, resolved_worldline_id, user_id)
        if not persist_request:
            return export
        request = PlayerPrivacyRequest(
            world_id=world_id,
            worldline_id=resolved_worldline_id,
            user_id=user_id,
            request_kind=PlayerPrivacyRequestKind.EXPORT.value,
            status=PlayerPrivacyRequestStatus.COMPLETED.value,
            target_ref_kind="all_player_data",
            target_ref_id=None,
            reason=None,
            summary_json={
                "counts": dict(export.counts),
                "safeguards": list(export.safeguards),
            },
            redaction_plan_json={},
            created_by_actor_ref=actor_ref or _actor_ref(user_id),
            metadata_json={"generated_synchronously": True},
        )
        self._session.add(request)
        self._session.flush()
        return export.model_copy(update={"request_id": request.id})

    def list_requests(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        include_all_users: bool = False,
        limit: int = 100,
    ) -> list[PlayerPrivacyRequestRead]:
        statement = (
            select(PlayerPrivacyRequest)
            .where(PlayerPrivacyRequest.world_id == world_id)
            .order_by(PlayerPrivacyRequest.created_at.desc())
            .limit(max(1, min(limit, 200)))
        )
        if worldline_id is not None:
            statement = statement.where(PlayerPrivacyRequest.worldline_id == worldline_id)
        if not include_all_users:
            if user_id is None:
                raise PlayerPrivacyValidationError("user_id is required")
            statement = statement.where(PlayerPrivacyRequest.user_id == user_id)
        return [self._request_read(request) for request in self._session.scalars(statement).all()]

    def create_delete_request(
        self,
        world_id: uuid.UUID,
        user_id: uuid.UUID,
        request: PlayerPrivacyRequestCreate,
        *,
        actor_ref: str | None = None,
    ) -> PlayerPrivacyRequestRead:
        _validate_safe_text(request.reason, "reason")
        resolved_worldline_id = self._resolve_worldline_id(world_id, request.worldline_id)
        export = self._build_export_payload(world_id, resolved_worldline_id, user_id)
        summary = {
            "target_ref_kind": request.target_ref_kind.value,
            "target_ref_id": None if request.target_ref_id is None else str(request.target_ref_id),
            "counts": dict(export.counts),
            "shared_world_records_protected": True,
        }
        redaction_plan = {
            "mode": "review_required",
            "automatic_delete": False,
            "shared_canonical_records_protected": True,
            "requires_admin_review": True,
            "eligible_player_owned_categories": [
                "player_actor_profiles",
                "player_journal_entries",
                "in_world_notifications",
                "player_intervention_records",
            ],
            "shared_record_categories": [
                "conversation_sessions",
                "conversation_turns",
                "world_events",
                "media_assets",
                "provider_integrations",
            ],
        }
        model = PlayerPrivacyRequest(
            world_id=world_id,
            worldline_id=resolved_worldline_id,
            user_id=user_id,
            request_kind=PlayerPrivacyRequestKind.DELETE.value,
            status=PlayerPrivacyRequestStatus.REQUESTED.value,
            target_ref_kind=request.target_ref_kind.value,
            target_ref_id=request.target_ref_id,
            reason=request.reason,
            summary_json=_sanitize_json(summary),
            redaction_plan_json=_sanitize_json(redaction_plan),
            created_by_actor_ref=actor_ref or _actor_ref(user_id),
            metadata_json={"phase": "v0.8.6"},
        )
        self._session.add(model)
        self._session.flush()
        return self._request_read(model)

    def review_request(
        self,
        world_id: uuid.UUID,
        request_id: uuid.UUID,
        review: PlayerPrivacyRequestReview,
        *,
        actor_ref: str,
    ) -> PlayerPrivacyRequestRead:
        _validate_safe_text(review.review_note, "review_note")
        request = self._session.get(PlayerPrivacyRequest, request_id)
        if request is None or request.world_id != world_id:
            raise PlayerPrivacyNotFoundError("privacy request not found")
        if (
            request.request_kind == PlayerPrivacyRequestKind.DELETE.value
            and review.status == PlayerPrivacyRequestStatus.COMPLETED
        ):
            raise PlayerPrivacyValidationError(
                "delete requests cannot be completed automatically in Phase 6",
            )
        request.status = review.status.value
        request.review_note = review.review_note
        request.reviewed_by_actor_ref = actor_ref
        request.reviewed_at = datetime.now(UTC)
        self._session.flush()
        return self._request_read(request)

    def _build_export_payload(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> PlayerPrivacyExport:
        user = self._session.get(User, user_id)
        if user is None:
            raise PlayerPrivacyNotFoundError("user not found")
        role = self._session.scalars(
            select(WorldMembership.role).where(
                WorldMembership.world_id == world_id,
                WorldMembership.user_id == user_id,
            )
        ).one_or_none()
        actors = self._session.scalars(
            select(PlayerActorProfile)
            .where(
                PlayerActorProfile.world_id == world_id,
                PlayerActorProfile.worldline_id == worldline_id,
                PlayerActorProfile.user_id == user_id,
            )
            .order_by(PlayerActorProfile.created_at)
        ).all()
        choices = self._session.scalars(
            select(PlayerChoiceRecord)
            .where(
                PlayerChoiceRecord.world_id == world_id,
                PlayerChoiceRecord.worldline_id == worldline_id,
                PlayerChoiceRecord.user_id == user_id,
            )
            .order_by(PlayerChoiceRecord.created_at.desc())
        ).all()
        journal = self._session.scalars(
            select(PlayerJournalEntry)
            .where(
                PlayerJournalEntry.world_id == world_id,
                PlayerJournalEntry.worldline_id == worldline_id,
                PlayerJournalEntry.user_id == user_id,
            )
            .order_by(PlayerJournalEntry.created_at.desc())
        ).all()
        notifications = self._session.scalars(
            select(InWorldNotification)
            .where(
                InWorldNotification.world_id == world_id,
                InWorldNotification.worldline_id == worldline_id,
                InWorldNotification.user_id == user_id,
            )
            .order_by(InWorldNotification.created_at.desc())
        ).all()
        interventions = self._session.scalars(
            select(PlayerInterventionRecord)
            .where(
                PlayerInterventionRecord.world_id == world_id,
                PlayerInterventionRecord.worldline_id == worldline_id,
                PlayerInterventionRecord.user_id == user_id,
            )
            .order_by(PlayerInterventionRecord.created_at.desc())
        ).all()
        conversations = self._session.scalars(
            select(ConversationSession)
            .where(
                ConversationSession.world_id == world_id,
                ConversationSession.worldline_id == worldline_id,
            )
            .order_by(ConversationSession.created_at.desc())
        ).all()
        counts = {
            "player_actors": len(actors),
            "choices": len(choices),
            "journal_entries": len(journal),
            "notifications": len(notifications),
            "interventions": len(interventions),
            "conversation_references": len(conversations),
        }
        return PlayerPrivacyExport(
            request_id=None,
            world_id=world_id,
            worldline_id=worldline_id,
            user_id=user_id,
            generated_at=datetime.now(UTC),
            profile=PlayerPrivacyProfile(
                user_id=user.id,
                email=user.email,
                display_name=user.display_name,
                world_role=role,
            ),
            counts=counts,
            player_actors=tuple(
                PlayerPrivacyActorExport(
                    id=actor.id,
                    worldline_id=actor.worldline_id,
                    display_name=actor.display_name,
                    current_scene_id=actor.current_scene_id,
                    profile=_sanitize_json(actor.profile_json),
                    is_active=actor.is_active,
                    created_at=actor.created_at,
                    updated_at=actor.updated_at,
                )
                for actor in actors
            ),
            choices=tuple(
                PlayerPrivacyChoiceExport(
                    id=choice.id,
                    worldline_id=choice.worldline_id,
                    player_actor_id=choice.player_actor_id,
                    choice_key=choice.choice_key,
                    choice_kind=choice.choice_kind,
                    selected_option=_safe_text(choice.selected_option),
                    applied_event_id=None,
                    created_at=choice.created_at,
                    updated_at=choice.updated_at,
                )
                for choice in choices
            ),
            journal_entries=tuple(
                PlayerPrivacyJournalExport(
                    id=entry.id,
                    worldline_id=entry.worldline_id,
                    player_actor_id=entry.player_actor_id,
                    entry_kind=entry.entry_kind,
                    title=_safe_text(entry.title),
                    body=_safe_text(entry.body),
                    source_ref=None,
                    visibility=entry.visibility,
                    created_at=entry.created_at,
                    updated_at=entry.updated_at,
                )
                for entry in journal
            ),
            notifications=tuple(
                PlayerPrivacyNotificationExport(
                    id=notification.id,
                    worldline_id=notification.worldline_id,
                    notification_kind=notification.notification_kind,
                    title=_safe_text(notification.title),
                    body=_safe_text(notification.body),
                    source_ref=None,
                    status=notification.status,
                    created_at=notification.created_at,
                    updated_at=notification.updated_at,
                )
                for notification in notifications
            ),
            interventions=tuple(
                PlayerPrivacyInterventionExport(
                    id=intervention.id,
                    worldline_id=intervention.worldline_id,
                    player_actor_id=intervention.player_actor_id,
                    intervention_kind=intervention.intervention_kind,
                    target_agent_id=intervention.target_agent_id,
                    target_scene_id=intervention.target_scene_id,
                    choice_id=None,
                    event_id=None,
                    status=intervention.status,
                    created_at=intervention.created_at,
                    updated_at=intervention.updated_at,
                )
                for intervention in interventions
            ),
            conversation_references=tuple(
                PlayerPrivacyConversationReference(
                    id=conversation.id,
                    worldline_id=conversation.worldline_id,
                    session_key=conversation.session_key,
                    title=_safe_text(conversation.title),
                    scope_type=conversation.scope_type,
                    mode=conversation.mode,
                    status=conversation.status,
                    scene_id=conversation.scene_id,
                    created_at=conversation.created_at,
                    updated_at=conversation.updated_at,
                )
                for conversation in conversations
                if conversation.worldline_id is not None
            ),
            safeguards=(
                "raw prompts and raw outputs are excluded",
                "storage paths, encoded data, and resolved credentials are excluded",
                "shared canonical world history is not deleted by privacy workflows",
            ),
        )

    def _resolve_worldline_id(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
    ) -> uuid.UUID:
        if worldline_id is not None:
            worldline = self._session.get(Worldline, worldline_id)
            if worldline is None or worldline.world_id != world_id:
                raise PlayerPrivacyNotFoundError("worldline not found")
            return worldline.id
        worldline = self._session.scalars(
            select(Worldline)
            .where(Worldline.world_id == world_id)
            .order_by(Worldline.parent_worldline_id.is_not(None), Worldline.created_at)
        ).first()
        if worldline is None:
            raise PlayerPrivacyNotFoundError("worldline not found")
        return worldline.id

    def _request_read(self, request: PlayerPrivacyRequest) -> PlayerPrivacyRequestRead:
        return PlayerPrivacyRequestRead(
            id=request.id,
            world_id=request.world_id,
            worldline_id=request.worldline_id,
            user_id=request.user_id,
            request_kind=PlayerPrivacyRequestKind(request.request_kind),
            status=PlayerPrivacyRequestStatus(request.status),
            target_ref_kind=request.target_ref_kind,
            target_ref_id=request.target_ref_id,
            reason=request.reason,
            summary=_sanitize_json(request.summary_json),
            redaction_plan=_sanitize_json(request.redaction_plan_json),
            created_by_actor_ref=request.created_by_actor_ref,
            reviewed_by_actor_ref=request.reviewed_by_actor_ref,
            reviewed_at=request.reviewed_at,
            review_note=request.review_note,
            metadata=_sanitize_json(request.metadata_json),
            created_at=request.created_at,
            updated_at=request.updated_at,
        )


def _actor_ref(user_id: uuid.UUID) -> str:
    return f"user:{user_id}"


def _validate_safe_text(value: str | None, field_name: str) -> None:
    if value is not None and _LEAK_PATTERN.search(value):
        raise PlayerPrivacyValidationError(f"{field_name} contains sensitive data")


def _sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_leaky_key(key_text):
                sanitized[f"redacted_{len(sanitized) + 1}"] = _REDACTED
            else:
                sanitized[key_text] = _sanitize_json(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, str):
        return _safe_text(value)
    return value


def _is_leaky_key(key: str) -> bool:
    return key.strip().lower() in _LEAKY_KEYS


def _safe_text(value: str) -> str:
    if _LEAK_PATTERN.search(value):
        return _REDACTED
    return value
