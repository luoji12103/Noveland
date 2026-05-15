from __future__ import annotations

import uuid
from typing import cast

from noveland.agents.models import Agent, AgentRelationshipEdge
from noveland.auth.models import User
from noveland.conversations import ConversationService
from noveland.conversations.contracts import (
    ConversationErrorPolicy,
    ConversationMemoryConfig,
    ConversationMode,
    ConversationParticipantDefinition,
    ConversationPolicyConfig,
    ConversationScopeType,
    ConversationSeed,
    ConversationSessionCreate,
    ConversationSpeakerPolicyMode,
    ConversationWriterConfig,
)
from noveland.conversations.models import (
    ConversationParticipant,
    ConversationSession,
    ConversationTurn,
)
from noveland.events.models import WorldEventModel
from noveland.narrative.models import NarrativeArtifact, NarrativePublication
from noveland.narrative_quality.contracts import (
    NarrativeQualityContextKind,
    NarrativeQualityContextPreviewRequest,
)
from noveland.narrative_quality.service import (
    NarrativeQualityService,
    NarrativeQualityValidationError,
)
from noveland.worlds.models import (
    CharacterEmotionalState,
    CharacterKnowledgeFact,
    GMAgenda,
    GMEventProposal,
    LongRunEvalRun,
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
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_agent_runtime_context_uses_living_world_selector() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "The bell rings at dusk.")

    with Session(engine) as session:
        preview = NarrativeQualityService(session).preview_context(
            world_id,
            NarrativeQualityContextPreviewRequest(
                worldline_id=worldline_id,
                context_kind=NarrativeQualityContextKind.AGENT,
                agent_id=agent_id,
            ),
        )

    assert preview.worldline_id == worldline_id
    assert preview.context_kind == NarrativeQualityContextKind.AGENT
    assert "The bell rings at dusk." in preview.prompt_text
    assert preview.metadata["context_sections"]["public_fact_count"] == 1
    assert preview.diagnostics["public_fact_count"] == 1


def test_conversation_runtime_context_is_worldline_scoped_and_sanitized() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(
        engine,
        "storage_uri=media://leaky/path",
    )
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)

    with Session(engine) as session:
        preview = NarrativeQualityService(session).preview_context(
            world_id,
            NarrativeQualityContextPreviewRequest(
                worldline_id=worldline_id,
                context_kind=NarrativeQualityContextKind.CONVERSATION,
                conversation_id=conversation_id,
            ),
        )

    serialized = preview.model_dump_json()
    assert preview.subject_ref == f"conversation:{conversation_id}"
    assert preview.metadata["conversation_id"] == str(conversation_id)
    assert preview.metadata["turn_count"] == 1
    assert "storage_uri" not in serialized
    assert "media://" not in serialized


def test_conversation_context_rejects_cross_worldline_session() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)
    with Session(engine) as session:
        other_worldline = ensure_primary_worldline(session, world_id)
        fork_id = uuid.uuid4()
        session.add(
            type(other_worldline)(
                id=fork_id,
                world_id=world_id,
                worldline_key=f"fork-{fork_id.hex[:8]}",
                name="Fork",
                status="active",
                created_by_actor_ref="test",
                metadata_json={},
            )
        )
        session.commit()

    with Session(engine) as session:
        try:
            NarrativeQualityService(session).preview_context(
                world_id,
                NarrativeQualityContextPreviewRequest(
                    worldline_id=fork_id,
                    context_kind=NarrativeQualityContextKind.CONVERSATION,
                    conversation_id=conversation_id,
                ),
            )
        except NarrativeQualityValidationError as exc:
            assert "worldline" in str(exc)
        else:
            raise AssertionError("expected cross-worldline conversation rejection")


def test_gm_narrative_and_eval_contexts_return_safe_worldline_previews() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")

    with Session(engine) as session:
        for kind in (
            NarrativeQualityContextKind.GM,
            NarrativeQualityContextKind.NARRATIVE,
            NarrativeQualityContextKind.EVAL,
        ):
            preview = NarrativeQualityService(session).preview_context(
                world_id,
                NarrativeQualityContextPreviewRequest(
                    worldline_id=worldline_id,
                    context_kind=kind,
                ),
            )
            assert preview.worldline_id == worldline_id
            assert preview.subject_ref == f"{kind.value}:{worldline_id}"
            assert "storage_uri" not in preview.model_dump_json()


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _create_tables(engine)
    return engine


def _create_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, Scene.__table__),
        cast(Table, Agent.__table__),
        cast(Table, AgentRelationshipEdge.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, WorldBible.__table__),
        cast(Table, SecretRecord.__table__),
        cast(Table, CharacterKnowledgeFact.__table__),
        cast(Table, CharacterEmotionalState.__table__),
        cast(Table, StoryHook.__table__),
        cast(Table, PlotThread.__table__),
        cast(Table, RouteAffinity.__table__),
        cast(Table, NarrativeArtifact.__table__),
        cast(Table, NarrativePublication.__table__),
        cast(Table, NarrativeContinuityReview.__table__),
        cast(Table, GMAgenda.__table__),
        cast(Table, GMEventProposal.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationParticipant.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, LongRunEvalRun.__table__),
    ):
        table.create(engine)


def _seed_world_agent_and_fact(
    engine: Engine,
    fact_text: str,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    world_id = uuid.uuid4()
    user_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug=f"world-{world_id.hex[:8]}",
                name="World",
            )
        )
        worldline = ensure_primary_worldline(session, world_id)
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key=f"agent-{agent_id.hex[:8]}",
                display_name="Alice",
                kind="role_agent",
                character_profile={},
                config={},
            )
        )
        session.flush()
        session.add(
            CharacterKnowledgeFact(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline.id,
                agent_id=agent_id,
                fact_key="fact-1",
                knowledge_kind="fact",
                content=fact_text,
                confidence=90,
                visibility="public",
                is_active=True,
                metadata_json={},
            )
        )
        session.commit()
        return world_id, worldline.id, agent_id


def _seed_conversation(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> uuid.UUID:
    with Session(engine) as session:
        service = ConversationService(session)
        created = service.create_session(
            ConversationSessionCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                session_key=f"session-{uuid.uuid4().hex[:8]}",
                title="Opening scene",
                scope_type=ConversationScopeType.WORLD,
                mode=ConversationMode.MANUAL_CHAIN,
                objective="Keep the scene quiet.",
                opening_prompt="Hello.",
                max_turns=4,
                policy=ConversationPolicyConfig(
                    error_policy=ConversationErrorPolicy.FAIL_SESSION,
                    max_consecutive_failed_turns=2,
                    loop_guard_window=3,
                    repeat_output_threshold=2,
                    speaker_policy=ConversationSpeakerPolicyMode.ROUND_ROBIN,
                ),
                writer_config=ConversationWriterConfig(),
                memory_config=ConversationMemoryConfig(),
            )
        )
        service.replace_participants(
            world_id,
            created.id,
            [ConversationParticipantDefinition(agent_id=agent_id, turn_order=0)],
        )
        service.seed_session(world_id, created.id, ConversationSeed(input_text="Operator seed"))
        session.commit()
        return created.id
