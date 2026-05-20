from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.media.contracts import (
    MediaAssetKind,
    MediaJobCreate,
    MediaJobKind,
    MediaJobRecord,
    MediaJobStatus,
    MediaJobUpdate,
    MediaReferenceCreate,
    MediaReferenceKind,
    MediaReferenceRole,
)
from noveland.media.models import MediaObject
from noveland.media.service import MediaJobService, MediaReferenceService, MediaService
from noveland.media.storage import MediaObjectStorage
from noveland.providers.contracts import (
    ProviderCapabilityRead,
    ProviderExecutionRequest,
    ProviderIntegrationRead,
    ProviderKind,
)
from noveland.providers.registry import ProviderRegistryService, ProviderValidationError
from noveland.providers.service import ProviderExecutionService
from noveland.speech.contracts import (
    SpeechTranscriptCreate,
    STTRequest,
    STTResult,
    TTSRequest,
    TTSResult,
    VoiceProfileRead,
)
from noveland.speech.style_mapping import SpeechStyleMappingService
from noveland.speech.transcripts import SpeechTranscriptService
from noveland.speech.voice_profiles import (
    SpeechValidationError,
    VoiceProfileService,
)
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy.orm import Session


class SpeechService:
    def __init__(self, session: Session, storage: MediaObjectStorage) -> None:
        self._session = session
        self._storage = storage

    def text_to_speech(
        self,
        world_id: uuid.UUID,
        request: TTSRequest,
        *,
        actor_ref: str,
    ) -> TTSResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        provider = self._provider_required(world_id, request.provider_id)
        self._require_capability(world_id, request.provider_id, "supports_tts")
        voice_profile, binding_overrides = self._resolve_voice_profile(
            world_id,
            worldline_id,
            request,
        )
        style_json = self._style_json(
            world_id,
            provider.adapter_kind.value,
            provider.provider_kind.value,
            request,
        )
        if binding_overrides:
            style_json.update(binding_overrides)
        style_json.update(request.style_overrides_json)
        self._validate_turn_refs(world_id, worldline_id, request.conversation_id, request.turn_id)
        job = self._tts_job(
            world_id,
            worldline_id,
            request,
            provider_id=request.provider_id,
            actor_ref=actor_ref,
        )
        result = ProviderExecutionService(self._session, self._storage).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=request.provider_id,
                provider_kind=ProviderKind.TEXT_TO_SPEECH,
                capability_key="speech.tts",
                input_text=request.text,
                request_json={
                    "operation": "tts",
                    "text": request.text,
                    "language": request.language,
                    "emotion": request.emotion,
                    "intensity": request.intensity,
                    "style_json": style_json,
                    "output_format": request.output_format,
                    "voice_profile_id": None if voice_profile is None else str(voice_profile.id),
                    "provider_voice_id": (
                        None if voice_profile is None else voice_profile.provider_voice_id
                    ),
                    "asset_role": "speech_audio",
                    "metadata": {"conversation_id": _str_or_none(request.conversation_id)},
                },
                media_job_id=job.id,
                player_actor_id=request.player_actor_id,
                actor_ref=actor_ref,
            )
        )
        if result.media_job is None or result.output_asset is None:
            raise SpeechValidationError("TTS provider did not return audio media")
        if request.turn_id is not None:
            MediaReferenceService(self._session).create_reference(
                MediaReferenceCreate(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    asset_id=result.output_asset.id,
                    ref_kind=MediaReferenceKind.CONVERSATION_TURN,
                    ref_id=request.turn_id,
                    ref_role=MediaReferenceRole.OUTPUT,
                    metadata={"source": "tts"},
                )
            )
        return TTSResult(
            media_job=result.media_job,
            output_asset=result.output_asset,
            output_objects=result.output_objects,
            model_invocation=result.invocation,
            model_invocation_id=result.invocation.id,
        )

    def speech_to_text(
        self,
        world_id: uuid.UUID,
        request: STTRequest,
        *,
        actor_ref: str,
    ) -> STTResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        provider = self._provider_required(world_id, request.provider_id)
        self._require_capability(world_id, request.provider_id, "supports_stt")
        self._validate_turn_refs(world_id, worldline_id, request.conversation_id, request.turn_id)
        self._source_audio_required(world_id, worldline_id, request.source_asset_id)
        job = MediaJobService(self._session).create_job(
            MediaJobCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                conversation_id=request.conversation_id,
                turn_id=request.turn_id,
                job_kind=MediaJobKind.SPEECH_TRANSCRIPTION,
                provider_kind=provider.provider_kind.value,
                provider_config_json={"provider_id": str(request.provider_id)},
                request_json={
                    "source_asset_id": str(request.source_asset_id),
                    "language": request.language,
                    "diarization": request.diarization,
                    "timestamps": request.timestamps,
                },
            ),
            actor_ref=actor_ref,
        )
        result = ProviderExecutionService(self._session, self._storage).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=request.provider_id,
                provider_kind=ProviderKind.SPEECH_TO_TEXT,
                capability_key="speech.asr",
                request_json={
                    "operation": "stt",
                    "source_asset_id": str(request.source_asset_id),
                    "input_asset_ids": [str(request.source_asset_id)],
                    "language": request.language,
                    "diarization": request.diarization,
                    "timestamps": request.timestamps,
                },
                media_job_id=job.id,
                media_asset_id=request.source_asset_id,
                player_actor_id=request.player_actor_id,
                actor_ref=actor_ref,
            )
        )
        transcript = SpeechTranscriptService(self._session).create_transcript(
            SpeechTranscriptCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                source_asset_id=request.source_asset_id,
                media_job_id=job.id,
                model_invocation_id=result.invocation.id,
                conversation_id=request.conversation_id,
                turn_id=request.turn_id,
                speaker_actor_ref=request.speaker_actor_ref,
                language=request.language,
                transcript_text=result.output_text or "",
                segments_json=_segments(result.output_json),
                confidence_json=_confidence(result.output_json),
            )
        )
        if request.turn_id is not None:
            MediaReferenceService(self._session).create_reference(
                MediaReferenceCreate(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    asset_id=request.source_asset_id,
                    ref_kind=MediaReferenceKind.CONVERSATION_TURN,
                    ref_id=request.turn_id,
                    ref_role=MediaReferenceRole.INPUT,
                    metadata={"source": "stt", "transcript_id": str(transcript.id)},
                )
            )
        MediaJobService(self._session).update_job(
            world_id,
            job.id,
            MediaJobUpdate(
                status=MediaJobStatus.SUCCEEDED,
                result_json={"transcript_id": str(transcript.id)},
                finished_at=datetime.now(UTC),
            ),
        )
        updated_job = MediaJobService(self._session).get_job(
            world_id,
            job.id,
            worldline_id=worldline_id,
        )
        return STTResult(
            media_job=updated_job or job,
            transcript=transcript,
            model_invocation=result.invocation,
            model_invocation_id=result.invocation.id,
        )

    def _resolve_voice_profile(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        request: TTSRequest,
    ) -> tuple[VoiceProfileRead | None, dict[str, object]]:
        voice_service = VoiceProfileService(self._session)
        if request.voice_profile_id is not None:
            profile = voice_service.get_profile(world_id, request.voice_profile_id)
            if profile is None:
                raise SpeechValidationError("voice profile not found")
            if profile.worldline_id is not None and profile.worldline_id != worldline_id:
                raise SpeechValidationError("voice profile must belong to request worldline")
            return profile, {}
        if request.agent_id is not None:
            profile, binding = voice_service.resolve_agent_default(
                world_id,
                request.agent_id,
                worldline_id,
            )
            return profile, {} if binding is None else dict(binding.style_overrides_json)
        return None, {}

    def _style_json(
        self,
        world_id: uuid.UUID,
        adapter_kind: str,
        provider_kind: str,
        request: TTSRequest,
    ) -> dict[str, object]:
        style = SpeechStyleMappingService(self._session).resolve_style(
            world_id,
            adapter_kind,
            request.emotion,
        )
        if not style and adapter_kind != provider_kind:
            style = SpeechStyleMappingService(self._session).resolve_style(
                world_id,
                provider_kind,
                request.emotion,
            )
        if request.emotion is not None and not style:
            style = {"emotion": request.emotion}
        if request.intensity is not None:
            style["intensity"] = request.intensity
        return style

    def _tts_job(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        request: TTSRequest,
        *,
        provider_id: uuid.UUID,
        actor_ref: str,
    ) -> MediaJobRecord:
        service = MediaJobService(self._session)
        if request.media_job_id is not None:
            existing = service.get_job(world_id, request.media_job_id, worldline_id=worldline_id)
            if existing is None:
                raise SpeechValidationError("media job must belong to TTS worldline")
            return existing
        return service.create_job(
            MediaJobCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                conversation_id=request.conversation_id,
                turn_id=request.turn_id,
                agent_id=request.agent_id,
                job_kind=MediaJobKind.SPEECH_GENERATION,
                provider_kind="text_to_speech",
                provider_config_json={"provider_id": str(provider_id)},
                request_json={
                    "text_hash": hashlib.sha256(request.text.encode("utf-8")).hexdigest(),
                    "language": request.language,
                    "emotion": request.emotion,
                    "output_format": request.output_format,
                },
            ),
            actor_ref=actor_ref,
        )

    def _provider_required(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
    ) -> ProviderIntegrationRead:
        provider = ProviderRegistryService(self._session).get_provider(
            world_id,
            provider_id,
            platform_admin=True,
            include_hidden=True,
        )
        if provider is None:
            raise ProviderValidationError("provider integration not found")
        return provider

    def _require_capability(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
        capability_key: str,
    ) -> None:
        capabilities = ProviderRegistryService(self._session).list_capabilities(
            world_id,
            provider_id,
            platform_admin=True,
        )
        if not _capability_true(capabilities, capability_key):
            raise SpeechValidationError(f"provider does not support {capability_key}")

    def _source_audio_required(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        asset_id: uuid.UUID,
    ) -> None:
        asset = MediaService(self._session, self._storage).get_asset_by_id(
            world_id,
            asset_id,
            include_deleted=False,
        )
        if (
            asset is None
            or asset.worldline_id != worldline_id
            or asset.asset_kind != MediaAssetKind.AUDIO
        ):
            raise SpeechValidationError("source asset must be an audio asset in request worldline")
        objects = self._session.query(MediaObject).filter(MediaObject.asset_id == asset_id).all()
        if not objects:
            raise SpeechValidationError("source audio asset must have media object")

    def _validate_turn_refs(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        turn_id: uuid.UUID | None,
    ) -> None:
        if conversation_id is not None:
            conversation = self._session.get(ConversationSession, conversation_id)
            if (
                conversation is None
                or conversation.world_id != world_id
                or conversation.worldline_id != worldline_id
            ):
                raise SpeechValidationError("conversation must belong to speech worldline")
        if turn_id is not None:
            turn = self._session.get(ConversationTurn, turn_id)
            if turn is None:
                raise SpeechValidationError("turn must belong to speech worldline")
            session_model = self._session.get(ConversationSession, turn.session_id)
            if (
                session_model is None
                or session_model.world_id != world_id
                or session_model.worldline_id != worldline_id
            ):
                raise SpeechValidationError("turn must belong to speech worldline")

    def _worldline_id(self, world_id: uuid.UUID, worldline_id: uuid.UUID | None) -> uuid.UUID:
        try:
            return worldline_or_404(self._session, world_id, worldline_id).id
        except ValueError as exc:
            raise SpeechValidationError("worldline not found") from exc


def _capability_true(capabilities: list[ProviderCapabilityRead], key: str) -> bool:
    for capability in capabilities:
        if capability.capability_key != key:
            continue
        return bool(capability.capability_json.get("value", True))
    return False


def _segments(output_json: dict[str, object]) -> list[dict[str, object]] | None:
    value = output_json.get("segments")
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return [dict(item) for item in value]
    return None


def _confidence(output_json: dict[str, object]) -> dict[str, object] | None:
    value = output_json.get("confidence")
    return dict(value) if isinstance(value, dict) else None


def _str_or_none(value: uuid.UUID | None) -> str | None:
    return None if value is None else str(value)
