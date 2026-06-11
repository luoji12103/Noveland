from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
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


class SpeechMediaJobResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    conversation_id: uuid.UUID | None
    turn_id: uuid.UUID | None
    agent_id: uuid.UUID | None
    job_kind: str
    status: str
    priority: int
    provider_kind: str | None
    source_event_id: uuid.UUID | None
    source_invocation_id: uuid.UUID | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SpeechMediaAssetResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    asset_kind: str
    asset_role: str
    source_kind: str
    status: str
    visibility: str
    mime_type: str | None
    file_ext: str | None
    size_bytes: int | None
    checksum_sha256: str | None
    width: int | None
    height: int | None
    duration_ms: int | None
    sample_rate_hz: int | None
    audio_channels: int | None
    has_alpha: bool | None
    color_mode: str | None
    provider_kind: str | None
    source_job_id: uuid.UUID | None
    source_event_id: uuid.UUID | None
    source_invocation_id: uuid.UUID | None
    title: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class SpeechMediaObjectResponse(BaseModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    object_role: str
    filename: str | None
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    width: int | None
    height: int | None
    duration_ms: int | None
    sample_rate_hz: int | None
    audio_channels: int | None
    frame_rate: float | None
    created_at: datetime


class SpeechInvocationResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    trace_id: uuid.UUID
    parent_invocation_id: uuid.UUID | None
    invocation_kind: str
    actor_kind: str
    agent_id: uuid.UUID | None
    conversation_id: uuid.UUID | None
    turn_id: uuid.UUID | None
    world_event_id: uuid.UUID | None
    media_job_id: uuid.UUID | None
    media_asset_id: uuid.UUID | None
    memory_write_job_id: uuid.UUID | None
    provider_kind: str
    model_name: str | None
    model_version: str | None
    prompt_template_key: str | None
    prompt_template_version: int | None
    usage_json: dict[str, Any] | None
    latency_ms: int | None
    estimated_cost: Decimal | None
    status: str
    visibility: str
    redaction_status: str
    retention_policy: str
    contains_sensitive_context: bool
    purge_after: datetime | None
    created_at: datetime
    updated_at: datetime


class SafeTTSResult(BaseModel):
    media_job: SpeechMediaJobResponse
    output_asset: SpeechMediaAssetResponse
    output_objects: list[SpeechMediaObjectResponse]
    model_invocation: SpeechInvocationResponse
    model_invocation_id: uuid.UUID


class SafeSTTResult(BaseModel):
    media_job: SpeechMediaJobResponse
    transcript: SpeechTranscriptRead
    model_invocation: SpeechInvocationResponse
    model_invocation_id: uuid.UUID


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
    response_model=SafeTTSResult,
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
) -> SafeTTSResult:
    try:
        result = SpeechService(db_session, storage).text_to_speech(
            world_id,
            request,
            actor_ref=_actor_ref(subject),
        )
        return _safe_tts_result(result)
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
    response_model=SafeSTTResult,
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
) -> SafeSTTResult:
    try:
        result = SpeechService(db_session, storage).speech_to_text(
            world_id,
            request,
            actor_ref=_actor_ref(subject),
        )
        return _safe_stt_result(result)
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


def _safe_tts_result(result: TTSResult) -> SafeTTSResult:
    return SafeTTSResult(
        media_job=_safe_media_job(result.media_job),
        output_asset=_safe_media_asset(result.output_asset),
        output_objects=[_safe_media_object(item) for item in result.output_objects],
        model_invocation=_safe_invocation(result.model_invocation),
        model_invocation_id=result.model_invocation_id,
    )


def _safe_stt_result(result: STTResult) -> SafeSTTResult:
    return SafeSTTResult(
        media_job=_safe_media_job(result.media_job),
        transcript=result.transcript,
        model_invocation=_safe_invocation(result.model_invocation),
        model_invocation_id=result.model_invocation_id,
    )


def _safe_media_job(job: Any) -> SpeechMediaJobResponse:
    return SpeechMediaJobResponse(
        id=job.id,
        world_id=job.world_id,
        worldline_id=job.worldline_id,
        conversation_id=job.conversation_id,
        turn_id=job.turn_id,
        agent_id=job.agent_id,
        job_kind=_enum_value(job.job_kind),
        status=_enum_value(job.status),
        priority=job.priority,
        provider_kind=job.provider_kind,
        source_event_id=job.source_event_id,
        source_invocation_id=job.source_invocation_id,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _safe_media_asset(asset: Any) -> SpeechMediaAssetResponse:
    return SpeechMediaAssetResponse(
        id=asset.id,
        world_id=asset.world_id,
        worldline_id=asset.worldline_id,
        asset_kind=_enum_value(asset.asset_kind),
        asset_role=_enum_value(asset.asset_role),
        source_kind=_enum_value(asset.source_kind),
        status=_enum_value(asset.status),
        visibility=_enum_value(asset.visibility),
        mime_type=asset.mime_type,
        file_ext=asset.file_ext,
        size_bytes=asset.size_bytes,
        checksum_sha256=asset.checksum_sha256,
        width=asset.width,
        height=asset.height,
        duration_ms=asset.duration_ms,
        sample_rate_hz=asset.sample_rate_hz,
        audio_channels=asset.audio_channels,
        has_alpha=asset.has_alpha,
        color_mode=asset.color_mode,
        provider_kind=asset.provider_kind,
        source_job_id=asset.source_job_id,
        source_event_id=asset.source_event_id,
        source_invocation_id=asset.source_invocation_id,
        title=asset.title,
        description=asset.description,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def _safe_media_object(media_object: Any) -> SpeechMediaObjectResponse:
    return SpeechMediaObjectResponse(
        id=media_object.id,
        asset_id=media_object.asset_id,
        world_id=media_object.world_id,
        worldline_id=media_object.worldline_id,
        object_role=_enum_value(media_object.object_role),
        filename=media_object.filename,
        mime_type=media_object.mime_type,
        size_bytes=media_object.size_bytes,
        checksum_sha256=media_object.checksum_sha256,
        width=media_object.width,
        height=media_object.height,
        duration_ms=media_object.duration_ms,
        sample_rate_hz=media_object.sample_rate_hz,
        audio_channels=media_object.audio_channels,
        frame_rate=media_object.frame_rate,
        created_at=media_object.created_at,
    )


def _safe_invocation(invocation: Any) -> SpeechInvocationResponse:
    return SpeechInvocationResponse(
        id=invocation.id,
        world_id=invocation.world_id,
        worldline_id=invocation.worldline_id,
        trace_id=invocation.trace_id,
        parent_invocation_id=invocation.parent_invocation_id,
        invocation_kind=_enum_value(invocation.invocation_kind),
        actor_kind=_enum_value(invocation.actor_kind),
        agent_id=invocation.agent_id,
        conversation_id=invocation.conversation_id,
        turn_id=invocation.turn_id,
        world_event_id=invocation.world_event_id,
        media_job_id=invocation.media_job_id,
        media_asset_id=invocation.media_asset_id,
        memory_write_job_id=invocation.memory_write_job_id,
        provider_kind=_enum_value(invocation.provider_kind),
        model_name=invocation.model_name,
        model_version=invocation.model_version,
        prompt_template_key=invocation.prompt_template_key,
        prompt_template_version=invocation.prompt_template_version,
        usage_json=invocation.usage_json,
        latency_ms=invocation.latency_ms,
        estimated_cost=invocation.estimated_cost,
        status=_enum_value(invocation.status),
        visibility=_enum_value(invocation.visibility),
        redaction_status=_enum_value(invocation.redaction_status),
        retention_policy=_enum_value(invocation.retention_policy),
        contains_sensitive_context=invocation.contains_sensitive_context,
        purge_after=invocation.purge_after,
        created_at=invocation.created_at,
        updated_at=invocation.updated_at,
    )


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value



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
