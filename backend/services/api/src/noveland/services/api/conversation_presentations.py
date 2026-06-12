from __future__ import annotations

import re
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from noveland.auth import AuthenticatedSubject, AuthRole
from noveland.conversations import (
    ConversationPresentationService,
    ConversationTurnPresentationPatch,
    ConversationTurnPresentationRecord,
    ConversationTurnPresentationUpsert,
)
from noveland.conversations.errors import ConversationValidationError
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.core.settings import load_settings
from noveland.media.contracts import (
    MediaReferenceCreate,
    MediaReferenceKind,
    MediaReferenceRole,
)
from noveland.media.errors import MediaConflictError, MediaNotFoundError, MediaValidationError
from noveland.media.service import MediaReferenceService
from noveland.media.storage import LocalMediaObjectStorage
from noveland.providers.registry import ProviderNotFoundError, ProviderValidationError
from noveland.providers.service import ProviderExecutionError
from noveland.services.api.authorization import is_platform_admin
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_current_subject,
    get_db_session,
    get_world_admin_context,
    get_world_member_context,
)
from noveland.speech.contracts import STTRequest, TTSRequest
from noveland.speech.service import SpeechService
from noveland.speech.voice_profiles import SpeechNotFoundError, SpeechValidationError
from noveland.visual.composition import VisualCompositionService
from noveland.visual.contracts import (
    BackgroundResolveRequest,
    SceneComposeRequest,
    SceneLayer,
    SpriteResolveRequest,
)
from noveland.visual.resolver import VisualResolver
from noveland.visual.service import VisualNotFoundError, VisualValidationError
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation",
    tags=["conversation-presentations"],
)


class _RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PresentationUpsertRequest(_RequestModel):
    speaker_agent_id: uuid.UUID | None = None
    emotion_key: str | None = Field(default=None, min_length=1, max_length=80)
    emotion_intensity: float | None = Field(default=None, ge=0.0, le=2.0)
    sprite_set_id: uuid.UUID | None = None
    sprite_variant_id: uuid.UUID | None = None
    voice_profile_id: uuid.UUID | None = None
    tts_media_asset_id: uuid.UUID | None = None
    background_asset_id: uuid.UUID | None = None
    composite_scene_asset_id: uuid.UUID | None = None
    transcript_id: uuid.UUID | None = None
    presentation_json: dict[str, Any] = Field(default_factory=dict)
    render_state: str = "draft"


class PresentationPatchRequest(_RequestModel):
    speaker_agent_id: uuid.UUID | None = None
    emotion_key: str | None = Field(default=None, min_length=1, max_length=80)
    emotion_intensity: float | None = Field(default=None, ge=0.0, le=2.0)
    sprite_set_id: uuid.UUID | None = None
    sprite_variant_id: uuid.UUID | None = None
    voice_profile_id: uuid.UUID | None = None
    tts_media_asset_id: uuid.UUID | None = None
    background_asset_id: uuid.UUID | None = None
    composite_scene_asset_id: uuid.UUID | None = None
    transcript_id: uuid.UUID | None = None
    presentation_json: dict[str, Any] | None = None
    render_state: str | None = None


class RenderVisualRequest(_RequestModel):
    speaker_agent_id: uuid.UUID | None = None
    emotion_key: str | None = Field(default=None, min_length=1, max_length=80)
    emotion_intensity: float | None = Field(default=None, ge=0.0, le=2.0)
    pose_key: str | None = Field(default=None, min_length=1, max_length=80)
    outfit_key: str | None = Field(default=None, min_length=1, max_length=80)
    mood_tags: tuple[str, ...] = ()
    style_key: str | None = Field(default=None, min_length=1, max_length=120)
    scene_id: uuid.UUID | None = None
    location_key: str = Field(min_length=1, max_length=120)
    time_of_day: str | None = Field(default=None, min_length=1, max_length=40)
    weather_key: str | None = Field(default=None, min_length=1, max_length=80)
    sprite_x: int = 0
    sprite_y: int = 0
    sprite_width: int | None = Field(default=None, gt=0)
    sprite_height: int | None = Field(default=None, gt=0)
    sprite_opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    sprite_z_index: int = 10
    extra_layers: tuple[SceneLayer, ...] = ()
    presentation_json: dict[str, Any] = Field(default_factory=dict)


class RenderSpeechRequest(_RequestModel):
    provider_id: uuid.UUID
    voice_profile_id: uuid.UUID | None = None
    speaker_agent_id: uuid.UUID | None = None
    text: str | None = Field(default=None, min_length=1)
    language: str | None = Field(default=None, min_length=1, max_length=40)
    emotion_key: str | None = Field(default=None, min_length=1, max_length=80)
    emotion_intensity: float | None = Field(default=None, ge=0.0, le=2.0)
    style_overrides_json: dict[str, Any] = Field(default_factory=dict)
    output_format: str = Field(default="wav", min_length=1, max_length=20)
    allow_provider_default_voice: bool = False
    media_job_id: uuid.UUID | None = None
    presentation_json: dict[str, Any] = Field(default_factory=dict)


class TranscribeAudioRequest(_RequestModel):
    provider_id: uuid.UUID
    source_asset_id: uuid.UUID
    language: str | None = Field(default=None, min_length=1, max_length=40)
    diarization: bool = False
    timestamps: bool = False
    speaker_actor_ref: str | None = Field(default=None, min_length=1, max_length=160)
    presentation_json: dict[str, Any] = Field(default_factory=dict)


def _presentation_storage() -> LocalMediaObjectStorage:
    return LocalMediaObjectStorage(load_settings().object_storage_root / "media")


_MEMBER_PRESENTATION_SENSITIVE_KEYS = {
    "adapter_kind",
    "api_key",
    "apikey",
    "auth_ref",
    "auth_refs",
    "authorization",
    "base64",
    "bearer_token",
    "bytes",
    "client_secret",
    "compose_media_job_id",
    "file_path",
    "filepath",
    "filesystem_path",
    "invocation",
    "invocation_id",
    "local_path",
    "media_job",
    "media_job_id",
    "model_invocation",
    "model_invocation_id",
    "object_path",
    "password",
    "path",
    "private_key",
    "prompt_snapshot",
    "prompt_snapshot_id",
    "provider",
    "provider_id",
    "provider_key",
    "provider_kind",
    "raw_bytes",
    "raw_output",
    "raw_prompt",
    "resolved_secret",
    "secret",
    "secret_ref",
    "secret_refs",
    "source_asset_id",
    "source_media_job_id",
    "storage_uri",
    "token",
    "transcript_id",
    "tts_media_job_id",
    "voice_profile_id",
}
_MEMBER_PRESENTATION_SENSITIVE_VALUE_RE = re.compile(
    r"(media://|object://|file://|s3://|gs://|/root/|/tmp/|base64,|"
    r"BEGIN PRIVATE KEY|sk-[A-Za-z0-9]|bearer\s+|authorization|"
    r"raw[_ -]?prompt|raw[_ -]?output|prompt_snapshot|model_invocation|media_job|"
    r"storage_uri|provider[_ -]?(kind|key|id)?)",
    re.IGNORECASE,
)
_OMIT_MEMBER_PRESENTATION_VALUE = object()


def _presentation_response(
    record: ConversationTurnPresentationRecord,
    context: WorldAccessContext,
) -> ConversationTurnPresentationRecord:
    if _include_admin_presentation_fields(context):
        return record
    return record.model_copy(
        update={
            "sprite_set_id": None,
            "sprite_variant_id": None,
            "voice_profile_id": None,
            "transcript_id": None,
            "presentation_json": _sanitize_member_presentation_json(record.presentation_json),
        }
    )


def _include_admin_presentation_fields(context: WorldAccessContext) -> bool:
    return context.is_platform_admin or context.role == AuthRole.WORLD_ADMIN.value


def _sanitize_member_presentation_json(value: Any) -> dict[str, Any]:
    sanitized = _sanitize_member_presentation_json_value(value)
    return sanitized if isinstance(sanitized, dict) else {}


def _sanitize_member_presentation_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for raw_key, item in value.items():
            key = str(raw_key)
            if key.strip().lower() in _MEMBER_PRESENTATION_SENSITIVE_KEYS:
                continue
            clean_item = _sanitize_member_presentation_json_value(item)
            if clean_item is not _OMIT_MEMBER_PRESENTATION_VALUE:
                sanitized[key] = clean_item
        return sanitized
    if isinstance(value, list | tuple | set):
        sanitized_list: list[Any] = []
        for item in value:
            clean_item = _sanitize_member_presentation_json_value(item)
            if clean_item is not _OMIT_MEMBER_PRESENTATION_VALUE:
                sanitized_list.append(clean_item)
        return sanitized_list
    if isinstance(value, str) and _MEMBER_PRESENTATION_SENSITIVE_VALUE_RE.search(value):
        return _OMIT_MEMBER_PRESENTATION_VALUE
    return value


@router.get("", response_model=ConversationTurnPresentationRecord | None)
def get_presentation(
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationTurnPresentationRecord | None:
    try:
        record = ConversationPresentationService(db_session).get_presentation(
            world_id,
            conversation_id,
            turn_id,
        )
        return None if record is None else _presentation_response(record, context)
    except LookupError as exc:
        raise _not_found() from exc
    except ConversationValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.put(
    "",
    response_model=ConversationTurnPresentationRecord,
    dependencies=[Depends(require_csrf)],
)
def put_presentation(
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
    request: PresentationUpsertRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationTurnPresentationRecord:
    try:
        return ConversationPresentationService(db_session).put_presentation(
            world_id,
            conversation_id,
            turn_id,
            ConversationTurnPresentationUpsert(**request.model_dump()),
        )
    except LookupError as exc:
        raise _not_found() from exc
    except (ConversationValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.patch(
    "",
    response_model=ConversationTurnPresentationRecord,
    dependencies=[Depends(require_csrf)],
)
def patch_presentation(
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
    request: PresentationPatchRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationTurnPresentationRecord:
    try:
        return ConversationPresentationService(db_session).patch_presentation(
            world_id,
            conversation_id,
            turn_id,
            ConversationTurnPresentationPatch(**request.model_dump(exclude_unset=True)),
        )
    except LookupError as exc:
        raise _not_found() from exc
    except (ConversationValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/render-visual",
    response_model=ConversationTurnPresentationRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def render_visual(
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
    request: RenderVisualRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_presentation_storage)],
) -> ConversationTurnPresentationRecord:
    try:
        worldline_id, turn = _turn_context(db_session, world_id, conversation_id, turn_id)
        speaker_agent_id = _speaker_agent_id(request.speaker_agent_id, turn)
        if speaker_agent_id is None:
            raise ConversationValidationError("speaker agent is required to render visual")
        resolver = VisualResolver(db_session)
        sprite = resolver.resolve_sprite(
            world_id,
            SpriteResolveRequest(
                worldline_id=worldline_id,
                agent_id=speaker_agent_id,
                expression_key=request.emotion_key,
                pose_key=request.pose_key,
                outfit_key=request.outfit_key,
                mood_tags=request.mood_tags,
                style_key=request.style_key,
                include_restricted=context.is_platform_admin,
            ),
        )
        background = resolver.resolve_background(
            world_id,
            BackgroundResolveRequest(
                worldline_id=worldline_id,
                scene_id=request.scene_id,
                location_key=request.location_key,
                time_of_day=request.time_of_day,
                weather_key=request.weather_key,
                include_restricted=context.is_platform_admin,
            ),
        )
        compose = VisualCompositionService(db_session, storage).compose_scene(
            world_id,
            SceneComposeRequest(
                worldline_id=worldline_id,
                background_asset_id=background.asset.id,
                layers=(
                    SceneLayer(
                        asset_id=sprite.asset.id,
                        x=request.sprite_x,
                        y=request.sprite_y,
                        width=request.sprite_width,
                        height=request.sprite_height,
                        opacity=request.sprite_opacity,
                        z_index=request.sprite_z_index,
                    ),
                    *request.extra_layers,
                ),
                metadata_json={
                    "source": "conversation_turn_render_visual",
                    "conversation_id": str(conversation_id),
                    "turn_id": str(turn_id),
                },
            ),
            actor_ref=_actor_ref(subject),
        )
        _attach_turn_media(
            db_session,
            world_id,
            worldline_id,
            turn_id,
            sprite.asset.id,
            MediaReferenceRole.CHARACTER_SPRITE,
            {"source": "render_visual", "sprite_variant_id": str(sprite.variant.id)},
        )
        _attach_turn_media(
            db_session,
            world_id,
            worldline_id,
            turn_id,
            background.asset.id,
            MediaReferenceRole.BACKGROUND,
            {"source": "render_visual", "background_id": str(background.background.id)},
        )
        _attach_turn_media(
            db_session,
            world_id,
            worldline_id,
            turn_id,
            compose.output_asset.id,
            MediaReferenceRole.OUTPUT,
            {"source": "render_visual", "media_job_id": str(compose.media_job.id)},
        )
        return ConversationPresentationService(db_session).apply_visual_result(
            world_id,
            conversation_id,
            turn_id,
            speaker_agent_id=speaker_agent_id,
            emotion_key=request.emotion_key,
            emotion_intensity=request.emotion_intensity,
            sprite_set_id=sprite.sprite_set.id,
            sprite_variant_id=sprite.variant.id,
            background_asset_id=background.asset.id,
            composite_scene_asset_id=compose.output_asset.id,
            presentation_json={
                **request.presentation_json,
                "visual": {
                    "sprite_fallback_reason": sprite.fallback_reason,
                    "background_fallback_reason": background.fallback_reason,
                    "compose_media_job_id": str(compose.media_job.id),
                },
            },
        )
    except LookupError as exc:
        raise _not_found() from exc
    except (
        ConversationValidationError,
        MediaConflictError,
        MediaNotFoundError,
        MediaValidationError,
        VisualNotFoundError,
        VisualValidationError,
        ValueError,
    ) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/render-speech",
    response_model=ConversationTurnPresentationRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def render_speech(
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
    request: RenderSpeechRequest,
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_presentation_storage)],
) -> ConversationTurnPresentationRecord:
    try:
        worldline_id, turn = _turn_context(db_session, world_id, conversation_id, turn_id)
        speaker_agent_id = _speaker_agent_id(request.speaker_agent_id, turn)
        result = SpeechService(db_session, storage).text_to_speech(
            world_id,
            TTSRequest(
                worldline_id=worldline_id,
                provider_id=request.provider_id,
                voice_profile_id=request.voice_profile_id,
                agent_id=speaker_agent_id,
                allow_provider_default_voice=request.allow_provider_default_voice,
                text=request.text or turn.output_text or turn.input_text,
                language=request.language,
                emotion=request.emotion_key,
                intensity=request.emotion_intensity,
                style_overrides_json=request.style_overrides_json,
                output_format=request.output_format,
                conversation_id=conversation_id,
                turn_id=turn_id,
                media_job_id=request.media_job_id,
            ),
            actor_ref=_actor_ref(subject),
        )
        return ConversationPresentationService(db_session).apply_speech_result(
            world_id,
            conversation_id,
            turn_id,
            speaker_agent_id=speaker_agent_id,
            emotion_key=request.emotion_key,
            emotion_intensity=request.emotion_intensity,
            voice_profile_id=request.voice_profile_id,
            tts_media_asset_id=result.output_asset.id,
            presentation_json={
                **request.presentation_json,
                "speech": {
                    "tts_media_job_id": str(result.media_job.id),
                    "model_invocation_id": str(result.model_invocation_id),
                },
            },
        )
    except LookupError as exc:
        raise _not_found() from exc
    except (
        ConversationValidationError,
        ProviderNotFoundError,
        ProviderValidationError,
        ProviderExecutionError,
        SpeechNotFoundError,
        SpeechValidationError,
        ValueError,
    ) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/transcribe-audio",
    response_model=ConversationTurnPresentationRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def transcribe_audio(
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
    request: TranscribeAudioRequest,
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_presentation_storage)],
) -> ConversationTurnPresentationRecord:
    try:
        worldline_id, _turn = _turn_context(db_session, world_id, conversation_id, turn_id)
        result = SpeechService(db_session, storage).speech_to_text(
            world_id,
            STTRequest(
                worldline_id=worldline_id,
                provider_id=request.provider_id,
                source_asset_id=request.source_asset_id,
                language=request.language,
                diarization=request.diarization,
                timestamps=request.timestamps,
                conversation_id=conversation_id,
                turn_id=turn_id,
                speaker_actor_ref=request.speaker_actor_ref,
            ),
            actor_ref=_actor_ref(subject),
        )
        return ConversationPresentationService(db_session).apply_transcript_result(
            world_id,
            conversation_id,
            turn_id,
            transcript_id=result.transcript.id,
            source_asset_id=request.source_asset_id,
            presentation_json={
                **request.presentation_json,
                "stt": {
                    "media_job_id": str(result.media_job.id),
                    "model_invocation_id": str(result.model_invocation_id),
                },
            },
        )
    except LookupError as exc:
        raise _not_found() from exc
    except (
        ConversationValidationError,
        ProviderValidationError,
        ProviderExecutionError,
        SpeechNotFoundError,
        SpeechValidationError,
        ValueError,
    ) as exc:
        raise _unprocessable(str(exc)) from exc


def _turn_context(
    db_session: Session,
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
) -> tuple[uuid.UUID, ConversationTurn]:
    conversation = db_session.get(ConversationSession, conversation_id)
    if conversation is None or conversation.world_id != world_id:
        raise LookupError("Conversation session not found")
    if conversation.worldline_id is None:
        raise ConversationValidationError("conversation must have worldline_id")
    turn = db_session.get(ConversationTurn, turn_id)
    if turn is None or turn.session_id != conversation_id:
        raise LookupError("Conversation turn not found")
    return conversation.worldline_id, turn


def _speaker_agent_id(
    requested: uuid.UUID | None,
    turn: ConversationTurn,
) -> uuid.UUID | None:
    if turn.speaker_agent_id is not None:
        if requested is not None and requested != turn.speaker_agent_id:
            raise ConversationValidationError("speaker agent must match conversation turn")
        return turn.speaker_agent_id
    return requested


def _attach_turn_media(
    db_session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    turn_id: uuid.UUID,
    asset_id: uuid.UUID,
    role: MediaReferenceRole,
    metadata: dict[str, Any],
) -> None:
    try:
        MediaReferenceService(db_session).create_reference(
            MediaReferenceCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                asset_id=asset_id,
                ref_kind=MediaReferenceKind.CONVERSATION_TURN,
                ref_id=turn_id,
                ref_role=role,
                metadata=metadata,
            )
        )
    except MediaValidationError as exc:
        if "already exists" not in str(exc):
            raise


def _actor_ref(subject: AuthenticatedSubject) -> str:
    if is_platform_admin(subject):
        return "platform_admin"
    return f"world_admin:{subject.user_id}"


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
