from __future__ import annotations

import uuid
from typing import cast

import pytest
from noveland.agents.models import Agent
from noveland.auth.models import User
from noveland.events.models import WorldEventModel
from noveland.memory import (
    VECTOR_DIMENSIONS,
    LocalPgvectorMemoryBackend,
    MemoryItemCreate,
    MemorySearchQuery,
)
from noveland.memory.models import AgentMemoryItem
from noveland.worlds.models import World
from pydantic import ValidationError
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_memory_contract_requires_expected_embedding_dimensions() -> None:
    with pytest.raises(ValidationError):
        MemoryItemCreate(
            world_id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            content="short",
            embedding=[0.1],
        )


def test_local_pgvector_memory_backend_adds_lists_searches_and_disables() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id)
    agent_id = _seed_agent(engine, world_id)

    with Session(engine) as session:
        backend = LocalPgvectorMemoryBackend(session)
        first = backend.add(
            MemoryItemCreate(
                world_id=world_id,
                agent_id=agent_id,
                content="likes green tea",
                embedding=_embedding(1.0),
            ),
        )
        second = backend.add(
            MemoryItemCreate(
                world_id=world_id,
                agent_id=agent_id,
                content="likes red apples",
                embedding=_embedding(0.1),
            ),
        )
        listed = backend.list(world_id, agent_id)
        searched = backend.search(
            MemorySearchQuery(world_id=world_id, agent_id=agent_id, embedding=_embedding(1.0)),
        )
        backend.disable(first.id)
        after_disable = backend.list(world_id, agent_id)
        session.commit()

    assert {item.id for item in listed} == {first.id, second.id}
    assert searched[0].id == first.id
    assert searched[0].score is not None
    assert [item.id for item in after_disable] == [second.id]


def _embedding(seed: float) -> list[float]:
    return [seed, *([0.0] * (VECTOR_DIMENSIONS - 1))]


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
        cast(Table, AgentMemoryItem.__table__),
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
