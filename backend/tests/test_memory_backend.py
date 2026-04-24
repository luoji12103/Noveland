from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import cast

import pytest
from noveland.agents.models import Agent
from noveland.auth.models import User
from noveland.core.settings import AppSettings
from noveland.events.models import WorldEventModel
from noveland.memory import (
    FakeMemoryBackend,
    LocalPgvectorMemoryBackend,
    Mem0OssMemoryBackend,
    MemoryBackendKind,
    MemoryBackendProfileCreate,
    MemoryBackendProfileService,
    MemoryDeleteScope,
    MemoryEvalCase,
    MemoryEvent,
    MemoryMessage,
    MemoryProfileSnapshotRecord,
    MemorySearchRequest,
    MemoryService,
    MemoryTurn,
    run_memory_eval_cases,
)
from noveland.memory.models import (
    AgentMemoryItem,
    AgentProfileSnapshotModel,
    MemoryBackendProfile,
    MemoryRetrievalLog,
    MemoryWriteJob,
    MemoryWriteLog,
)
from noveland.worlds.models import World
from pydantic import ValidationError
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_memory_turn_requires_at_least_one_message() -> None:
    with pytest.raises(ValidationError):
        MemoryTurn(
            world_id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            messages=[],
            dedupe_key="turn-1",
        )


def test_local_pgvector_memory_backend_records_lists_searches_and_deletes_scope() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id)
    agent_id = _seed_agent(engine, world_id)

    with Session(engine) as session:
        backend = LocalPgvectorMemoryBackend(session)
        first = backend.record_turn(
            MemoryTurn(
                world_id=world_id,
                agent_id=agent_id,
                messages=[MemoryMessage(role="assistant", content="likes green tea")],
                dedupe_key="turn-1",
            ),
        )
        second = backend.record_turn(
            MemoryTurn(
                world_id=world_id,
                agent_id=agent_id,
                messages=[MemoryMessage(role="assistant", content="likes red apples")],
                dedupe_key="turn-2",
            ),
        )
        listed = backend.list_memories(world_id, agent_id)
        searched = backend.search(
            MemorySearchRequest(
                world_id=world_id,
                agent_id=agent_id,
                query_text="green tea",
            ),
        )
        delete_result = backend.delete_scope(
            MemoryDeleteScope(
                world_id=world_id,
                agent_id=agent_id,
                run_id=None,
            ),
        )
        after_delete = backend.list_memories(world_id, agent_id)
        session.commit()

    assert set(first.backend_ids) | set(second.backend_ids) == {item.id for item in listed}
    assert searched.items[0].content == "likes green tea"
    assert searched.items[0].score is not None
    assert delete_result.deleted_count == 2
    assert after_delete == []


def test_fake_memory_backend_matches_long_term_memory_contract() -> None:
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    backend = FakeMemoryBackend()

    turn_result = backend.record_turn(
        MemoryTurn(
            world_id=world_id,
            agent_id=agent_id,
            messages=[MemoryMessage(role="assistant", content="remembers the blue gate")],
            dedupe_key="turn-1",
        )
    )
    event_result = backend.record_events(
        [
            MemoryEvent(
                world_id=world_id,
                agent_id=agent_id,
                event_id=uuid.uuid4(),
                content="saw the blue gate again",
                dedupe_key="event-1",
            )
        ]
    )
    search_result = backend.search(
        MemorySearchRequest(world_id=world_id, agent_id=agent_id, query_text="blue gate")
    )
    delete_result = backend.delete_scope(
        MemoryDeleteScope(world_id=world_id, agent_id=agent_id),
    )

    assert turn_result.recorded_count == 1
    assert event_result.recorded_count == 1
    assert len(search_result.items) == 2
    assert delete_result.deleted_count == 2
    assert backend.healthcheck().status.value == "ok"


def test_mem0_oss_backend_translates_sdk_payloads() -> None:
    with Session(_engine()) as session:
        profile = MemoryBackendProfileService(session).create_profile(
            MemoryBackendProfileCreate(
                profile_key="mem0",
                name="Mem0",
                backend_kind=MemoryBackendKind.MEM0_OSS,
            )
        )
        session.commit()
    backend = Mem0OssMemoryBackend(profile, AppSettings())
    backend._client = _FakeMem0Client()
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()

    turn_result = backend.record_turn(
        MemoryTurn(
            world_id=world_id,
            agent_id=agent_id,
            conversation_id=uuid.uuid4(),
            turn_id=uuid.uuid4(),
            messages=[MemoryMessage(role="assistant", content="remembers the green tea")],
            dedupe_key="turn-1",
        )
    )
    search_result = backend.search(
        MemorySearchRequest(world_id=world_id, agent_id=agent_id, query_text="green tea")
    )

    assert turn_result.backend == "mem0_oss"
    assert turn_result.recorded_count == 1
    assert search_result.items[0].content == "remembers the green tea"
    assert search_result.items[0].metadata["tag"] == "mem0"


def test_run_memory_eval_cases_reports_hits_and_context_sizes() -> None:
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    backend = FakeMemoryBackend()
    backend.record_turn(
        MemoryTurn(
            world_id=world_id,
            agent_id=agent_id,
            messages=[MemoryMessage(role="assistant", content="prefers green tea")],
            dedupe_key="turn-1",
        )
    )

    result = run_memory_eval_cases(
        backend="fake_memory",
        cases=[
            MemoryEvalCase(
                label="green-tea",
                world_id=world_id,
                agent_id=agent_id,
                query_text="green tea",
                limit=3,
            )
        ],
        search_fn=backend.search,
    )

    assert result.case_count == 1
    assert result.hit_case_count == 1
    assert result.average_context_items == 1
    assert result.cases[0].query_text == "green tea"


def test_memory_service_delete_scope_scrubs_logs_and_snapshots() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id)
    agent_id = _seed_agent(engine, world_id)

    with Session(engine) as session:
        profile = MemoryBackendProfileService(session).create_profile(
            MemoryBackendProfileCreate(
                profile_key="local-memory",
                name="Local memory",
                backend_kind=MemoryBackendKind.LOCAL_PGVECTOR,
            )
        )
        world = session.get(World, world_id)
        assert world is not None
        world.memory_backend_profile_id = profile.id
        session.add(
            AgentMemoryItem(
                world_id=world_id,
                agent_id=agent_id,
                content="Guide likes green tea",
                metadata_json={"source": "runtime"},
                embedding=[0.25] * 1536,
                visibility="private",
                is_active=True,
            )
        )
        session.add(
            AgentProfileSnapshotModel(
                world_id=world_id,
                agent_id=agent_id,
                aliases=["guide"],
                identity_notes=["identity"],
                durable_preferences=["tea"],
                long_lived_goals=["help"],
                language_style_preferences=["direct"],
            )
        )
        job = MemoryWriteJob(
            world_id=world_id,
            agent_id=agent_id,
            backend_profile_id=profile.id,
            source_kind="agent_run",
            source_id=uuid.uuid4(),
            payload_json={"content": "Guide likes green tea"},
            dedupe_key="job-1",
            status="succeeded",
            attempt_count=1,
            next_attempt_at=datetime.now(UTC),
        )
        session.add(job)
        session.flush()
        session.add(
            MemoryWriteLog(
                job_id=job.id,
                backend="local_pgvector",
                success=True,
                latency_ms=4,
                request_summary={"prompt": "secret"},
                response_summary={"stored": True},
                correlation_ids={"run_id": "secret"},
            )
        )
        session.add(
            MemoryRetrievalLog(
                world_id=world_id,
                agent_id=agent_id,
                backend_profile_id=profile.id,
                backend="local_pgvector",
                query_text="green tea",
                hit_count=1,
                selected_item_ids=["memory-1"],
                latency_ms=5,
                context_item_count=1,
            )
        )
        session.flush()

        service = MemoryService(session, AppSettings())
        result = service.delete_scope(
            MemoryDeleteScope(world_id=world_id, agent_id=agent_id),
        )
        snapshot = service.refresh_profile_snapshot(world_id, agent_id)
        write_log = session.scalars(select(MemoryWriteLog)).one()
        retrieval_log = session.scalars(select(MemoryRetrievalLog)).one()
        write_log_request_summary = dict(write_log.request_summary)
        retrieval_log_query_text = retrieval_log.query_text
        session.commit()

    assert result.deleted_count == 1
    assert write_log_request_summary == {"redacted": True}
    assert retrieval_log_query_text == "[redacted]"
    assert snapshot == MemoryProfileSnapshotRecord(
        id=snapshot.id,
        world_id=world_id,
        agent_id=agent_id,
        aliases=[],
        identity_notes=[],
        durable_preferences=[],
        long_lived_goals=[],
        language_style_preferences=[],
        refreshed_at=snapshot.refreshed_at,
        created_at=snapshot.created_at,
        updated_at=snapshot.updated_at,
    )


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        cast(Table, User.__table__),
        cast(Table, World.__table__),
        cast(Table, Agent.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, AgentMemoryItem.__table__),
        cast(Table, MemoryWriteJob.__table__),
        cast(Table, MemoryWriteLog.__table__),
        cast(Table, MemoryRetrievalLog.__table__),
        cast(Table, AgentProfileSnapshotModel.__table__),
    ):
        table.create(engine)
    return engine


def _seed_user(engine: Engine) -> uuid.UUID:
    user_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(User(id=user_id, email=f"{user_id}@example.test", display_name="User"))
        session.commit()
    return user_id


def _seed_world(engine: Engine, user_id: uuid.UUID) -> uuid.UUID:
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug=f"world-{world_id.hex[:8]}",
                name="World",
                rules_config={},
            ),
        )
        session.commit()
    return world_id


def _seed_agent(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key=f"agent-{agent_id.hex[:8]}",
                display_name="Agent",
                kind="role_agent",
                config={},
            ),
        )
        session.commit()
    return agent_id


class _FakeMem0Client:
    def __init__(self) -> None:
        self._items: list[dict[str, object]] = []

    def add(
        self,
        *,
        messages: list[dict[str, str]],
        metadata: dict[str, object],
        **_: object,
    ) -> dict[str, object]:
        item_id = str(uuid.uuid4())
        content = messages[0]["content"]
        self._items.insert(
            0,
            {
                "id": item_id,
                "memory": content,
                "metadata": {**metadata, "tag": "mem0"},
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        return {"id": item_id}

    def search(self, query: str, **_: object) -> list[dict[str, object]]:
        return [
            {**item, "score": 0.9}
            for item in self._items
            if query.lower() in str(item["memory"]).lower()
        ]

    def get_all(self, **_: object) -> list[dict[str, object]]:
        return list(self._items)

    def delete_all(self, **_: object) -> dict[str, int]:
        deleted_count = len(self._items)
        self._items = []
        return {"deleted_count": deleted_count}
