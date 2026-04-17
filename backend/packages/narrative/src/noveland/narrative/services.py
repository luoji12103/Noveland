from __future__ import annotations

import uuid
from datetime import UTC, datetime

from noveland.narrative.contracts import (
    NarrativeArtifactCreate,
    NarrativeArtifactKind,
    NarrativeArtifactRecord,
)
from noveland.narrative.models import NarrativeArtifact
from sqlalchemy import select
from sqlalchemy.orm import Session


class NarrativeArtifactService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_artifacts(self, world_id: uuid.UUID) -> list[NarrativeArtifactRecord]:
        return [
            _record(model)
            for model in self._session.scalars(
                select(NarrativeArtifact)
                .where(NarrativeArtifact.world_id == world_id)
                .order_by(NarrativeArtifact.created_at.desc()),
            ).all()
        ]

    def create_artifact(
        self,
        artifact_create: NarrativeArtifactCreate,
    ) -> NarrativeArtifactRecord:
        model = NarrativeArtifact(
            world_id=artifact_create.world_id,
            agent_id=artifact_create.agent_id,
            source_run_id=artifact_create.source_run_id,
            title=artifact_create.title,
            content=artifact_create.content,
            artifact_kind=artifact_create.artifact_kind.value,
            artifact_metadata=artifact_create.metadata,
        )
        self._session.add(model)
        self._session.flush()
        return _record(model)


def _record(model: NarrativeArtifact) -> NarrativeArtifactRecord:
    return NarrativeArtifactRecord(
        id=model.id,
        world_id=model.world_id,
        agent_id=model.agent_id,
        source_run_id=model.source_run_id,
        title=model.title,
        content=model.content,
        artifact_kind=NarrativeArtifactKind(model.artifact_kind),
        metadata=model.artifact_metadata,
        created_at=_utc(model.created_at),
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
