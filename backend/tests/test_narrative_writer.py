from __future__ import annotations

import uuid
from typing import cast

from noveland.adapters import ProviderCompletion, ProviderProfileRecord, ProviderType
from noveland.agents.models import Agent, AgentRelationshipEdge
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
    NarrativeArtifactCreate,
    NarrativeArtifactKind,
    NarrativeArtifactService,
    NarrativeGenerationMode,
    NarrativePublicationBlockedError,
)
from noveland.narrative.models import NarrativePublication
from noveland.worlds.models import (
    CharacterEmotionalState,
    CharacterKnowledgeFact,
    NarrativeContinuityReview,
    PlotThread,
    RouteAffinity,
    Scene,
    SecretRecord,
    StoryHook,
    World,
    WorldBible,
    Worldline,
)
from noveland.worlds.worldlines import ensure_primary_worldline
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
    assert profile_service.prompts[0].startswith("Writer controls:")
    assert "Write a concise but complete conversation summary." in profile_service.prompts[0]
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


def test_writer_prompt_uses_leak_safe_participant_context() -> None:
    engine = _engine()
    world_id = _seed_world(engine)
    scene_id = _seed_scene(engine, world_id)
    agent_id = _seed_agent(engine, world_id, scene_id)
    other_agent_id = _seed_agent(engine, world_id, scene_id, agent_key="outsider")
    profile_service = FakeProfileService()

    with Session(engine) as session:
        worldline_id = ensure_primary_worldline(session, world_id).id
        session.add_all(
            [
                SecretRecord(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    secret_key="hidden-letter",
                    title="Hidden letter",
                    content="nonholder forbidden content",
                    holder_agent_ids=[str(other_agent_id)],
                    reveal_conditions={},
                    consequence_metadata={},
                    visibility="holders",
                    status="hidden",
                    metadata_json={},
                ),
                CharacterKnowledgeFact(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    agent_id=agent_id,
                    fact_key="daily-plan",
                    knowledge_kind="fact",
                    content="Scribe plans a public festival scene.",
                    confidence=90,
                    visibility="private",
                    is_active=True,
                    metadata_json={},
                ),
            ],
        )
        conversation_id = _seed_conversation(
            session,
            world_id=world_id,
            scene_id=scene_id,
            agent_id=agent_id,
            writer_config=ConversationWriterConfig(
                provider_profile_id=profile_service.profile.id,
                auto_generate_on_complete=False,
                generate_summary=True,
                generate_chapter=False,
            ),
        )
        ConversationNarrativeWriterService(session, profile_service).generate_for_conversation(
            ConversationNarrativeGenerate(
                world_id=world_id,
                conversation_id=conversation_id,
                artifact_set=ConversationNarrativeArtifactSet.SUMMARY_ONLY,
                provider_profile_id=profile_service.profile.id,
                generation_mode=NarrativeGenerationMode.MANUAL,
            ),
        )

    assert "Scribe plans a public festival scene." in profile_service.prompts[0]
    assert "nonholder forbidden content" not in profile_service.prompts[0]


def test_writer_context_pack_records_bible_hooks_and_route_metadata() -> None:
    engine = _engine()
    world_id = _seed_world(engine)
    scene_id = _seed_scene(engine, world_id)
    agent_id = _seed_agent(engine, world_id, scene_id)
    profile_service = FakeProfileService()

    with Session(engine) as session:
        worldline_id = ensure_primary_worldline(session, world_id).id
        session.add_all(
            [
                WorldBible(
                    world_id=world_id,
                    source_material="Original school romance route.",
                    canon_timeline=[],
                    setting_rules={"tone": "daily-life galgame"},
                    forbidden_changes=[
                        {"title": "No generic chatbot drift", "reason": "Keep sequel tone."}
                    ],
                    sequel_boundaries={},
                    continuity_config={},
                    metadata_json={},
                ),
                StoryHook(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    hook_key="festival-promise",
                    title="Festival promise",
                    hook_type="promise",
                    summary="Scribe promised to help after school.",
                    status="open",
                    priority=80,
                    metadata_json={},
                ),
                PlotThread(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    thread_key="festival-route",
                    title="Festival route",
                    thread_type="personal",
                    status="active",
                    summary="A festival route is opening.",
                    next_beats=["after-school rehearsal"],
                    priority=70,
                    metadata_json={},
                ),
                RouteAffinity(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    agent_id=agent_id,
                    route_key="scribe-route",
                    status="active",
                    affinity=35,
                    stage=2,
                    flags=["festival"],
                    metadata_json={},
                ),
            ],
        )
        conversation_id = _seed_conversation(
            session,
            world_id=world_id,
            scene_id=scene_id,
            agent_id=agent_id,
            writer_config=ConversationWriterConfig(
                provider_profile_id=profile_service.profile.id,
                auto_generate_on_complete=False,
                generate_summary=True,
                generate_chapter=False,
            ),
        )
        writer = ConversationNarrativeWriterService(session, profile_service)
        artifacts = writer.generate_for_conversation(
            ConversationNarrativeGenerate(
                world_id=world_id,
                conversation_id=conversation_id,
                artifact_set=ConversationNarrativeArtifactSet.SUMMARY_ONLY,
                provider_profile_id=profile_service.profile.id,
                generation_mode=NarrativeGenerationMode.MANUAL,
            ),
        )
        preview = writer.preview_for_conversation(
            ConversationNarrativeGenerate(
                world_id=world_id,
                conversation_id=conversation_id,
                artifact_set=ConversationNarrativeArtifactSet.SUMMARY_ONLY,
                provider_profile_id=profile_service.profile.id,
                generation_mode=NarrativeGenerationMode.MANUAL,
            ),
        )

    prompt = profile_service.prompts[0]
    metadata = artifacts[0].metadata["living_world_context"]
    context_pack = metadata["context_pack"]
    assert "World bible constraints" in prompt
    assert "Forbidden continuity changes" in prompt
    assert "Festival promise" in prompt
    assert "Festival route" in prompt
    assert metadata["context_pack"]["diagnostics"]["open_hook_count"] == 1
    assert context_pack["diagnostics"]["forbidden_change_count"] == 1
    assert artifacts[0].metadata["worldline_id"] == str(worldline_id)
    assert preview.living_world_context["context_pack"]["diagnostics"]["route_state_count"] == 1
    assert "open story hooks are in scope" in preview.warnings


def test_publish_blocks_hidden_secret_leak_and_records_review() -> None:
    engine = _engine()
    world_id = _seed_world(engine)
    scene_id = _seed_scene(engine, world_id)
    agent_id = _seed_agent(engine, world_id, scene_id)

    with Session(engine) as session:
        worldline_id = ensure_primary_worldline(session, world_id).id
        session.add(
            SecretRecord(
                world_id=world_id,
                worldline_id=worldline_id,
                secret_key="hidden-letter",
                title="Hidden letter",
                content="forbidden hidden content",
                holder_agent_ids=[],
                reveal_conditions={},
                consequence_metadata={},
                visibility="holders",
                status="hidden",
                metadata_json={},
            ),
        )
        artifact = NarrativeArtifactService(session).create_artifact(
            NarrativeArtifactCreate(
                world_id=world_id,
                agent_id=agent_id,
                title="Leaky draft",
                content="This draft says forbidden hidden content.",
                artifact_kind=NarrativeArtifactKind.AGENT_NOTE,
                metadata={"worldline_id": str(worldline_id)},
            ),
        )
        try:
            NarrativeArtifactService(session).publish_artifact(
                world_id,
                artifact.id,
                actor_user_id=None,
            )
        except NarrativePublicationBlockedError as exc:
            blocked = exc
        else:
            raise AssertionError("expected publication to be blocked")
        review = session.get(NarrativeContinuityReview, blocked.review_id)

    assert blocked.review_status == "fail"
    assert review is not None
    assert review.status == "fail"
    assert any(issue["code"] == "hidden_secret_leak" for issue in review.issues)


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
        cast(Table, Worldline.__table__),
        cast(Table, Scene.__table__),
        cast(Table, Agent.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationParticipant.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, AgentRelationshipEdge.__table__),
        cast(Table, NarrativeArtifact.__table__),
        cast(Table, NarrativePublication.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, SecretRecord.__table__),
        cast(Table, CharacterKnowledgeFact.__table__),
        cast(Table, CharacterEmotionalState.__table__),
        cast(Table, NarrativeContinuityReview.__table__),
        cast(Table, WorldBible.__table__),
        cast(Table, StoryHook.__table__),
        cast(Table, PlotThread.__table__),
        cast(Table, RouteAffinity.__table__),
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


def _seed_agent(
    engine: Engine,
    world_id: uuid.UUID,
    scene_id: uuid.UUID,
    agent_key: str = "scribe",
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
                kind="narrative_agent",
                config={},
                is_enabled=True,
            ),
        )
        session.commit()
    return agent_id
