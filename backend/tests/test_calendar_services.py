from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import cast

import pytest
from noveland.agents.models import Agent
from noveland.auth.models import User
from noveland.calendar import (
    CalendarEntryCreate,
    CalendarEntryStatus,
    CalendarService,
    ScheduleRuleCreate,
    ScheduleRuleKind,
)
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.worlds.models import World
from pydantic import ValidationError
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_calendar_entry_contract_requires_timezone_aware_datetimes() -> None:
    with pytest.raises(ValidationError):
        CalendarEntryCreate(
            world_id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            title="Naive",
            starts_at=datetime(2030, 1, 1),
        )


def test_calendar_service_creates_lists_and_resolves_due_entries() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id)
    agent_id = _seed_agent(engine, world_id)

    with Session(engine) as session:
        service = CalendarService(session)
        entry = service.create_entry(
            CalendarEntryCreate(
                world_id=world_id,
                agent_id=agent_id,
                title="Morning scene",
                starts_at=datetime(2030, 1, 1, 8, tzinfo=UTC),
                ends_at=datetime(2030, 1, 1, 9, tzinfo=UTC),
            ),
        )
        due = service.due_entries(world_id, datetime(2030, 1, 1, 8, 30, tzinfo=UTC))
        service.cancel_entry(session.get_one(AgentCalendarEntry, entry.id))
        cancelled_due = service.due_entries(world_id, datetime(2030, 1, 1, 8, 30, tzinfo=UTC))
        session.commit()

    assert entry.status is CalendarEntryStatus.ACTIVE
    assert [item.id for item in due] == [entry.id]
    assert cancelled_due == []


def test_schedule_rules_match_weekday_weekend_and_timetable() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id)

    with Session(engine) as session:
        service = CalendarService(session)
        service.create_rule(
            ScheduleRuleCreate(
                world_id=world_id,
                rule_key="weekday-rule",
                name="Weekdays",
                kind=ScheduleRuleKind.WEEKDAY,
            ),
        )
        service.create_rule(
            ScheduleRuleCreate(
                world_id=world_id,
                rule_key="weekend-rule",
                name="Weekends",
                kind=ScheduleRuleKind.WEEKEND,
            ),
        )
        service.create_rule(
            ScheduleRuleCreate(
                world_id=world_id,
                rule_key="hour-rule",
                name="Hour",
                kind=ScheduleRuleKind.TIMETABLE,
                config={"hours": [8]},
            ),
        )
        weekday_rules = service.due_rules(world_id, datetime(2030, 1, 1, 8, tzinfo=UTC))
        weekend_rules = service.due_rules(world_id, datetime(2030, 1, 5, 8, tzinfo=UTC))
        session.commit()

    assert {rule.rule_key for rule in weekday_rules} == {"weekday-rule", "hour-rule"}
    assert {rule.rule_key for rule in weekend_rules} == {"weekend-rule", "hour-rule"}


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
        cast(Table, AgentCalendarEntry.__table__),
        cast(Table, WorldScheduleRule.__table__),
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
