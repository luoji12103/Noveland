from __future__ import annotations

import uuid
from typing import cast

from noveland.adapters import ProviderCompletion, ProviderProfileRecord, ProviderType
from noveland.agents.models import Agent
from noveland.auth.models import User
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
    ConversationWriterConfig,
)
from noveland.conversations.models import (
    ConversationParticipant,
    ConversationSession,
    ConversationTurn,
)
from noveland.events.models import WorldEventModel
from noveland.narrative import (
    ConversationNarrativeArtifactSet,
    ConversationNarrativeGenerate,
    ConversationNarrativeWriterService,
    NarrativeArtifact,
    NarrativeGenerationMode,
)
from noveland.worlds.models import Scene, World
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_writer_generates_summary_then_chapter() -> None:
    engine = _engine()
    world_id = _seed_world(engine)
    scene_id = _seed_scene(engine, world_id)
    agent_id = _seed_agent(engine, world_id, scene_id)
    profile_service = FakeProfileService()

    with Session(engine) as session:
        conversation_id = _seed_conversation(
            session,
            world_id=world_id,
            scene_id=scene_id,
            agent_id=agent_id,
            writer_config=ConversationWriterConfig(
                provider_profile_id=profile_service.profile.id,
                auto_generate_on_complete=False,
                generate_summary=True,
                generate_chapter=True,
            ),
        )
        artifacts = ConversationNarrativeWriterService(
            session,
            profile_service,
        ).generate_for_conversation(
            ConversationNarrativeGenerate(
                world_id=world_id,
                conversation_id=conversation_id,
                artifact_set=ConversationNarrativeArtifactSet.SUMMARY_AND_CHAPTER,
                provider_profile_id=profile_service.profile.id,
                generation_mode=NarrativeGenerationMode.MANUAL,
            ),
        )

    assert [artifact.artifact_kind.value for artifact in artifacts] == [
        "conversation_summary",
        "chapter_draft",
    ]
    assert profile_service.prompts[0].startswith(
        "Write a concise but complete conversation summary.",
    )
    assert "Conversation summary output" in profile_service.prompts[1]
    assert artifacts[0].metadata["generation_mode"] == "manual"
    assert artifacts[0].metadata["source_turn_count"] == 2
    assert artifacts[0].source_conversation_id == conversation_id


def test_auto_generate_is_idempotent_for_completed_session() -> None:
    engine = _engine()
    world_id = _seed_world(engine)
    scene_id = _seed_scene(engine, world_id)
    agent_id = _seed_agent(engine, world_id, scene_id)
    profile_service = FakeProfileService()

    with Session(engine) as session:
        conversation_id = _seed_conversation(
            session,
            world_id=world_id,
            scene_id=scene_id,
            agent_id=agent_id,
            writer_config=ConversationWriterConfig(
                provider_profile_id=profile_service.profile.id,
                auto_generate_on_complete=True,
                generate_summary=True,
                generate_chapter=True,
            ),
        )
        model = session.get(ConversationSession, conversation_id)
        assert model is not None
        model.status = ConversationSessionStatus.COMPLETED.value
        session.flush()

        writer = ConversationNarrativeWriterService(session, profile_service)
        first = writer.auto_generate_for_completed_conversation(world_id, conversation_id)
        second = writer.auto_generate_for_completed_conversation(world_id, conversation_id)
        stored = session.scalars(select(NarrativeArtifact)).all()

    assert len(first) == 2
    assert len(second) == 2
    assert len(stored) == 2
    assert len(profile_service.prompts) == 2


class FakeProfileService:
    def __init__(self) -> None:
        self.profile = ProviderProfileRecord(
            id=uuid.uuid4(),
            profile_key="writer-profile",
            name="Writer Profile",
            provider_type=ProviderType.OPENAI_COMPATIBLE,
            base_url="https://api.example.test/v1",
            model_name="test-model",
            capabilities={},
            api_key_ref="writer-ref",
            timeout_seconds=20,
            retry_attempts=1,
            rate_limit_per_minute=None,
            last_tested_at=None,
            last_test_status=None,
            last_test_error=None,
            is_enabled=True,
        )
        self.prompts: list[str] = []

    def get_profile(self, profile_id: uuid.UUID) -> ProviderProfileRecord | None:
        return self.profile if profile_id == self.profile.id else None

    def first_enabled_profile(self) -> ProviderProfileRecord:
        return self.profile

    def invoke_profile(
        self,
        profile: ProviderProfileRecord,
        prompt: str,
    ) -> ProviderCompletion:
        assert profile.id == self.profile.id
        self.prompts.append(prompt)
        if len(self.prompts) == 1:
            return ProviderCompletion(text="Conversation summary output", raw_response={"ok": True})
        return ProviderCompletion(text="Chapter draft output", raw_response={"ok": True})


def _seed_conversation(
    session: Session,
    *,
    world_id: uuid.UUID,
    scene_id: uuid.UUID,
    agent_id: uuid.UUID,
    writer_config: ConversationWriterConfig,
) -> uuid.UUID:
    service = ConversationService(session)
    created = service.create_session(
        ConversationSessionCreate(
            world_id=world_id,
            scene_id=scene_id,
            session_key=f"conversation-{uuid.uuid4().hex[:8]}",
            title="Writer session",
            scope_type=ConversationScopeType.SCENE,
            mode=ConversationMode.MANUAL_CHAIN,
            objective="Create a chapter from the transcript.",
            opening_prompt="Start the scene.",
            max_turns=2,
            policy=ConversationPolicyConfig(
                error_policy=ConversationErrorPolicy.RETRY_ONCE_THEN_FAIL,
                max_consecutive_failed_turns=2,
                loop_guard_window=4,
                repeat_output_threshold=3,
            ),
            writer_config=writer_config,
        ),
    )
    service.replace_participants(
        world_id,
        created.id,
        [ConversationParticipantDefinition(agent_id=agent_id, turn_order=0)],
    )
    service.seed_session(world_id, created.id, ConversationSeed(input_text="Operator seed"))
    prepared = service.prepare_next_turn(world_id, created.id)
    service.finalize_turn(
        prepared,
        response_text="Agent reply",
        run_id=None,
        diagnostics={},
        succeeded=True,
    )
    session.flush()
    return created.id


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
        cast(Table, Agent.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationParticipant.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, NarrativeArtifact.__table__),
        cast(Table, WorldEventModel.__table__),
    ):
        table.create(engine)
    return engine


def _seed_world(engine: Engine) -> uuid.UUID:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(User(id=user_id, email="writer@example.test", display_name="Writer"))
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug="writer-world",
                name="Writer World",
                rules_config={},
                is_active=True,
            ),
        )
        session.commit()
    return world_id


def _seed_scene(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    scene_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Scene(
                id=scene_id,
                world_id=world_id,
                scene_key="hall",
                name="Hall",
                is_active=True,
            ),
        )
        session.commit()
    return scene_id


def _seed_agent(engine: Engine, world_id: uuid.UUID, scene_id: uuid.UUID) -> uuid.UUID:
    agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                home_scene_id=scene_id,
                agent_key="scribe",
                display_name="Scribe",
                kind="narrative_agent",
                config={},
                is_enabled=True,
            ),
        )
        session.commit()
    return agent_id
