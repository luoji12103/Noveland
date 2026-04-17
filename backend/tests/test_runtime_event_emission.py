from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import cast

import pytest
from noveland.adapters.models import ProviderProfile
from noveland.agents.models import Agent, AgentRuntimeRun
from noveland.auth.models import User
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.events import (
    EventPublishError,
    InMemoryWorldEventPublisher,
    WorldEventEnvelope,
    WorldEventPublisher,
    subject_for_world,
)
from noveland.events.models import WorldEventModel
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.services.runtime.clock_tick import (
    CLOCK_ADVANCED_EVENT_NAME,
    RuntimeClockTicker,
    RuntimeEventPublishError,
)
from noveland.worlds.clock_service import WorldClockService
from noveland.worlds.models import Scene, World, WorldClockStateModel, WorldClockTransitionModel
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_runtime_tick_advances_running_clocks_and_publishes_event() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    running_world_id = _seed_world(engine, user_id, "running-world")
    paused_world_id = _seed_world(engine, user_id, "paused-world")

    with Session(engine) as session:
        service = WorldClockService(session)
        service.ensure_initialized(running_world_id, datetime(2026, 4, 17, 12, tzinfo=UTC))
        service.resume(running_world_id, datetime(2026, 4, 17, 12, 1, tzinfo=UTC), "2")
        service.ensure_initialized(paused_world_id, datetime(2026, 4, 17, 12, tzinfo=UTC))
        session.commit()

    publisher = InMemoryWorldEventPublisher()
    with Session(engine) as session:
        result = RuntimeClockTicker(session, publisher).run_once(
            datetime(2026, 4, 17, 12, 3, tzinfo=UTC),
        )

    with Session(engine) as session:
        events = session.scalars(select(WorldEventModel).order_by(WorldEventModel.sequence)).all()
        running_clock = session.scalars(
            select(WorldClockStateModel).where(WorldClockStateModel.world_id == running_world_id),
        ).one()
        paused_clock = session.scalars(
            select(WorldClockStateModel).where(WorldClockStateModel.world_id == paused_world_id),
        ).one()

    assert result.advanced_worlds == 1
    assert result.published_events == 1
    assert len(events) == 1
    assert events[0].event_name == CLOCK_ADVANCED_EVENT_NAME
    assert events[0].world_id == running_world_id
    assert events[0].sequence == 1
    assert events[0].payload["revision"] == 2
    assert running_clock.revision == 2
    assert paused_clock.revision == 0
    assert [item.subject for item in publisher.published] == [subject_for_world(running_world_id)]
    assert publisher.published[0].envelope.event_name == CLOCK_ADVANCED_EVENT_NAME
    assert publisher.published[0].envelope.payload["status"] == "running"


def test_runtime_tick_keeps_event_log_when_publish_fails() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id, "publish-failure")

    with Session(engine) as session:
        service = WorldClockService(session)
        service.ensure_initialized(world_id, datetime(2026, 4, 17, 12, tzinfo=UTC))
        service.resume(world_id, datetime(2026, 4, 17, 12, 1, tzinfo=UTC))
        session.commit()

    with Session(engine) as session, pytest.raises(RuntimeEventPublishError) as exc_info:
        RuntimeClockTicker(session, FailingPublisher()).run_once(
            datetime(2026, 4, 17, 12, 2, tzinfo=UTC),
        )

    with Session(engine) as session:
        events = session.scalars(select(WorldEventModel)).all()
        diagnostics = session.scalars(select(RuntimeDiagnosticEvent)).all()

    assert len(exc_info.value.failures) == 1
    assert len(events) == 1
    assert events[0].event_name == CLOCK_ADVANCED_EVENT_NAME
    assert diagnostics[0].event_type == "event_publisher.publish_failed"
    assert diagnostics[0].component == "event_publisher"


class FailingPublisher(WorldEventPublisher):
    def publish(self, envelope: WorldEventEnvelope) -> None:
        raise EventPublishError(f"blocked {envelope.subject}")


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        cast(Table, User.__table__),
        cast(Table, World.__table__),
        cast(Table, Scene.__table__),
        cast(Table, ProviderProfile.__table__),
        cast(Table, Agent.__table__),
        cast(Table, WorldScheduleRule.__table__),
        cast(Table, WorldClockStateModel.__table__),
        cast(Table, WorldClockTransitionModel.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, AgentCalendarEntry.__table__),
        cast(Table, AgentRuntimeRun.__table__),
        cast(Table, RuntimeDiagnosticEvent.__table__),
    ):
        table.create(engine)
    return engine


def _seed_user(engine: Engine) -> uuid.UUID:
    user_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(User(id=user_id, email=f"{user_id}@example.test", display_name="User"))
        session.commit()
    return user_id


def _seed_world(engine: Engine, user_id: uuid.UUID, slug: str) -> uuid.UUID:
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug=slug,
                name=slug.replace("-", " ").title(),
                rules_config={},
            ),
        )
        session.commit()
    return world_id
