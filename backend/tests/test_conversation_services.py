from __future__ import annotations

import uuid
from typing import cast

import pytest
from noveland.adapters.models import ProviderProfile
from noveland.agents.models import Agent, AgentRuntimeRun
from noveland.auth.models import User
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.conversations import (
    ConversationErrorPolicy,
    ConversationMode,
    ConversationParticipantDefinition,
    ConversationPolicyConfig,
    ConversationScopeType,
    ConversationSeed,
    ConversationService,
    ConversationSessionCreate,
    ConversationSessionStatus,
    ConversationSpeakerPolicyMode,
    ConversationTerminalReason,
    ConversationWriterConfig,
)
from noveland.conversations.errors import ConversationStateError
from noveland.conversations.models import (
    ConversationParticipant,
    ConversationSession,
    ConversationTurn,
)
from noveland.events.models import WorldEventModel
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.worlds.models import Scene, World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_manual_chain_round_robin_and_completion() -> None:
    engine = _engine()
    world_id = _seed_world(engine)
    scene_id = _seed_scene(engine, world_id, "hall")
    first_agent_id = _seed_agent(engine, world_id, "first", scene_id)
    second_agent_id = _seed_agent(engine, world_id, "second", scene_id)

    with Session(engine) as session:
        service = ConversationService(session)
        created = service.create_session(
            ConversationSessionCreate(
                world_id=world_id,
                scene_id=scene_id,
                session_key="scene-chat",
                title="Scene chat",
                scope_type=ConversationScopeType.SCENE,
                mode=ConversationMode.MANUAL_CHAIN,
                objective="Coordinate the next move.",
                opening_prompt="Start from the operator seed.",
                max_turns=2,
                policy=_default_policy(),
                writer_config=_default_writer_config(),
            ),
        )
        service.replace_participants(
            world_id,
            created.id,
            [
                ConversationParticipantDefinition(agent_id=first_agent_id, turn_order=0),
                ConversationParticipantDefinition(agent_id=second_agent_id, turn_order=1),
            ],
        )
        service.seed_session(
            world_id,
            created.id,
            ConversationSeed(input_text="Operator seed"),
        )

        first_prepared = service.prepare_next_turn(world_id, created.id)
        assert first_prepared.speaker_agent_id == first_agent_id
        assert "Operator seed" in first_prepared.prompt_text

        first_result = service.finalize_turn(
            first_prepared,
            response_text="First response",
            run_id=None,
            diagnostics={},
            succeeded=True,
        )
        assert first_result.session.status.value == "draft"
        assert first_result.session.next_turn_index == 1

        second_prepared = service.prepare_next_turn(world_id, created.id)
        assert second_prepared.speaker_agent_id == second_agent_id
        assert "First response" in second_prepared.prompt_text

        second_result = service.finalize_turn(
            second_prepared,
            response_text="Second response",
            run_id=None,
            diagnostics={},
            succeeded=True,
        )
        turns = service.list_turns(world_id, created.id)

    assert second_result.session.status == ConversationSessionStatus.COMPLETED
    assert second_result.session.terminal_reason == ConversationTerminalReason.MAX_TURNS_REACHED
    assert [turn.turn_index for turn in turns] == [0, 1, 2]
    assert [turn.speaker_kind.value for turn in turns] == ["operator", "agent", "agent"]
    assert turns[1].output_text == "First response"
    assert turns[2].output_text == "Second response"


def test_conversation_service_scopes_session_and_events_to_worldline() -> None:
    engine = _engine()
    world_id = _seed_world(engine)
    fork_id = _seed_fork_worldline(engine, world_id)
    first_agent_id = _seed_agent(engine, world_id, "first")

    with Session(engine) as session:
        service = ConversationService(session)
        created = service.create_session(
            ConversationSessionCreate(
                world_id=world_id,
                worldline_id=fork_id,
                session_key="fork-chat",
                title="Fork chat",
                scope_type=ConversationScopeType.WORLD,
                mode=ConversationMode.MANUAL_CHAIN,
                max_turns=1,
                policy=_default_policy(),
                writer_config=_default_writer_config(),
            ),
        )
        service.replace_participants(
            world_id,
            created.id,
            [ConversationParticipantDefinition(agent_id=first_agent_id, turn_order=0)],
        )
        prepared = service.prepare_next_turn(world_id, created.id)
        service.finalize_turn(
            prepared,
            response_text="Fork response",
            run_id=None,
            diagnostics={},
            succeeded=True,
        )
        events = session.scalars(
            select(WorldEventModel).order_by(WorldEventModel.sequence.asc()),
        ).all()

    assert created.worldline_id == fork_id
    assert {event.event_name for event in events} >= {
        "conversation.session_started",
        "conversation.turn_completed",
        "conversation.session_completed",
    }
    assert {event.worldline_id for event in events} == {fork_id}


def test_prepare_next_turn_skips_disabled_participant_and_marks_failed_without_available_agent(
) -> None:
    engine = _engine()
    world_id = _seed_world(engine)
    first_agent_id = _seed_agent(engine, world_id, "first")
    second_agent_id = _seed_agent(engine, world_id, "second")

    with Session(engine) as session:
        service = ConversationService(session)
        created = service.create_session(
            ConversationSessionCreate(
                world_id=world_id,
                session_key="world-chat",
                title="World chat",
                scope_type=ConversationScopeType.WORLD,
                mode=ConversationMode.MANUAL_CHAIN,
                max_turns=3,
                policy=_default_policy(),
                writer_config=_default_writer_config(),
            ),
        )
        service.replace_participants(
            world_id,
            created.id,
            [
                ConversationParticipantDefinition(
                    agent_id=first_agent_id,
                    turn_order=0,
                    is_enabled=False,
                ),
                ConversationParticipantDefinition(agent_id=second_agent_id, turn_order=1),
            ],
        )

        prepared = service.prepare_next_turn(world_id, created.id)
        assert prepared.speaker_agent_id == second_agent_id

        service.replace_participants(world_id, created.id, [])
        with pytest.raises(ConversationStateError, match="no enabled participants"):
            service.prepare_next_turn(world_id, created.id)
        refreshed = service.get_session(world_id, created.id)

    assert refreshed.status == ConversationSessionStatus.FAILED
    assert refreshed.terminal_reason == ConversationTerminalReason.NO_ENABLED_PARTICIPANTS


def test_speaker_policy_preview_and_least_recent_selection() -> None:
    engine = _engine()
    world_id = _seed_world(engine)
    first_agent_id = _seed_agent(engine, world_id, "first")
    second_agent_id = _seed_agent(engine, world_id, "second")

    with Session(engine) as session:
        service = ConversationService(session)
        created = service.create_session(
            ConversationSessionCreate(
                world_id=world_id,
                session_key="least-recent-world",
                title="Least recent world",
                scope_type=ConversationScopeType.WORLD,
                mode=ConversationMode.MANUAL_CHAIN,
                max_turns=4,
                policy=ConversationPolicyConfig(
                    error_policy=ConversationErrorPolicy.FAIL_SESSION,
                    max_consecutive_failed_turns=2,
                    loop_guard_window=4,
                    repeat_output_threshold=3,
                    speaker_policy=ConversationSpeakerPolicyMode.LEAST_RECENT,
                ),
                writer_config=_default_writer_config(),
            ),
        )
        service.replace_participants(
            world_id,
            created.id,
            [
                ConversationParticipantDefinition(agent_id=first_agent_id, turn_order=0),
                ConversationParticipantDefinition(agent_id=second_agent_id, turn_order=1),
            ],
        )

        initial_preview = service.preview_next_speaker(world_id, created.id)
        assert initial_preview.policy_mode == ConversationSpeakerPolicyMode.LEAST_RECENT
        assert initial_preview.selected_agent_id == first_agent_id
        first_prepared = service.prepare_next_turn(world_id, created.id)
        service.finalize_turn(
            first_prepared,
            response_text="First speaks",
            run_id=None,
            diagnostics={},
            succeeded=True,
        )

        next_preview = service.preview_next_speaker(world_id, created.id)
        next_prepared = service.prepare_next_turn(world_id, created.id)

    assert next_preview.selected_agent_id == second_agent_id
    assert next_prepared.speaker_agent_id == second_agent_id


def test_min_enabled_participants_guardrail_marks_failed() -> None:
    engine = _engine()
    world_id = _seed_world(engine)
    agent_id = _seed_agent(engine, world_id, "solo")

    with Session(engine) as session:
        service = ConversationService(session)
        created = service.create_session(
            ConversationSessionCreate(
                world_id=world_id,
                session_key="guardrail-world",
                title="Guardrail world",
                scope_type=ConversationScopeType.WORLD,
                mode=ConversationMode.MANUAL_CHAIN,
                max_turns=4,
                policy=ConversationPolicyConfig(
                    error_policy=ConversationErrorPolicy.FAIL_SESSION,
                    max_consecutive_failed_turns=2,
                    loop_guard_window=4,
                    repeat_output_threshold=3,
                    min_enabled_participants=2,
                ),
                writer_config=_default_writer_config(),
            ),
        )
        service.replace_participants(
            world_id,
            created.id,
            [ConversationParticipantDefinition(agent_id=agent_id, turn_order=0)],
        )

        with pytest.raises(ConversationStateError, match="minimum enabled participants"):
            service.prepare_next_turn(world_id, created.id)
        refreshed = service.get_session(world_id, created.id)

    assert refreshed.status == ConversationSessionStatus.FAILED
    assert refreshed.terminal_reason == ConversationTerminalReason.NO_ENABLED_PARTICIPANTS


def test_skip_policy_and_failure_threshold_mark_failed() -> None:
    engine = _engine()
    world_id = _seed_world(engine)
    agent_id = _seed_agent(engine, world_id, "speaker")

    with Session(engine) as session:
        service = ConversationService(session)
        created = service.create_session(
            ConversationSessionCreate(
                world_id=world_id,
                session_key="skip-world",
                title="Skip world",
                scope_type=ConversationScopeType.WORLD,
                mode=ConversationMode.MANUAL_CHAIN,
                max_turns=4,
                policy=ConversationPolicyConfig(
                    error_policy=ConversationErrorPolicy.SKIP_TURN,
                    max_consecutive_failed_turns=2,
                    loop_guard_window=4,
                    repeat_output_threshold=3,
                ),
                writer_config=_default_writer_config(),
            ),
        )
        service.replace_participants(
            world_id,
            created.id,
            [ConversationParticipantDefinition(agent_id=agent_id, turn_order=0)],
        )

        first_prepared = service.prepare_next_turn(world_id, created.id)
        first_result = service.finalize_turn(
            first_prepared,
            response_text=None,
            run_id=None,
            diagnostics={"error": "upstream timeout"},
            succeeded=False,
            error_text="upstream timeout",
        )

        second_prepared = service.prepare_next_turn(world_id, created.id)
        second_result = service.finalize_turn(
            second_prepared,
            response_text=None,
            run_id=None,
            diagnostics={"error": "upstream timeout"},
            succeeded=False,
            error_text="upstream timeout",
        )
        turns = service.list_turns(world_id, created.id)

    assert first_result.turn.status.value == "skipped"
    assert first_result.session.status == ConversationSessionStatus.DRAFT
    assert second_result.turn.status.value == "skipped"
    assert second_result.session.status == ConversationSessionStatus.FAILED
    assert (
        second_result.session.terminal_reason
        == ConversationTerminalReason.CONSECUTIVE_FAILURES_EXCEEDED
    )
    assert [turn.status.value for turn in turns] == ["skipped", "skipped"]


def test_loop_guard_stops_repeated_output_session() -> None:
    engine = _engine()
    world_id = _seed_world(engine)
    agent_id = _seed_agent(engine, world_id, "speaker")

    with Session(engine) as session:
        service = ConversationService(session)
        created = service.create_session(
            ConversationSessionCreate(
                world_id=world_id,
                session_key="loop-world",
                title="Loop world",
                scope_type=ConversationScopeType.WORLD,
                mode=ConversationMode.MANUAL_CHAIN,
                max_turns=6,
                policy=ConversationPolicyConfig(
                    error_policy=ConversationErrorPolicy.FAIL_SESSION,
                    max_consecutive_failed_turns=2,
                    loop_guard_window=4,
                    repeat_output_threshold=2,
                ),
                writer_config=_default_writer_config(),
            ),
        )
        service.replace_participants(
            world_id,
            created.id,
            [ConversationParticipantDefinition(agent_id=agent_id, turn_order=0)],
        )

        first_prepared = service.prepare_next_turn(world_id, created.id)
        first_result = service.finalize_turn(
            first_prepared,
            response_text="Same answer",
            run_id=None,
            diagnostics={},
            succeeded=True,
        )
        second_prepared = service.prepare_next_turn(world_id, created.id)
        second_result = service.finalize_turn(
            second_prepared,
            response_text="Same answer",
            run_id=None,
            diagnostics={},
            succeeded=True,
        )

    assert first_result.session.status == ConversationSessionStatus.DRAFT
    assert second_result.session.status == ConversationSessionStatus.STOPPED
    assert (
        second_result.session.terminal_reason
        == ConversationTerminalReason.LOOP_GUARD_REPEATED_OUTPUT
    )


def _default_policy() -> ConversationPolicyConfig:
    return ConversationPolicyConfig(
        error_policy=ConversationErrorPolicy.RETRY_ONCE_THEN_FAIL,
        max_consecutive_failed_turns=2,
        loop_guard_window=4,
        repeat_output_threshold=3,
    )


def _default_writer_config() -> ConversationWriterConfig:
    return ConversationWriterConfig(
        provider_profile_id=None,
        auto_generate_on_complete=False,
        generate_summary=True,
        generate_chapter=True,
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
        cast(Table, Worldline.__table__),
        cast(Table, Scene.__table__),
        cast(Table, ProviderProfile.__table__),
        cast(Table, Agent.__table__),
        cast(Table, AgentCalendarEntry.__table__),
        cast(Table, WorldScheduleRule.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, RuntimeDiagnosticEvent.__table__),
        cast(Table, AgentRuntimeRun.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationParticipant.__table__),
        cast(Table, ConversationTurn.__table__),
    ):
        table.create(engine)
    return engine


def _seed_world(engine: Engine) -> uuid.UUID:
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=uuid.uuid4(),
                slug=f"world-{world_id.hex[:8]}",
                name="Test World",
                rules_config={},
                is_active=True,
            ),
        )
        session.commit()
    return world_id


def _seed_scene(engine: Engine, world_id: uuid.UUID, scene_key: str) -> uuid.UUID:
    scene_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Scene(
                id=scene_id,
                world_id=world_id,
                scene_key=scene_key,
                name=scene_key.title(),
                description=None,
                is_active=True,
            ),
        )
        session.commit()
    return scene_id


def _seed_agent(
    engine: Engine,
    world_id: uuid.UUID,
    agent_key: str,
    scene_id: uuid.UUID | None = None,
) -> uuid.UUID:
    agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                home_scene_id=scene_id,
                agent_key=agent_key,
                display_name=agent_key.title(),
                kind="role_agent",
                config={},
                is_enabled=True,
            ),
        )
        session.commit()
    return agent_id


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
            created_by_actor_ref="test:conversation",
            metadata_json={},
        )
        session.add(fork)
        session.commit()
        return fork.id
