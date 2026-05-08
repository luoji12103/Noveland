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
from noveland.conversations.models import (
    ConversationParticipant,
    ConversationSession,
    ConversationTurn,
)
from noveland.core.models import RuntimeControlState
from noveland.core.settings import AppSettings
from noveland.events import InMemoryWorldEventPublisher
from noveland.events.models import WorldEventModel
from noveland.memory.models import (
    AgentMemoryItem,
    AgentProfileSnapshotModel,
    MemoryBackendProfile,
    MemoryRetrievalLog,
    MemoryWriteJob,
    MemoryWriteLog,
)
from noveland.narrative.models import NarrativeArtifact
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.services.runtime.agent_loop import AgentRuntimeOrchestrator
from noveland.services.runtime.daemon import RuntimeDaemon
from noveland.worlds.clock_service import WorldClockService
from noveland.worlds.models import (
    AgentPresenceState,
    DailyLifeEventCandidate,
    FactionProgressTrack,
    OffscreenEventQueueItem,
    OrganizationMembership,
    Scene,
    SceneLocationEdge,
    World,
    WorldClockStateModel,
    WorldClockTransitionModel,
    Worldline,
    WorldOrganization,
)
from noveland.worlds.worldlines import ensure_primary_worldline
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
    assert result.processed_memory_jobs == 1

    with Session(engine) as session:
        control = session.scalars(select(RuntimeControlState)).one()
        runs = session.scalars(select(AgentRuntimeRun)).all()
        memories = session.scalars(select(AgentMemoryItem)).all()
        artifacts = session.scalars(select(NarrativeArtifact)).all()
        observations = session.scalars(select(AgentObservation)).all()
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
    assert observations
    assert all(observation.runtime_use_count == 1 for observation in observations)
    assert all(observation.last_used_run_id == runs[0].id for observation in observations)
    assert [event.event_name for event in events] == [
        "world.clock_advanced",
        "calendar.entry_due",
        "agent.run_started",
        "agent.run_completed",
        "memory.item_created",
        "narrative.artifact_created",
    ]
    assert {event.actor_ref for event in events} == {"system:runtime"}
    assert {event.event_type for event in diagnostics} >= {
        "runtime.iteration_started",
        "runtime.iteration_finished",
        "agent.run_succeeded",
    }
    finished_diagnostic = next(
        event for event in diagnostics if event.event_type == "runtime.iteration_finished"
    )
    assert finished_diagnostic.details["processed_memory_jobs"] == 1


def test_run_agent_scopes_run_events_and_memory_jobs_to_fork_worldline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime-fork.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path}"
    engine = create_engine(database_url)
    _create_tables(engine)

    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id, "runtime-fork-world")
    agent_id = _seed_agent(engine, world_id, "guide")
    fork_id = _seed_fork_worldline(engine, world_id)
    _seed_provider_profile(engine, "runtime-profile", "runtime-ref")

    def fake_invoke_profile(
        self: ProviderProfileService,
        profile: object,
        prompt: str,
    ) -> ProviderCompletion:
        del self, profile, prompt
        return ProviderCompletion(text="Fork runtime response", raw_response={"ok": True})

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
    with Session(engine) as session:
        profile_service = ProviderProfileService(session, settings)
        run = AgentRuntimeOrchestrator(session, profile_service, settings).run_agent(
            world_id=world_id,
            worldline_id=fork_id,
            agent_id=agent_id,
            prompt_text="Fork prompt",
            trigger_source="manual",
            create_narrative_artifact=False,
        )
        run_model = session.get(AgentRuntimeRun, run.run_id)
        events = session.scalars(
            select(WorldEventModel).order_by(WorldEventModel.sequence.asc()),
        ).all()
        job = session.scalars(
            select(MemoryWriteJob).where(MemoryWriteJob.dedupe_key == f"agent-run:{run.run_id}"),
        ).one()
        run_model_worldline_id = None if run_model is None else run_model.worldline_id
        event_names = {event.event_name for event in events}
        event_worldline_ids = {event.worldline_id for event in events}
        job_worldline_id = job.worldline_id
        session.commit()

    assert run.worldline_id == fork_id
    assert run_model_worldline_id == fork_id
    assert event_names == {
        "agent.run_started",
        "agent.run_completed",
        "memory.item_created",
    }
    assert event_worldline_ids == {fork_id}
    assert job_worldline_id == fork_id


def test_run_agent_rejects_cross_world_worldline(tmp_path: Path) -> None:
    database_path = tmp_path / "runtime-cross-worldline.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path}"
    engine = create_engine(database_url)
    _create_tables(engine)

    user_id = _seed_user(engine)
    source_world_id = _seed_world(engine, user_id, "source-world")
    other_world_id = _seed_world(engine, user_id, "other-world")
    agent_id = _seed_agent(engine, source_world_id, "guide")
    other_worldline_id = _seed_fork_worldline(engine, other_world_id)
    _seed_provider_profile(engine, "runtime-profile", "runtime-ref")
    settings = AppSettings.model_construct(
        environment="local",
        database_url=database_url,
        nats_url="nats://localhost:4222",
        object_storage_root=tmp_path / "object-storage",
        provider_api_keys_json={"runtime-ref": "secret-key"},
    )

    with Session(engine) as session:
        profile_service = ProviderProfileService(session, settings)
        with pytest.raises(LookupError, match="Worldline not found"):
            AgentRuntimeOrchestrator(session, profile_service, settings).run_agent(
                world_id=source_world_id,
                worldline_id=other_worldline_id,
                agent_id=agent_id,
                prompt_text="Should fail",
                trigger_source="manual",
                create_narrative_artifact=False,
            )


def test_runtime_daemon_advances_running_auto_conversation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime-conversation.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path}"
    engine = create_engine(database_url)
    _create_tables(engine)

    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id, "conversation-world")
    agent_id = _seed_agent(engine, world_id, "speaker")
    fork_id = _seed_fork_worldline(engine, world_id)
    _seed_provider_profile(engine, "runtime-profile", "runtime-ref")
    _seed_runtime_control(engine, "running")
    _seed_running_conversation(engine, world_id, agent_id, fork_id)

    def fake_invoke_profile(
        self: ProviderProfileService,
        profile: object,
        prompt: str,
    ) -> ProviderCompletion:
        del self, profile
        return ProviderCompletion(
            text=f"Conversation response for: {prompt}",
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

    with Session(engine) as session:
        session_model = session.scalars(select(ConversationSession)).one()
        turns = session.scalars(
            select(ConversationTurn).order_by(ConversationTurn.turn_index.asc()),
        ).all()
        run_model = session.scalars(select(AgentRuntimeRun)).one()
        memories = session.scalars(select(AgentMemoryItem)).all()
        events = session.scalars(
            select(WorldEventModel).order_by(WorldEventModel.sequence),
        ).all()

    assert result.executed_runs == 1
    assert result.processed_memory_jobs == 1
    assert session_model.next_turn_index == 1
    assert session_model.worldline_id == fork_id
    assert len(turns) == 1
    assert turns[0].speaker_kind == "agent"
    assert turns[0].output_text is not None
    assert {event.actor_ref for event in events} == {"system:runtime"}
    assert turns[0].run_id is not None
    assert run_model.worldline_id == fork_id
    assert {memory.worldline_id for memory in memories} == {fork_id}
    assert {event.worldline_id for event in events} == {fork_id}


def _create_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, Scene.__table__),
        cast(Table, WorldClockStateModel.__table__),
        cast(Table, WorldClockTransitionModel.__table__),
        cast(Table, ProviderProfile.__table__),
        cast(Table, Agent.__table__),
        cast(Table, WorldOrganization.__table__),
        cast(Table, OrganizationMembership.__table__),
        cast(Table, FactionProgressTrack.__table__),
        cast(Table, SceneLocationEdge.__table__),
        cast(Table, AgentPersona.__table__),
        cast(Table, AgentObservation.__table__),
        cast(Table, AgentCalendarEntry.__table__),
        cast(Table, WorldScheduleRule.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationParticipant.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, RuntimeControlState.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, AgentPresenceState.__table__),
        cast(Table, DailyLifeEventCandidate.__table__),
        cast(Table, OffscreenEventQueueItem.__table__),
        cast(Table, AgentRuntimeRun.__table__),
        cast(Table, AgentMemoryItem.__table__),
        cast(Table, MemoryWriteJob.__table__),
        cast(Table, MemoryWriteLog.__table__),
        cast(Table, MemoryRetrievalLog.__table__),
        cast(Table, AgentProfileSnapshotModel.__table__),
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


def _seed_running_conversation(
    engine: Engine,
    world_id: uuid.UUID,
    agent_id: uuid.UUID,
    worldline_id: uuid.UUID | None = None,
) -> None:
    session_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            ConversationSession(
                id=session_id,
                world_id=world_id,
                worldline_id=worldline_id,
                scene_id=None,
                session_key="runtime-session",
                title="Runtime session",
                scope_type="world",
                mode="auto_dialogue",
                status="running",
                objective="Keep talking.",
                opening_prompt="Begin the conversation.",
                max_turns=3,
                next_turn_index=0,
                policy_config={
                    "error_policy": "retry_once_then_fail",
                    "max_consecutive_failed_turns": 2,
                    "loop_guard_window": 4,
                    "repeat_output_threshold": 3,
                },
                writer_config={
                    "provider_profile_id": None,
                    "auto_generate_on_complete": False,
                    "generate_summary": True,
                    "generate_chapter": True,
                },
                terminal_reason=None,
            ),
        )
        session.add(
            ConversationParticipant(
                id=uuid.uuid4(),
                session_id=session_id,
                agent_id=agent_id,
                turn_order=0,
                is_enabled=True,
            ),
        )
        session.commit()


def _seed_fork_worldline(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        primary = ensure_primary_worldline(session, world_id)
        fork = Worldline(
            world_id=world_id,
            worldline_key=f"fork-{uuid.uuid4().hex[:8]}",
            name="Fork",
            description="Forked test worldline",
            parent_worldline_id=primary.id,
            status="active",
            created_by_actor_ref="test:runtime",
            metadata_json={},
        )
        session.add(fork)
        session.commit()
        return fork.id
