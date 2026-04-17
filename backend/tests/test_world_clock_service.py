from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import cast

from noveland.auth.models import User
from noveland.worlds.clock_service import WorldClockService
from noveland.worlds.models import World, WorldClockStateModel, WorldClockTransitionModel
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_clock_service_initializes_missing_world_clock() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id)
    initialized_at = datetime(2026, 4, 17, 12, tzinfo=UTC)

    with Session(engine) as session:
        state = WorldClockService(session).ensure_initialized(
            world_id,
            initialized_at,
            actor_ref=f"user:{user_id}",
            reason="test init",
        )
        session.commit()

    with Session(engine) as session:
        transitions = session.scalars(
            select(WorldClockTransitionModel).where(WorldClockTransitionModel.world_id == world_id),
        ).all()

    assert state.status.value == "paused"
    assert state.current_world_time == initialized_at
    assert state.revision == 0
    assert len(transitions) == 1
    assert transitions[0].transition_type == "initialize"
    assert transitions[0].new_revision == 0


def test_clock_service_persists_resume_advance_pause_skip() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id)

    with Session(engine) as session:
        service = WorldClockService(session)
        service.ensure_initialized(world_id, datetime(2026, 4, 17, 12, tzinfo=UTC))
        resume = service.resume(world_id, datetime(2026, 4, 17, 12, 1, tzinfo=UTC), "3")
        advance = service.advance(world_id, datetime(2026, 4, 17, 12, 3, tzinfo=UTC))
        pause = service.pause(world_id, datetime(2026, 4, 17, 12, 4, tzinfo=UTC))
        skip = service.skip(
            world_id,
            datetime(2030, 1, 1, tzinfo=UTC),
            datetime(2026, 4, 17, 12, 5, tzinfo=UTC),
        )
        session.commit()

    with Session(engine) as session:
        state = session.scalars(
            select(WorldClockStateModel).where(WorldClockStateModel.world_id == world_id),
        ).one()
        transition_count = len(
            session.scalars(
                select(WorldClockTransitionModel).where(
                    WorldClockTransitionModel.world_id == world_id,
                ),
            ).all(),
        )

    assert resume.state.status.value == "running"
    assert advance.state.revision == 2
    assert pause.state.status.value == "paused"
    assert skip.state.current_world_time == datetime(2030, 1, 1, tzinfo=UTC)
    assert state.revision == 4
    assert transition_count == 5


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        cast(Table, User.__table__),
        cast(Table, World.__table__),
        cast(Table, WorldClockStateModel.__table__),
        cast(Table, WorldClockTransitionModel.__table__),
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
