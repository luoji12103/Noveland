from __future__ import annotations

import uuid

from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.invocations.models import ModelInvocation
from noveland.media.models import MediaAsset, MediaJob
from noveland.speech.contracts import (
    SpeechTranscriptCreate,
    SpeechTranscriptRead,
    SpeechTranscriptStatus,
    SpeechTranscriptVisibility,
)
from noveland.speech.models import SpeechTranscript
from noveland.speech.voice_profiles import SpeechNotFoundError, SpeechValidationError
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import select
from sqlalchemy.orm import Session


class SpeechTranscriptService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_transcript(self, create: SpeechTranscriptCreate) -> SpeechTranscriptRead:
        worldline_id = self._worldline_id(create.world_id, create.worldline_id)
        self._validate_refs(create, worldline_id)
        model = SpeechTranscript(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=worldline_id,
            source_asset_id=create.source_asset_id,
            media_job_id=create.media_job_id,
            model_invocation_id=create.model_invocation_id,
            conversation_id=create.conversation_id,
            turn_id=create.turn_id,
            speaker_actor_ref=create.speaker_actor_ref,
            language=create.language,
            transcript_text=create.transcript_text,
            segments_json=create.segments_json,
            confidence_json=create.confidence_json,
            status=create.status.value,
            visibility=create.visibility.value,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _transcript_record(model)

    def get_transcript(
        self,
        world_id: uuid.UUID,
        transcript_id: uuid.UUID,
    ) -> SpeechTranscriptRead | None:
        model = self._session.get(SpeechTranscript, transcript_id)
        if model is None or model.world_id != world_id or model.status == "deleted":
            return None
        return _transcript_record(model)

    def list_transcripts(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
        source_asset_id: uuid.UUID | None = None,
    ) -> list[SpeechTranscriptRead]:
        resolved = self._worldline_id(world_id, worldline_id)
        statement = select(SpeechTranscript).where(
            SpeechTranscript.world_id == world_id,
            SpeechTranscript.worldline_id == resolved,
            SpeechTranscript.status != "deleted",
        )
        if source_asset_id is not None:
            statement = statement.where(SpeechTranscript.source_asset_id == source_asset_id)
        statement = statement.order_by(SpeechTranscript.created_at.desc())
        return [_transcript_record(model) for model in self._session.scalars(statement).all()]

    def _validate_refs(self, create: SpeechTranscriptCreate, worldline_id: uuid.UUID) -> None:
        asset = self._session.get(MediaAsset, create.source_asset_id)
        if asset is None or asset.world_id != create.world_id or asset.worldline_id != worldline_id:
            raise SpeechValidationError("source asset must belong to transcript worldline")
        if create.media_job_id is not None:
            job = self._session.get(MediaJob, create.media_job_id)
            if job is None or job.world_id != create.world_id or job.worldline_id != worldline_id:
                raise SpeechValidationError("media job must belong to transcript worldline")
        if create.model_invocation_id is not None:
            invocation = self._session.get(ModelInvocation, create.model_invocation_id)
            if (
                invocation is None
                or invocation.world_id != create.world_id
                or invocation.worldline_id != worldline_id
            ):
                raise SpeechValidationError(
                    "model invocation must belong to transcript worldline"
                )
        if create.conversation_id is not None:
            conversation = self._session.get(ConversationSession, create.conversation_id)
            if (
                conversation is None
                or conversation.world_id != create.world_id
                or conversation.worldline_id != worldline_id
            ):
                raise SpeechValidationError("conversation must belong to transcript worldline")
        if create.turn_id is not None:
            turn = self._session.get(ConversationTurn, create.turn_id)
            if turn is None:
                raise SpeechValidationError("turn must belong to transcript worldline")
            session_model = self._session.get(ConversationSession, turn.session_id)
            if (
                session_model is None
                or session_model.world_id != create.world_id
                or session_model.worldline_id != worldline_id
            ):
                raise SpeechValidationError("turn must belong to transcript worldline")

    def _worldline_id(self, world_id: uuid.UUID, worldline_id: uuid.UUID | None) -> uuid.UUID:
        try:
            return worldline_or_404(self._session, world_id, worldline_id).id
        except ValueError as exc:
            raise SpeechNotFoundError("worldline not found") from exc


def _transcript_record(model: SpeechTranscript) -> SpeechTranscriptRead:
    return SpeechTranscriptRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        source_asset_id=model.source_asset_id,
        media_job_id=model.media_job_id,
        model_invocation_id=model.model_invocation_id,
        conversation_id=model.conversation_id,
        turn_id=model.turn_id,
        speaker_actor_ref=model.speaker_actor_ref,
        language=model.language,
        transcript_text=model.transcript_text,
        segments_json=model.segments_json,
        confidence_json=model.confidence_json,
        status=SpeechTranscriptStatus(model.status),
        visibility=SpeechTranscriptVisibility(model.visibility),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
