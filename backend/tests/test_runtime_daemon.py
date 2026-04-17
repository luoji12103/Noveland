from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest
from noveland.adapters import ProviderCompletion, ProviderProfileService
from noveland.adapters.models import ProviderProfile
from noveland.agents.models import Agent, AgentObservation, AgentPersona, AgentRuntimeRun
from noveland.auth.models import User
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.core.models import RuntimeControlState
from noveland.core.settings import AppSettings
from noveland.events import InMemoryWorldEventPublisher
from noveland.events.models import WorldEventModel
from noveland.memory.models import AgentMemoryItem
from noveland.narrative.models import NarrativeArtifact
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.services.runtime.daemon import RuntimeDaemon
from noveland.worlds.clock_service import WorldClockService
from noveland.worlds.models import World, WorldClockStateModel, WorldClockTransitionModel
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


def test_runtime_daemon_runs_due_agent_and_records_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime-daemon.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path}"
    engine = create_engine(database_url)
    _create_tables(engine)

    now = datetime.now(UTC)
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id, "runtime-world")
    agent_id = _seed_agent(engine, world_id, "guide")
    _seed_provider_profile(engine, "runtime-profile", "runtime-ref")
    _seed_due_calendar_entry(engine, world_id, agent_id, now - timedelta(hours=1))
    _seed_runtime_control(engine, "running")

    with Session(engine) as session:
        service = WorldClockService(session)
        service.ensure_initialized(world_id, now - timedelta(hours=2))
        service.resume(world_id, now - timedelta(hours=1), "1")
        session.commit()

    def fake_invoke_profile(
        self: ProviderProfileService,
        profile: object,
        prompt: str,
    ) -> ProviderCompletion:
        del self, profile
        return ProviderCompletion(
            text=f"Runtime response for: {prompt}",
            raw_response={"ok": True},
        )

    monkeypatch.setattr(ProviderProfileService, "invoke_profile", fake_invoke_profile)

    settings = AppSettings.model_construct(
        environment="local",
        database_url=database_url,
        nats_url="nats://localhost:4222",
        object_storage_root=tmp_path / "object-storage",
        provider_api_keys_json={"runtime-ref": "secret-key"},
        runtime_loop_interval_seconds=1,
        runtime_batch_limit=20,
    )
    daemon = RuntimeDaemon(settings, InMemoryWorldEventPublisher())

    result = daemon.run_iteration()

    assert result.desired_state == "running"
    assert result.advanced_worlds == 1
    assert result.executed_runs == 1

    with Session(engine) as session:
        control = session.scalars(select(RuntimeControlState)).one()
        runs = session.scalars(select(AgentRuntimeRun)).all()
        memories = session.scalars(select(AgentMemoryItem)).all()
        artifacts = session.scalars(select(NarrativeArtifact)).all()
        events = session.scalars(
            select(WorldEventModel).order_by(WorldEventModel.sequence),
        ).all()
        diagnostics = session.scalars(select(RuntimeDiagnosticEvent)).all()

    assert control.last_heartbeat_at is not None
    assert control.last_run_started_at is not None
    assert control.last_run_finished_at is not None
    assert control.last_error is None
    assert len(runs) == 1
    assert runs[0].status == "succeeded"
    assert runs[0].response_text is not None
    assert len(memories) == 1
    assert memories[0].content.startswith("Runtime response for:")
    assert len(artifacts) == 1
    assert artifacts[0].title == "guide runtime note"
    assert [event.event_name for event in events] == [
        "world.clock_advanced",
        "calendar.entry_due",
        "agent.run_started",
        "agent.run_completed",
        "memory.item_created",
        "narrative.artifact_created",
    ]
    assert {event.event_type for event in diagnostics} >= {
        "runtime.iteration_started",
        "runtime.iteration_finished",
        "agent.run_succeeded",
    }


def _create_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, World.__table__),
        cast(Table, WorldClockStateModel.__table__),
        cast(Table, WorldClockTransitionModel.__table__),
        cast(Table, ProviderProfile.__table__),
        cast(Table, Agent.__table__),
        cast(Table, AgentPersona.__table__),
        cast(Table, AgentObservation.__table__),
        cast(Table, AgentCalendarEntry.__table__),
        cast(Table, WorldScheduleRule.__table__),
        cast(Table, RuntimeControlState.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, AgentRuntimeRun.__table__),
        cast(Table, AgentMemoryItem.__table__),
        cast(Table, NarrativeArtifact.__table__),
        cast(Table, RuntimeDiagnosticEvent.__table__),
    ):
        table.create(engine)


def _seed_user(engine: Engine) -> uuid.UUID:
    user_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(User(id=user_id, email="runtime@example.test", display_name="Runtime User"))
        session.commit()
    return user_id


def _seed_world(engine: Engine, owner_user_id: uuid.UUID, slug: str) -> uuid.UUID:
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=owner_user_id,
                slug=slug,
                name=slug,
                rules_config={},
                is_active=True,
            ),
        )
        session.commit()
    return world_id


def _seed_agent(engine: Engine, world_id: uuid.UUID, agent_key: str) -> uuid.UUID:
    agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key=agent_key,
                display_name=agent_key,
                kind="role_agent",
                config={},
                is_enabled=True,
            ),
        )
        session.commit()
    return agent_id


def _seed_provider_profile(engine: Engine, profile_key: str, api_key_ref: str) -> None:
    with Session(engine) as session:
        session.add(
            ProviderProfile(
                profile_key=profile_key,
                name=profile_key,
                provider_type="openai_compatible",
                base_url="https://api.example.test/v1",
                model_name="test-model",
                capabilities={},
                api_key_ref=api_key_ref,
                is_enabled=True,
            ),
        )
        session.commit()


def _seed_due_calendar_entry(
    engine: Engine,
    world_id: uuid.UUID,
    agent_id: uuid.UUID,
    starts_at: datetime,
) -> None:
    with Session(engine) as session:
        session.add(
            AgentCalendarEntry(
                world_id=world_id,
                agent_id=agent_id,
                title="Scheduled run",
                description=None,
                starts_at=starts_at,
                ends_at=None,
                recurrence_rule=None,
                status="active",
                metadata_json={},
            ),
        )
        session.commit()


def _seed_runtime_control(engine: Engine, desired_state: str) -> None:
    with Session(engine) as session:
        session.add(
            RuntimeControlState(
                control_key="default",
                desired_state=desired_state,
            ),
        )
        session.commit()
