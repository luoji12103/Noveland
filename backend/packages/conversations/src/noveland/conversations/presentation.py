from __future__ import annotations

import uuid
from typing import Any

from noveland.agents.models import Agent
from noveland.conversations.contracts import (
    ConversationPresentationRenderState,
    ConversationTurnPresentationPatch,
    ConversationTurnPresentationRecord,
    ConversationTurnPresentationUpsert,
)
from noveland.conversations.errors import ConversationValidationError
from noveland.conversations.models import (
    ConversationSession,
    ConversationTurn,
    ConversationTurnPresentation,
)
from noveland.core.database import Base
from sqlalchemy import select
from sqlalchemy.orm import Session


class ConversationPresentationService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_presentation(
        self,
        world_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
    ) -> ConversationTurnPresentationRecord | None:
        session_model, _turn, worldline_id = self._turn_context(
            world_id,
            conversation_id,
            turn_id,
        )
        model = self._session.scalars(
            select(ConversationTurnPresentation).where(
                ConversationTurnPresentation.world_id == world_id,
                ConversationTurnPresentation.worldline_id == worldline_id,
                ConversationTurnPresentation.conversation_id == session_model.id,
                ConversationTurnPresentation.turn_id == turn_id,
            ),
        ).one_or_none()
        return None if model is None else _presentation_record(model)

    def put_presentation(
        self,
        world_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
        upsert: ConversationTurnPresentationUpsert,
    ) -> ConversationTurnPresentationRecord:
        session_model, turn, worldline_id = self._turn_context(
            world_id,
            conversation_id,
            turn_id,
        )
        self._validate_upsert(world_id, worldline_id, turn, upsert)
        model = self._model_for_turn(turn_id)
        if model is None:
            model = ConversationTurnPresentation(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                conversation_id=session_model.id,
                turn_id=turn_id,
            )
            self._session.add(model)
        self._apply_upsert(model, upsert)
        self._session.flush()
        self._session.refresh(model)
        return _presentation_record(model)

    def patch_presentation(
        self,
        world_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
        patch: ConversationTurnPresentationPatch,
    ) -> ConversationTurnPresentationRecord:
        current = self.get_presentation(world_id, conversation_id, turn_id)
        merged = _merge_patch(current, patch)
        return self.put_presentation(world_id, conversation_id, turn_id, merged)

    def apply_visual_result(
        self,
        world_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
        *,
        speaker_agent_id: uuid.UUID | None,
        emotion_key: str | None,
        emotion_intensity: float | None,
        sprite_set_id: uuid.UUID,
        sprite_variant_id: uuid.UUID,
        background_asset_id: uuid.UUID,
        composite_scene_asset_id: uuid.UUID,
        presentation_json: dict[str, Any],
    ) -> ConversationTurnPresentationRecord:
        current = self.get_presentation(world_id, conversation_id, turn_id)
        return self.put_presentation(
            world_id,
            conversation_id,
            turn_id,
            ConversationTurnPresentationUpsert(
                speaker_agent_id=speaker_agent_id,
                emotion_key=emotion_key,
                emotion_intensity=emotion_intensity,
                sprite_set_id=sprite_set_id,
                sprite_variant_id=sprite_variant_id,
                voice_profile_id=None if current is None else current.voice_profile_id,
                tts_media_asset_id=None if current is None else current.tts_media_asset_id,
                background_asset_id=background_asset_id,
                composite_scene_asset_id=composite_scene_asset_id,
                transcript_id=None if current is None else current.transcript_id,
                presentation_json={
                    **({} if current is None else current.presentation_json),
                    **presentation_json,
                },
                render_state=ConversationPresentationRenderState.VISUAL_RENDERED,
            ),
        )

    def apply_speech_result(
        self,
        world_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
        *,
        speaker_agent_id: uuid.UUID | None,
        emotion_key: str | None,
        emotion_intensity: float | None,
        voice_profile_id: uuid.UUID | None,
        tts_media_asset_id: uuid.UUID,
        presentation_json: dict[str, Any],
    ) -> ConversationTurnPresentationRecord:
        current = self.get_presentation(world_id, conversation_id, turn_id)
        return self.put_presentation(
            world_id,
            conversation_id,
            turn_id,
            ConversationTurnPresentationUpsert(
                speaker_agent_id=speaker_agent_id,
                emotion_key=emotion_key,
                emotion_intensity=emotion_intensity,
                sprite_set_id=None if current is None else current.sprite_set_id,
                sprite_variant_id=None if current is None else current.sprite_variant_id,
                voice_profile_id=voice_profile_id,
                tts_media_asset_id=tts_media_asset_id,
                background_asset_id=None if current is None else current.background_asset_id,
                composite_scene_asset_id=(
                    None if current is None else current.composite_scene_asset_id
                ),
                transcript_id=None if current is None else current.transcript_id,
                presentation_json={
                    **({} if current is None else current.presentation_json),
                    **presentation_json,
                },
                render_state=ConversationPresentationRenderState.SPEECH_RENDERED,
            ),
        )

    def apply_transcript_result(
        self,
        world_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
        *,
        transcript_id: uuid.UUID,
        source_asset_id: uuid.UUID,
        presentation_json: dict[str, Any],
    ) -> ConversationTurnPresentationRecord:
        current = self.get_presentation(world_id, conversation_id, turn_id)
        return self.put_presentation(
            world_id,
            conversation_id,
            turn_id,
            ConversationTurnPresentationUpsert(
                speaker_agent_id=None if current is None else current.speaker_agent_id,
                emotion_key=None if current is None else current.emotion_key,
                emotion_intensity=None if current is None else current.emotion_intensity,
                sprite_set_id=None if current is None else current.sprite_set_id,
                sprite_variant_id=None if current is None else current.sprite_variant_id,
                voice_profile_id=None if current is None else current.voice_profile_id,
                tts_media_asset_id=None if current is None else current.tts_media_asset_id,
                background_asset_id=None if current is None else current.background_asset_id,
                composite_scene_asset_id=(
                    None if current is None else current.composite_scene_asset_id
                ),
                transcript_id=transcript_id,
                presentation_json={
                    **({} if current is None else current.presentation_json),
                    "source_audio_asset_id": str(source_asset_id),
                    **presentation_json,
                },
                render_state=ConversationPresentationRenderState.TRANSCRIBED,
            ),
        )

    def _turn_context(
        self,
        world_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
    ) -> tuple[ConversationSession, ConversationTurn, uuid.UUID]:
        session_model = self._session.get(ConversationSession, conversation_id)
        if session_model is None or session_model.world_id != world_id:
            raise LookupError("Conversation session not found")
        if session_model.worldline_id is None:
            raise ConversationValidationError("conversation must have worldline_id")
        turn = self._session.get(ConversationTurn, turn_id)
        if turn is None or turn.session_id != conversation_id:
            raise LookupError("Conversation turn not found")
        return session_model, turn, session_model.worldline_id

    def _validate_upsert(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        turn: ConversationTurn,
        upsert: ConversationTurnPresentationUpsert,
    ) -> None:
        if upsert.speaker_agent_id is not None:
            agent = self._session.get(Agent, upsert.speaker_agent_id)
            if agent is None or agent.world_id != world_id:
                raise ConversationValidationError("speaker agent must belong to world")
        if upsert.sprite_set_id is not None:
            self._assert_visual_record(
                "character_sprite_sets",
                upsert.sprite_set_id,
                world_id,
                worldline_id,
                "sprite set",
            )
        if upsert.sprite_variant_id is not None:
            self._assert_visual_record(
                "character_sprite_variants",
                upsert.sprite_variant_id,
                world_id,
                worldline_id,
                "sprite variant",
            )
        if upsert.voice_profile_id is not None:
            self._assert_optional_worldline_record(
                "voice_profiles",
                upsert.voice_profile_id,
                world_id,
                worldline_id,
                "voice profile",
            )
        if upsert.transcript_id is not None:
            self._assert_visual_record(
                "speech_transcripts",
                upsert.transcript_id,
                world_id,
                worldline_id,
                "speech transcript",
            )
        for asset_id, expected_kind, label in (
            (upsert.tts_media_asset_id, "audio", "TTS media asset"),
            (upsert.background_asset_id, "image", "background asset"),
            (upsert.composite_scene_asset_id, "image", "composite scene asset"),
        ):
            if asset_id is not None:
                self._assert_asset(world_id, worldline_id, asset_id, expected_kind, label)
        if turn.speaker_agent_id is not None and upsert.speaker_agent_id is not None:
            if turn.speaker_agent_id != upsert.speaker_agent_id:
                raise ConversationValidationError("speaker agent must match conversation turn")

    def _model_for_turn(self, turn_id: uuid.UUID) -> ConversationTurnPresentation | None:
        return self._session.scalars(
            select(ConversationTurnPresentation).where(
                ConversationTurnPresentation.turn_id == turn_id,
            ),
        ).one_or_none()

    def _apply_upsert(
        self,
        model: ConversationTurnPresentation,
        upsert: ConversationTurnPresentationUpsert,
    ) -> None:
        model.speaker_agent_id = upsert.speaker_agent_id
        model.emotion_key = _normalized_key(upsert.emotion_key)
        model.emotion_intensity = upsert.emotion_intensity
        model.sprite_set_id = upsert.sprite_set_id
        model.sprite_variant_id = upsert.sprite_variant_id
        model.voice_profile_id = upsert.voice_profile_id
        model.tts_media_asset_id = upsert.tts_media_asset_id
        model.background_asset_id = upsert.background_asset_id
        model.composite_scene_asset_id = upsert.composite_scene_asset_id
        model.transcript_id = upsert.transcript_id
        model.presentation_json = dict(upsert.presentation_json)
        model.render_state = upsert.render_state.value

    def _assert_asset(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        asset_id: uuid.UUID,
        expected_kind: str,
        label: str,
    ) -> None:
        record = self._record_row("media_assets", asset_id)
        if (
            record is None
            or record.get("world_id") != world_id
            or record.get("worldline_id") != worldline_id
            or record.get("asset_kind") != expected_kind
            or record.get("status") == "deleted"
        ):
            raise ConversationValidationError(f"{label} must belong to conversation worldline")

    def _assert_visual_record(
        self,
        table_name: str,
        record_id: uuid.UUID,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        label: str,
    ) -> None:
        record = self._record_row(table_name, record_id)
        if (
            record is None
            or record.get("world_id") != world_id
            or record.get("worldline_id") != worldline_id
        ):
            raise ConversationValidationError(f"{label} must belong to conversation worldline")

    def _assert_optional_worldline_record(
        self,
        table_name: str,
        record_id: uuid.UUID,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        label: str,
    ) -> None:
        record = self._record_row(table_name, record_id)
        if record is None or record.get("world_id") != world_id:
            raise ConversationValidationError(f"{label} must belong to world")
        record_worldline_id = record.get("worldline_id")
        if record_worldline_id is not None and record_worldline_id != worldline_id:
            raise ConversationValidationError(f"{label} must belong to conversation worldline")

    def _record_row(self, table_name: str, record_id: uuid.UUID) -> dict[str, Any] | None:
        db_table = Base.metadata.tables[table_name]
        row = self._session.execute(
            select(db_table).where(db_table.c.id == record_id),
        ).mappings().first()
        return None if row is None else dict(row)


def _presentation_record(
    model: ConversationTurnPresentation,
) -> ConversationTurnPresentationRecord:
    return ConversationTurnPresentationRecord(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        conversation_id=model.conversation_id,
        turn_id=model.turn_id,
        speaker_agent_id=model.speaker_agent_id,
        emotion_key=model.emotion_key,
        emotion_intensity=model.emotion_intensity,
        sprite_set_id=model.sprite_set_id,
        sprite_variant_id=model.sprite_variant_id,
        voice_profile_id=model.voice_profile_id,
        tts_media_asset_id=model.tts_media_asset_id,
        background_asset_id=model.background_asset_id,
        composite_scene_asset_id=model.composite_scene_asset_id,
        transcript_id=model.transcript_id,
        presentation_json=model.presentation_json,
        render_state=ConversationPresentationRenderState(model.render_state),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _merge_patch(
    current: ConversationTurnPresentationRecord | None,
    patch: ConversationTurnPresentationPatch,
) -> ConversationTurnPresentationUpsert:
    if current is None:
        return ConversationTurnPresentationUpsert(
            speaker_agent_id=patch.speaker_agent_id,
            emotion_key=patch.emotion_key,
            emotion_intensity=patch.emotion_intensity,
            sprite_set_id=patch.sprite_set_id,
            sprite_variant_id=patch.sprite_variant_id,
            voice_profile_id=patch.voice_profile_id,
            tts_media_asset_id=patch.tts_media_asset_id,
            background_asset_id=patch.background_asset_id,
            composite_scene_asset_id=patch.composite_scene_asset_id,
            transcript_id=patch.transcript_id,
            presentation_json={} if patch.presentation_json is None else patch.presentation_json,
            render_state=patch.render_state or ConversationPresentationRenderState.DRAFT,
        )
    return ConversationTurnPresentationUpsert(
        speaker_agent_id=_patch_value(patch, "speaker_agent_id", current.speaker_agent_id),
        emotion_key=_patch_value(patch, "emotion_key", current.emotion_key),
        emotion_intensity=_patch_value(patch, "emotion_intensity", current.emotion_intensity),
        sprite_set_id=_patch_value(patch, "sprite_set_id", current.sprite_set_id),
        sprite_variant_id=_patch_value(patch, "sprite_variant_id", current.sprite_variant_id),
        voice_profile_id=_patch_value(patch, "voice_profile_id", current.voice_profile_id),
        tts_media_asset_id=_patch_value(patch, "tts_media_asset_id", current.tts_media_asset_id),
        background_asset_id=_patch_value(
            patch,
            "background_asset_id",
            current.background_asset_id,
        ),
        composite_scene_asset_id=_patch_value(
            patch,
            "composite_scene_asset_id",
            current.composite_scene_asset_id,
        ),
        transcript_id=_patch_value(patch, "transcript_id", current.transcript_id),
        presentation_json=(
            current.presentation_json
            if "presentation_json" not in patch.model_fields_set
            or patch.presentation_json is None
            else patch.presentation_json
        ),
        render_state=(
            current.render_state
            if patch.render_state is None
            else patch.render_state
        ),
    )


def _patch_value(
    patch: ConversationTurnPresentationPatch,
    field_name: str,
    current: Any,
) -> Any:
    if field_name in patch.model_fields_set:
        return getattr(patch, field_name)
    return current


def _normalized_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None
