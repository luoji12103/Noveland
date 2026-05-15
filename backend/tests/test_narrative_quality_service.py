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
from noveland.invocations.models import (
    AgentRuntimeRunModelInvocation,
    ModelInvocation,
    ModelInvocationTag,
    PromptSnapshot,
    PromptTemplate,
)
from noveland.narrative.models import NarrativeArtifact, NarrativePublication
from noveland.narrative_quality.contracts import (
    NarrativeQualityContextKind,
    NarrativeQualityContextPreviewRequest,
    NarrativeQualityGMProposalGenerateRequest,
)
from noveland.narrative_quality.service import (
    NarrativeQualityService,
    NarrativeQualityValidationError,
)
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderIntegrationCreate,
    ProviderKind,
    ProviderScopeKind,
)
from noveland.providers.models import ProviderCapability, ProviderHealthCheck, ProviderIntegration
from noveland.providers.registry import ProviderRegistryService
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
from sqlalchemy import Table, create_engine, func, select
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


def test_provider_backed_gm_generation_creates_proposal_and_invocation() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    provider_id = _seed_text_provider(engine, world_id)

    with Session(engine) as session:
        result = NarrativeQualityService(session).generate_gm_proposal(
            world_id,
            NarrativeQualityGMProposalGenerateRequest(
                worldline_id=worldline_id,
                provider_id=provider_id,
                prompt_goal="Suggest a quiet daily event.",
                title="Quiet daily event",
                event_name="gm.daily_quiet_event",
                payload_json={"kind": "daily"},
            ),
            actor_ref="test",
        )
        session.commit()

    with Session(engine) as session:
        proposal = session.get(GMEventProposal, result.proposal.id)
        invocation = session.get(ModelInvocation, result.invocation.id)
        snapshot = session.scalars(
            select(PromptSnapshot).where(PromptSnapshot.invocation_id == result.invocation.id)
        ).one()
        event_count = session.scalar(select(func.count(WorldEventModel.id)))

    assert result.dry_run is False
    assert result.provider.provider_kind == ProviderKind.TEXT_GENERATION
    assert result.invocation.status == "succeeded"
    assert proposal is not None
    assert proposal.worldline_id == worldline_id
    assert proposal.status == "proposed"
    assert proposal.source_context["model_invocation_id"] == str(result.invocation.id)
    assert proposal.proposed_payload == {
        "kind": "daily",
        "source": "provider_backed_gm_proposal",
        "goal": "Suggest a quiet daily event.",
    }
    assert invocation is not None
    assert invocation.worldline_id == worldline_id
    assert snapshot.raw_request_json is not None
    assert snapshot.raw_request_json["request_json"]["context_kind"] == "gm"
    assert event_count == 0


def test_provider_backed_gm_generation_dry_run_writes_no_proposal() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    provider_id = _seed_text_provider(engine, world_id)

    with Session(engine) as session:
        result = NarrativeQualityService(session).generate_gm_proposal(
            world_id,
            NarrativeQualityGMProposalGenerateRequest(
                worldline_id=worldline_id,
                provider_id=provider_id,
                prompt_goal="Preview only.",
                dry_run=True,
            ),
            actor_ref="test",
        )
        proposal_count = session.scalar(select(func.count(GMEventProposal.id)))
        invocation_count = session.scalar(select(func.count(ModelInvocation.id)))

    assert result.dry_run is True
    assert result.proposal.id is None
    assert result.proposal.status == "preview"
    assert proposal_count == 0
    assert invocation_count == 1


def test_provider_backed_gm_generation_rejects_non_text_provider() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    provider_id = _seed_provider(engine, world_id, ProviderKind.IMAGE_GENERATION)

    with Session(engine) as session:
        try:
            NarrativeQualityService(session).generate_gm_proposal(
                world_id,
                NarrativeQualityGMProposalGenerateRequest(
                    worldline_id=worldline_id,
                    provider_id=provider_id,
                    prompt_goal="This should not run.",
                ),
                actor_ref="test",
            )
        except NarrativeQualityValidationError as exc:
            assert "text_generation" in str(exc)
        else:
            raise AssertionError("expected non-text provider rejection")
        assert session.scalar(select(func.count(GMEventProposal.id))) == 0
        assert session.scalar(select(func.count(ModelInvocation.id))) == 0


def test_provider_backed_gm_generation_sanitizes_proposal_traceability() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    provider_id = _seed_text_provider(engine, world_id)

    with Session(engine) as session:
        result = NarrativeQualityService(session).generate_gm_proposal(
            world_id,
            NarrativeQualityGMProposalGenerateRequest(
                worldline_id=worldline_id,
                provider_id=provider_id,
                prompt_goal="storage_uri=media://hidden/object base64,AAAA",
                payload_json={"storage_uri": "media://hidden/object"},
            ),
            actor_ref="test",
        )
        serialized = result.model_dump_json()
        proposal = session.get(GMEventProposal, result.proposal.id)

    assert "storage_uri" not in serialized
    assert "media://" not in serialized
    assert "base64" not in serialized.lower()
    assert proposal is not None
    assert "storage_uri" not in proposal.proposed_payload
    assert "model_invocation_id" in proposal.source_context


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
        cast(Table, ProviderIntegration.__table__),
        cast(Table, ProviderCapability.__table__),
        cast(Table, ProviderHealthCheck.__table__),
        cast(Table, ModelInvocation.__table__),
        cast(Table, PromptTemplate.__table__),
        cast(Table, PromptSnapshot.__table__),
        cast(Table, AgentRuntimeRunModelInvocation.__table__),
        cast(Table, ModelInvocationTag.__table__),
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


def _seed_text_provider(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    return _seed_provider(engine, world_id, ProviderKind.TEXT_GENERATION)


def _seed_provider(
    engine: Engine,
    world_id: uuid.UUID,
    provider_kind: ProviderKind,
) -> uuid.UUID:
    with Session(engine) as session:
        provider = ProviderRegistryService(session).create_provider(
            ProviderIntegrationCreate(
                world_id=world_id,
                scope_kind=ProviderScopeKind.WORLD,
                provider_kind=provider_kind,
                adapter_kind=ProviderAdapterKind.FAKE,
                provider_key=f"fake-{provider_kind.value}",
                display_name=f"Fake {provider_kind.value}",
            )
        )
        session.commit()
        return provider.id
