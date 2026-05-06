from __future__ import annotations

import math
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from noveland.memory.contracts import (
    MemoryBackendHealth,
    MemoryBackendHealthStatus,
    MemoryDeleteResult,
    MemoryDeleteScope,
    MemoryEvent,
    MemoryItemRecord,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryTurn,
    MemoryWriteResult,
)
from noveland.memory.models import AgentMemoryItem
from noveland.memory.utils import deterministic_embedding
from noveland.worlds.worldlines import ensure_primary_worldline, primary_worldline_or_none
from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.orm import Session

BACKEND_NAME = "local_pgvector"


class LocalPgvectorMemoryBackend:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record_turn(self, turn: MemoryTurn) -> MemoryWriteResult:
        content = " ".join(
            message.content.strip() for message in turn.messages if message.content.strip()
        )
        if not content:
            return MemoryWriteResult(
                backend=BACKEND_NAME,
                source_dedupe_key=turn.dedupe_key,
                recorded_count=0,
            )

        model = AgentMemoryItem(
            id=uuid.uuid4(),
            world_id=turn.world_id,
            worldline_id=_worldline_id(self._session, turn.world_id, turn.worldline_id),
            agent_id=turn.agent_id,
            source_event_id=turn.source_event_id,
            content=content,
            metadata_json={
                **turn.metadata,
                "conversation_id": None
                if turn.conversation_id is None
                else str(turn.conversation_id),
                "turn_id": None if turn.turn_id is None else str(turn.turn_id),
                "run_id": None if turn.run_id is None else str(turn.run_id),
                "trigger_source": turn.trigger_source,
            },
            embedding=deterministic_embedding(content),
            visibility="private",
            is_active=True,
        )
        self._session.add(model)
        self._session.flush()
        return MemoryWriteResult(
            backend=BACKEND_NAME,
            source_dedupe_key=turn.dedupe_key,
            recorded_count=1,
            backend_ids=[str(model.id)],
        )

    def record_events(self, events: Sequence[MemoryEvent]) -> MemoryWriteResult:
        backend_ids: list[str] = []
        for event in events:
            model = AgentMemoryItem(
                id=uuid.uuid4(),
                world_id=event.world_id,
                worldline_id=_worldline_id(self._session, event.world_id, event.worldline_id),
                agent_id=event.agent_id,
                source_event_id=event.event_id,
                content=event.content,
                metadata_json=event.metadata,
                embedding=deterministic_embedding(event.content),
                visibility="private",
                is_active=True,
            )
            self._session.add(model)
            self._session.flush()
            backend_ids.append(str(model.id))
        dedupe_key = events[0].dedupe_key if events else "no-events"
        return MemoryWriteResult(
            backend=BACKEND_NAME,
            source_dedupe_key=dedupe_key,
            recorded_count=len(backend_ids),
            backend_ids=backend_ids,
        )

    def list_memories(
        self,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
        worldline_id: uuid.UUID | None = None,
    ) -> Sequence[MemoryItemRecord]:
        resolved_worldline_id = _worldline_id(self._session, world_id, worldline_id)
        models = self._session.scalars(
            select(AgentMemoryItem)
            .where(
                AgentMemoryItem.world_id == world_id,
                AgentMemoryItem.agent_id == agent_id,
                AgentMemoryItem.is_active.is_(True),
            )
            .where(_memory_worldline_scope(self._session, world_id, resolved_worldline_id))
            .order_by(AgentMemoryItem.created_at.desc()),
        ).all()
        return [_record(model) for model in models]

    def search(self, request: MemorySearchRequest) -> MemorySearchResult:
        started_at = datetime.now(UTC)
        query_embedding = deterministic_embedding(request.query_text)
        resolved_worldline_id = _worldline_id(
            self._session,
            request.world_id,
            request.worldline_id,
        )
        scored = [
            _record(model, _cosine_similarity(query_embedding, model.embedding))
            for model in self._session.scalars(
                select(AgentMemoryItem)
                .where(
                    AgentMemoryItem.world_id == request.world_id,
                    AgentMemoryItem.agent_id == request.agent_id,
                    AgentMemoryItem.is_active.is_(True),
                )
                .where(
                    _memory_worldline_scope(
                        self._session,
                        request.world_id,
                        resolved_worldline_id,
                    ),
                ),
            ).all()
        ]
        items = sorted(scored, key=lambda item: item.score or 0, reverse=True)[: request.limit]
        latency_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
        return MemorySearchResult(
            backend=BACKEND_NAME,
            items=items,
            latency_ms=latency_ms,
        )

    def delete_scope(self, scope: MemoryDeleteScope) -> MemoryDeleteResult:
        resolved_worldline_id = _worldline_id(self._session, scope.world_id, scope.worldline_id)
        models = self._session.scalars(
            select(AgentMemoryItem)
            .where(
                AgentMemoryItem.world_id == scope.world_id,
                AgentMemoryItem.agent_id == scope.agent_id,
                AgentMemoryItem.is_active.is_(True),
            )
            .where(_memory_worldline_scope(self._session, scope.world_id, resolved_worldline_id)),
        ).all()
        deleted_count = 0
        for model in models:
            model.is_active = False
            deleted_count += 1
        self._session.flush()
        return MemoryDeleteResult(backend=BACKEND_NAME, deleted_count=deleted_count)

    def healthcheck(self) -> MemoryBackendHealth:
        return MemoryBackendHealth(
            backend=BACKEND_NAME,
            status=MemoryBackendHealthStatus.OK,
            details={},
        )


def _record(model: AgentMemoryItem, score: float | None = None) -> MemoryItemRecord:
    return MemoryItemRecord(
        id=str(model.id),
        world_id=model.world_id,
        agent_id=model.agent_id,
        content=model.content,
        metadata=model.metadata_json,
        backend=BACKEND_NAME,
        created_at=_aware_datetime(model.created_at),
        score=score,
    )


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(left_item * right_item for left_item, right_item in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(item * item for item in left))
    right_norm = math.sqrt(sum(item * item for item in right))
    if left_norm == 0 or right_norm == 0:
        return 0
    return dot / (left_norm * right_norm)


def _aware_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _worldline_id(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID | None,
) -> uuid.UUID:
    if worldline_id is not None:
        return worldline_id
    return ensure_primary_worldline(session, world_id).id


def _memory_worldline_scope(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> ColumnElement[bool]:
    primary = primary_worldline_or_none(session, world_id)
    if primary is not None and primary.id == worldline_id:
        return or_(
            AgentMemoryItem.worldline_id == worldline_id,
            AgentMemoryItem.worldline_id.is_(None),
        )
    return AgentMemoryItem.worldline_id == worldline_id
