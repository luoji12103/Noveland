from __future__ import annotations

import uuid

from noveland.speech.contracts import (
    SpeechStyleMappingCreate,
    SpeechStyleMappingRead,
    SpeechStyleMappingUpdate,
)
from noveland.speech.models import SpeechStyleMapping
from noveland.speech.voice_profiles import SpeechNotFoundError, SpeechValidationError
from noveland.worlds.models import World
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class SpeechStyleMappingService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_mapping(self, create: SpeechStyleMappingCreate) -> SpeechStyleMappingRead:
        if self._session.get(World, create.world_id) is None:
            raise SpeechValidationError("world not found")
        model = SpeechStyleMapping(
            id=uuid.uuid4(),
            world_id=create.world_id,
            mapping_key=create.mapping_key,
            provider_kind=create.provider_kind,
            emotion_key=create.emotion_key,
            style_json=create.style_json,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise SpeechValidationError("speech style mapping already exists") from exc
        self._session.refresh(model)
        return _mapping_record(model)

    def update_mapping(
        self,
        world_id: uuid.UUID,
        mapping_id: uuid.UUID,
        update: SpeechStyleMappingUpdate,
    ) -> SpeechStyleMappingRead:
        model = self._mapping_required(world_id, mapping_id)
        if update.style_json is not None:
            model.style_json = update.style_json
        self._session.flush()
        self._session.refresh(model)
        return _mapping_record(model)

    def delete_mapping(self, world_id: uuid.UUID, mapping_id: uuid.UUID) -> None:
        model = self._mapping_required(world_id, mapping_id)
        self._session.delete(model)
        self._session.flush()

    def list_mappings(
        self,
        world_id: uuid.UUID,
        *,
        provider_kind: str | None = None,
        emotion_key: str | None = None,
    ) -> list[SpeechStyleMappingRead]:
        statement = select(SpeechStyleMapping).where(SpeechStyleMapping.world_id == world_id)
        if provider_kind is not None:
            statement = statement.where(SpeechStyleMapping.provider_kind == provider_kind)
        if emotion_key is not None:
            statement = statement.where(SpeechStyleMapping.emotion_key == emotion_key)
        statement = statement.order_by(
            SpeechStyleMapping.provider_kind,
            SpeechStyleMapping.emotion_key,
        )
        return [_mapping_record(model) for model in self._session.scalars(statement).all()]

    def resolve_style(
        self,
        world_id: uuid.UUID,
        provider_kind: str,
        emotion_key: str | None,
    ) -> dict[str, object]:
        if emotion_key is None:
            return {}
        model = self._session.scalars(
            select(SpeechStyleMapping)
            .where(
                SpeechStyleMapping.world_id == world_id,
                SpeechStyleMapping.provider_kind == provider_kind,
                SpeechStyleMapping.emotion_key == emotion_key.strip().lower(),
            )
            .order_by(SpeechStyleMapping.mapping_key)
            .limit(1)
        ).first()
        return {} if model is None else dict(model.style_json)

    def _mapping_required(self, world_id: uuid.UUID, mapping_id: uuid.UUID) -> SpeechStyleMapping:
        model = self._session.get(SpeechStyleMapping, mapping_id)
        if model is None or model.world_id != world_id:
            raise SpeechNotFoundError("speech style mapping not found")
        return model


def _mapping_record(model: SpeechStyleMapping) -> SpeechStyleMappingRead:
    return SpeechStyleMappingRead(
        id=model.id,
        world_id=model.world_id,
        mapping_key=model.mapping_key,
        provider_kind=model.provider_kind,
        emotion_key=model.emotion_key,
        style_json=dict(model.style_json),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
