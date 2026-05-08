from __future__ import annotations

import uuid
from collections import defaultdict
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

BACKEND_NAME = "fake_memory"


class FakeMemoryBackend:
    def __init__(self) -> None:
        self._items_by_scope: dict[
            tuple[uuid.UUID, uuid.UUID | None, uuid.UUID],
            list[MemoryItemRecord],
        ] = defaultdict(list)

    def record_turn(self, turn: MemoryTurn) -> MemoryWriteResult:
        content = " ".join(message.content for message in turn.messages).strip()
        if not content:
            return MemoryWriteResult(
                backend=BACKEND_NAME, source_dedupe_key=turn.dedupe_key, recorded_count=0
            )
        item = MemoryItemRecord(
            id=str(uuid.uuid4()),
            world_id=turn.world_id,
            agent_id=turn.agent_id,
            content=content,
            metadata=turn.metadata,
            backend=BACKEND_NAME,
            created_at=datetime.now(UTC),
            score=None,
        )
        self._items_by_scope[(turn.world_id, turn.worldline_id, turn.agent_id)].insert(0, item)
        return MemoryWriteResult(
            backend=BACKEND_NAME,
            source_dedupe_key=turn.dedupe_key,
            recorded_count=1,
            backend_ids=[item.id],
        )

    def record_events(self, events: Sequence[MemoryEvent]) -> MemoryWriteResult:
        backend_ids: list[str] = []
        for event in events:
            item = MemoryItemRecord(
                id=str(uuid.uuid4()),
                world_id=event.world_id,
                agent_id=event.agent_id,
                content=event.content,
                metadata=event.metadata,
                backend=BACKEND_NAME,
                created_at=datetime.now(UTC),
            )
            self._items_by_scope[(event.world_id, event.worldline_id, event.agent_id)].insert(
                0,
                item,
            )
            backend_ids.append(item.id)
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
        return list(self._items_by_scope[(world_id, worldline_id, agent_id)])

    def search(self, request: MemorySearchRequest) -> MemorySearchResult:
        matches = [
            item
            for item in self._items_by_scope[
                (request.world_id, request.worldline_id, request.agent_id)
            ]
            if request.query_text.lower() in item.content.lower()
        ][: request.limit]
        return MemorySearchResult(backend=BACKEND_NAME, items=matches, latency_ms=0)

    def delete_scope(self, scope: MemoryDeleteScope) -> MemoryDeleteResult:
        key = (scope.world_id, scope.worldline_id, scope.agent_id)
        deleted_count = len(self._items_by_scope[key])
        self._items_by_scope[key] = []
        return MemoryDeleteResult(backend=BACKEND_NAME, deleted_count=deleted_count)

    def healthcheck(self) -> MemoryBackendHealth:
        return MemoryBackendHealth(
            backend=BACKEND_NAME,
            status=MemoryBackendHealthStatus.OK,
            details={},
        )
