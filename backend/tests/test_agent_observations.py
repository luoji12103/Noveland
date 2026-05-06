from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import cast

from noveland.agents import (
    AgentObservationCreate,
    AgentObservationService,
    AgentPersonaService,
    AgentPersonaUpsert,
)
from noveland.agents.models import Agent, AgentObservation, AgentPersona
from noveland.auth.models import User
from noveland.events import WorldEventAppend, WorldEventStore
from noveland.events.models import WorldEventModel
from noveland.worlds.models import World, Worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


def test_persona_upsert_and_observation_refresh_are_agent_scoped_and_idempotent() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    _create_tables(engine)
    user_id, world_id, agent_id, other_agent_id = _seed_world_agents(engine)

    with Session(engine) as session:
        persona = AgentPersonaService(session).upsert(
            AgentPersonaUpsert(
                world_id=world_id,
                agent_id=agent_id,
                persona_text="Careful archivist.",
                behavior_policy={"tone": "precise"},
            ),
        )
        assert persona.persona_text == "Careful archivist."

        WorldEventStore(session).append_event(
            WorldEventAppend(
                world_id=world_id,
                event_name="world.clock_advanced",
                payload={"revision": 1},
                wall_time=datetime(2026, 4, 17, 12, tzinfo=UTC),
                actor_ref="system:test",
            ),
        )
        WorldEventStore(session).append_event(
            WorldEventAppend(
                world_id=world_id,
                event_name="agent.run_completed",
                payload={"agent_id": str(agent_id)},
                wall_time=datetime(2026, 4, 17, 12, 1, tzinfo=UTC),
                actor_ref="system:test",
            ),
        )
        WorldEventStore(session).append_event(
            WorldEventAppend(
                world_id=world_id,
                event_name="agent.run_completed",
                payload={"agent_id": str(other_agent_id)},
                wall_time=datetime(2026, 4, 17, 12, 2, tzinfo=UTC),
                actor_ref="system:test",
            ),
        )

        service = AgentObservationService(session)
        first_refresh = service.refresh_from_events(world_id, agent_id)
        second_refresh = service.refresh_from_events(world_id, agent_id)
        manual = service.create(
            AgentObservationCreate(
                world_id=world_id,
                agent_id=agent_id,
                observation_type="manual",
                content="Operator note",
            ),
        )
        consumed_count = service.mark_consumed([manual.id])
        observations = session.scalars(select(AgentObservation)).all()

        assert user_id
        assert first_refresh.created_count == 2
        assert second_refresh.created_count == 0
        assert {observation.observation_type for observation in first_refresh.observations} == {
            "agent.run_completed",
            "world.clock_advanced",
        }
        assert consumed_count == 1
        assert len(observations) == 3
        consumed_observation = session.get(AgentObservation, manual.id)
        assert consumed_observation is not None
        assert consumed_observation.consumed_at is not None
        assert consumed_observation.review_status == "unreviewed"
        assert consumed_observation.runtime_use_count == 1


def _create_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, Agent.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, AgentPersona.__table__),
        cast(Table, AgentObservation.__table__),
    ):
        table.create(engine)


def _seed_world_agents(engine: Engine) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    other_agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(User(id=user_id, email="owner@example.test", display_name="Owner"))
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug="observed-world",
                name="Observed World",
                rules_config={},
                is_active=True,
            ),
        )
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key="guide",
                display_name="Guide",
                kind="role_agent",
                config={},
                is_enabled=True,
            ),
        )
        session.add(
            Agent(
                id=other_agent_id,
                world_id=world_id,
                agent_key="other",
                display_name="Other",
                kind="role_agent",
                config={},
                is_enabled=True,
            ),
        )
        session.commit()
    return user_id, world_id, agent_id, other_agent_id
