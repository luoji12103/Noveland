from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from noveland.auth import AuthenticatedSubject
from noveland.core.settings import load_settings
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
)
from noveland.speech.contracts import (
    AgentVoiceProfileBindingCreate,
    AgentVoiceProfileBindingRead,
    SpeechStyleMappingCreate,
    SpeechStyleMappingRead,
    SpeechStyleMappingUpdate,
    SpeechTranscriptRead,
    STTRequest,
    STTResult,
    TTSRequest,
    TTSResult,
    VoiceProfileCreate,
    VoiceProfileRead,
    VoiceProfileUpdate,
)
from noveland.speech.service import SpeechService
from noveland.speech.style_mapping import SpeechStyleMappingService
from noveland.speech.transcripts import SpeechTranscriptService
from noveland.speech.voice_profiles import (
    SpeechNotFoundError,
    SpeechValidationError,
    VoiceProfileService,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/speech", tags=["speech"])
agent_voice_router = APIRouter(
    prefix="/worlds/{world_id}/agents/{agent_id}/voice-profiles",
    tags=["speech"],
)
RESTRICTED_VISIBILITIES = {"developer_only", "hidden"}


def _speech_storage() -> LocalMediaObjectStorage:
    return LocalMediaObjectStorage(load_settings().object_storage_root / "media")


class VoiceProfileCreateRequest(BaseModel):
    worldline_id: uuid.UUID | None = None
    profile_key: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: str = "active"
    visibility: str = "world_admin"
    owner_kind: str = "world"
    owner_agent_id: uuid.UUID | None = None
    provider_integration_id: uuid.UUID | None = None
    provider_voice_id: str | None = Field(default=None, min_length=1, max_length=200)
    default_language: str | None = Field(default=None, min_length=1, max_length=40)
    supported_languages: list[str] = Field(default_factory=list)
    voice_kind: str = "preset"
    reference_asset_id: uuid.UUID | None = None
    consent_status: str = "not_required"
    usage_policy_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AgentVoiceProfileBindingCreateRequest(BaseModel):
    worldline_id: uuid.UUID | None = None
    voice_profile_id: uuid.UUID
    binding_role: str = "default"
    priority: int = Field(default=100, ge=0)
    is_default: bool = False
    style_overrides_json: dict[str, Any] = Field(default_factory=dict)


class SpeechStyleMappingCreateRequest(BaseModel):
    mapping_key: str = Field(min_length=1, max_length=120)
    provider_kind: str = Field(min_length=1, max_length=80)
    emotion_key: str = Field(min_length=1, max_length=80)
    style_json: dict[str, Any] = Field(default_factory=dict)


@router.get("/voice-profiles", response_model=list[VoiceProfileRead])
def list_voice_profiles(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
) -> list[VoiceProfileRead]:
    profiles = VoiceProfileService(db_session).list_profiles(world_id, worldline_id=worldline_id)
    if context.is_platform_admin:
        return profiles
    return [
        profile
        for profile in profiles
        if profile.visibility.value not in RESTRICTED_VISIBILITIES
    ]


@router.post(
    "/voice-profiles",
    response_model=VoiceProfileRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_voice_profile(
    world_id: uuid.UUID,
    request: VoiceProfileCreateRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VoiceProfileRead:
    if request.visibility in RESTRICTED_VISIBILITIES and not context.is_platform_admin:
        raise _forbidden()
    try:
        return VoiceProfileService(db_session).create_profile(
            VoiceProfileCreate(world_id=world_id, **request.model_dump())
        )
    except (SpeechValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/voice-profiles/{voice_profile_id}", response_model=VoiceProfileRead)
def get_voice_profile(
    world_id: uuid.UUID,
    voice_profile_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VoiceProfileRead:
    profile = VoiceProfileService(db_session).get_profile(world_id, voice_profile_id)
    if profile is None or (
        profile.visibility.value in RESTRICTED_VISIBILITIES and not context.is_platform_admin
    ):
        raise _not_found()
    return profile


@router.patch(
    "/voice-profiles/{voice_profile_id}",
    response_model=VoiceProfileRead,
    dependencies=[Depends(require_csrf)],
)
def update_voice_profile(
    world_id: uuid.UUID,
    voice_profile_id: uuid.UUID,
    request: VoiceProfileUpdate,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VoiceProfileRead:
    if (
        request.visibility is not None
        and request.visibility.value in RESTRICTED_VISIBILITIES
        and not context.is_platform_admin
    ):
        raise _forbidden()
    try:
        return VoiceProfileService(db_session).update_profile(world_id, voice_profile_id, request)
    except SpeechNotFoundError as exc:
        raise _not_found() from exc
    except (SpeechValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.delete(
    "/voice-profiles/{voice_profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_voice_profile(
    world_id: uuid.UUID,
    voice_profile_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        VoiceProfileService(db_session).delete_profile(world_id, voice_profile_id)
    except SpeechNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@agent_voice_router.get("", response_model=list[AgentVoiceProfileBindingRead])
def list_agent_voice_profiles(
    world_id: uuid.UUID,
    agent_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
) -> list[AgentVoiceProfileBindingRead]:
    return VoiceProfileService(db_session).list_agent_bindings(
        world_id,
        agent_id,
        worldline_id=worldline_id,
    )


@agent_voice_router.post(
    "",
    response_model=AgentVoiceProfileBindingRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def bind_agent_voice_profile(
    world_id: uuid.UUID,
    agent_id: uuid.UUID,
    request: AgentVoiceProfileBindingCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AgentVoiceProfileBindingRead:
    try:
        return VoiceProfileService(db_session).bind_agent_voice(
            AgentVoiceProfileBindingCreate(
                world_id=world_id,
                agent_id=agent_id,
                **request.model_dump(),
            )
        )
    except (SpeechValidationError, SpeechNotFoundError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@agent_voice_router.delete(
    "/{binding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_agent_voice_profile_binding(
    world_id: uuid.UUID,
    agent_id: uuid.UUID,
    binding_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        VoiceProfileService(db_session).delete_agent_binding(world_id, agent_id, binding_id)
    except SpeechNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/tts",
    response_model=TTSResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def text_to_speech(
    world_id: uuid.UUID,
    request: TTSRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_speech_storage)],
) -> TTSResult:
    try:
        return SpeechService(db_session, storage).text_to_speech(
            world_id,
            request,
            actor_ref=_actor_ref(subject),
        )
    except (
        ProviderNotFoundError,
        ProviderValidationError,
        ProviderExecutionError,
        SpeechValidationError,
        SpeechNotFoundError,
        ValueError,
    ) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/stt",
    response_model=STTResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def speech_to_text(
    world_id: uuid.UUID,
    request: STTRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_speech_storage)],
) -> STTResult:
    try:
        return SpeechService(db_session, storage).speech_to_text(
            world_id,
            request,
            actor_ref=_actor_ref(subject),
        )
    except (
        ProviderValidationError,
        ProviderExecutionError,
        SpeechValidationError,
        SpeechNotFoundError,
        ValueError,
    ) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/transcripts", response_model=list[SpeechTranscriptRead])
def list_transcripts(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    source_asset_id: uuid.UUID | None = None,
) -> list[SpeechTranscriptRead]:
    return SpeechTranscriptService(db_session).list_transcripts(
        world_id,
        worldline_id=worldline_id,
        source_asset_id=source_asset_id,
    )


@router.get("/transcripts/{transcript_id}", response_model=SpeechTranscriptRead)
def get_transcript(
    world_id: uuid.UUID,
    transcript_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SpeechTranscriptRead:
    transcript = SpeechTranscriptService(db_session).get_transcript(world_id, transcript_id)
    if transcript is None:
        raise _not_found()
    return transcript


@router.get("/style-mappings", response_model=list[SpeechStyleMappingRead])
def list_style_mappings(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    provider_kind: str | None = None,
    emotion_key: str | None = None,
) -> list[SpeechStyleMappingRead]:
    return SpeechStyleMappingService(db_session).list_mappings(
        world_id,
        provider_kind=provider_kind,
        emotion_key=emotion_key,
    )


@router.post(
    "/style-mappings",
    response_model=SpeechStyleMappingRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_style_mapping(
    world_id: uuid.UUID,
    request: SpeechStyleMappingCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SpeechStyleMappingRead:
    try:
        return SpeechStyleMappingService(db_session).create_mapping(
            SpeechStyleMappingCreate(world_id=world_id, **request.model_dump())
        )
    except (SpeechValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.patch(
    "/style-mappings/{mapping_id}",
    response_model=SpeechStyleMappingRead,
    dependencies=[Depends(require_csrf)],
)
def update_style_mapping(
    world_id: uuid.UUID,
    mapping_id: uuid.UUID,
    request: SpeechStyleMappingUpdate,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SpeechStyleMappingRead:
    try:
        return SpeechStyleMappingService(db_session).update_mapping(world_id, mapping_id, request)
    except SpeechNotFoundError as exc:
        raise _not_found() from exc
    except (SpeechValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.delete(
    "/style-mappings/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_style_mapping(
    world_id: uuid.UUID,
    mapping_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    try:
        SpeechStyleMappingService(db_session).delete_mapping(world_id, mapping_id)
    except SpeechNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _actor_ref(subject: AuthenticatedSubject) -> str:
    if is_platform_admin(subject):
        return "platform_admin"
    return f"world_admin:{subject.user_id}"


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
