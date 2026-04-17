from __future__ import annotations

import math
import uuid
from collections.abc import Sequence

from noveland.memory.contracts import MemoryItemCreate, MemoryItemRecord, MemorySearchQuery
from noveland.memory.models import AgentMemoryItem
from sqlalchemy import select
from sqlalchemy.orm import Session


class LocalPgvectorMemoryBackend:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, item: MemoryItemCreate) -> MemoryItemRecord:
        model = AgentMemoryItem(
            id=uuid.uuid4(),
            world_id=item.world_id,
            agent_id=item.agent_id,
            source_event_id=item.source_event_id,
            content=item.content,
            metadata_json=item.metadata,
            embedding=item.embedding,
            visibility="private",
            is_active=True,
        )
        self._session.add(model)
        self._session.flush()
        return _record(model)

    def list(self, world_id: uuid.UUID, agent_id: uuid.UUID) -> Sequence[MemoryItemRecord]:
        models = self._session.scalars(
            select(AgentMemoryItem)
            .where(
                AgentMemoryItem.world_id == world_id,
                AgentMemoryItem.agent_id == agent_id,
                AgentMemoryItem.is_active.is_(True),
            )
            .order_by(AgentMemoryItem.created_at.desc()),
        ).all()
        return [_record(model) for model in models]

    def search(self, query: MemorySearchQuery) -> Sequence[MemoryItemRecord]:
        scored = [
            _record(model, _cosine_similarity(query.embedding, model.embedding))
            for model in self._session.scalars(
                select(AgentMemoryItem).where(
                    AgentMemoryItem.world_id == query.world_id,
                    AgentMemoryItem.agent_id == query.agent_id,
                    AgentMemoryItem.is_active.is_(True),
                ),
            ).all()
        ]
        return sorted(scored, key=lambda item: item.score or 0, reverse=True)[: query.limit]

    def disable(self, memory_id: uuid.UUID) -> None:
        model = self._session.get(AgentMemoryItem, memory_id)
        if model is not None:
            model.is_active = False
            self._session.flush()


def _record(model: AgentMemoryItem, score: float | None = None) -> MemoryItemRecord:
    return MemoryItemRecord(
        id=model.id,
        world_id=model.world_id,
        agent_id=model.agent_id,
        content=model.content,
        metadata=model.metadata_json,
        embedding=model.embedding,
        visibility=model.visibility,
        is_active=model.is_active,
        source_event_id=model.source_event_id,
        score=score,
    )


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(left_item * right_item for left_item, right_item in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(item * item for item in left))
    right_norm = math.sqrt(sum(item * item for item in right))
    if left_norm == 0 or right_norm == 0:
        return 0
    return dot / (left_norm * right_norm)
