from __future__ import annotations

import uuid
from typing import cast

import pytest
from noveland.agents.models import Agent
from noveland.asset_generation import AssetGenerationService
from noveland.asset_generation.contracts import (
    AssetGenerationApplyRequest,
    AssetGenerationPolicyCreate,
    AssetGenerationPreviewRequest,
    AssetGenerationProposalStatus,
    MediaJobCancelSupersededRequest,
    MediaJobReprioritizeRequest,
)
from noveland.asset_generation.models import (
    AssetGenerationPolicy,
    AssetGenerationProposal,
    AssetGenerationRun,
)
from noveland.asset_generation.service import AssetGenerationValidationError
from noveland.auth.models import User
from noveland.conversations.models import (
    ConversationSession,
    ConversationTurn,
    ConversationTurnPresentation,
)
from noveland.events.models import WorldEventModel
from noveland.invocations.models import (
    AgentRuntimeRunModelInvocation,
    ModelInvocation,
    ModelInvocationTag,
    PromptSnapshot,
    PromptTemplate,
)
from noveland.media.contracts import MediaJobCreate, MediaJobKind, MediaJobStatus, MediaJobUpdate
from noveland.media.models import (
    MediaAsset,
    MediaAssetCollection,
    MediaAssetCollectionItem,
    MediaAssetContext,
    MediaAssetInput,
    MediaAssetTag,
    MediaJob,
    MediaObject,
    MediaReference,
)
from noveland.media.service import MediaJobService
from noveland.memory.models import MemoryBackendProfile, MemoryWriteJob
from noveland.narrative.models import NarrativeArtifact
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderCapabilityCreate,
    ProviderIntegrationCreate,
    ProviderKind,
    ProviderScopeKind,
)
from noveland.providers.models import ProviderCapability, ProviderHealthCheck, ProviderIntegration
from noveland.providers.registry import ProviderRegistryService
from noveland.speech.models import (
    AgentVoiceProfileBinding,
    SpeechStyleMapping,
    SpeechTranscript,
    VoiceProfile,
)
from noveland.visual.models import (
    CharacterSpriteSet,
    CharacterSpriteVariant,
    SceneBackgroundProfile,
)
from noveland.worlds.models import Scene, World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_preview_persists_proposals_without_media_jobs_and_apply_creates_selected_jobs() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    with Session(engine) as session:
        _seed_provider(
            session,
            graph.world_id,
            ProviderKind.IMAGE_GENERATION,
            "supports_image_generation",
        )
        _seed_provider(session, graph.world_id, ProviderKind.TEXT_TO_SPEECH, "supports_tts")
        _seed_voice_binding(session, graph)
        service = AssetGenerationService(session)

        preview = service.preview(
            graph.world_id,
            AssetGenerationPreviewRequest(
                worldline_id=graph.worldline_id,
                conversation_id=graph.conversation_id,
                current_turn_id=graph.turn_ids[0],
            ),
            actor_ref="test",
        )
        proposed = [
            item
            for item in preview.run.proposals
            if item.status == AssetGenerationProposalStatus.PROPOSED
        ]
        apply = service.apply(
            graph.world_id,
            AssetGenerationApplyRequest(
                worldline_id=graph.worldline_id,
                run_id=preview.run.id,
                proposal_ids=(proposed[0].id,),
            ),
            actor_ref="test",
        )
        session.commit()

    with Session(engine) as session:
        proposals = session.scalars(select(AssetGenerationProposal)).all()
        assert len(preview.run.proposals) >= 3
        assert len(session.scalars(select(MediaJob)).all()) == 1
        assert len(apply.media_jobs) == 1
        assert any(proposal.status == "proposed" for proposal in proposals)
        job = session.scalars(select(MediaJob)).one()
        assert job.status == MediaJobStatus.QUEUED.value
        assert job.cancel_policy == "cancel_superseded"
        assert job.invalidation_key is not None
        assert "storage_uri" not in str(job.request_json)
        assert session.scalars(select(WorldEventModel)).all() == []


def test_budget_and_missing_provider_capability_block_proposals() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    with Session(engine) as session:
        service = AssetGenerationService(session)
        preview = service.preview(
            graph.world_id,
            AssetGenerationPreviewRequest(
                worldline_id=graph.worldline_id,
                conversation_id=graph.conversation_id,
                current_turn_id=graph.turn_ids[0],
                max_total_estimated_cost=0,
            ),
            actor_ref="test",
        )
        session.commit()

    statuses = {proposal.status for proposal in preview.run.proposals}
    reasons = " ".join(proposal.reason for proposal in preview.run.proposals)
    assert statuses == {AssetGenerationProposalStatus.BLOCKED}
    assert "missing provider capability" in reasons or "cost budget exceeded" in reasons


def test_policy_rejects_leaky_json_and_preview_validates_worldline() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    fork_id = _seed_fork(engine, graph.world_id, graph.worldline_id)
    with Session(engine) as session:
        service = AssetGenerationService(session)
        with pytest.raises(ValueError, match="storage_uri"):
            AssetGenerationPolicyCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                policy_key="default",
                rules_json={"nested": {"storage_uri": "local://leak"}},
            )
        with pytest.raises(AssetGenerationValidationError, match="turn"):
            service.preview(
                graph.world_id,
                AssetGenerationPreviewRequest(
                    worldline_id=fork_id,
                    current_turn_id=graph.turn_ids[0],
                ),
                actor_ref="test",
            )


def test_reprioritize_and_cancel_superseded_respect_terminal_jobs() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    with Session(engine) as session:
        jobs = MediaJobService(session)
        queued = jobs.create_job(
            MediaJobCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                job_kind=MediaJobKind.IMAGE_GENERATION,
                priority=50,
                invalidation_key="turn:one",
            ),
            actor_ref="test",
        )
        succeeded = jobs.create_job(
            MediaJobCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                job_kind=MediaJobKind.IMAGE_GENERATION,
                priority=50,
                invalidation_key="turn:one",
            ),
            actor_ref="test",
        )
        jobs.update_job(
            graph.world_id,
            succeeded.id,
            MediaJobUpdate(status=MediaJobStatus.SUCCEEDED),
        )
        session.commit()

    with Session(engine) as session:
        service = AssetGenerationService(session)
        reprioritized = service.reprioritize_jobs(
            graph.world_id,
            MediaJobReprioritizeRequest(
                worldline_id=graph.worldline_id,
                invalidation_key="turn:one",
                priority=5,
            ),
        )
        cancelled = service.cancel_superseded_jobs(
            graph.world_id,
            MediaJobCancelSupersededRequest(
                worldline_id=graph.worldline_id,
                invalidation_key="turn:one",
            ),
        )
        session.commit()

    assert {job.priority for job in reprioritized.jobs} == {5}
    assert queued.id in cancelled.cancelled_job_ids
    assert succeeded.id in cancelled.skipped_job_ids


class _Graph:
    def __init__(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
        scene_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_ids: tuple[uuid.UUID, uuid.UUID],
    ) -> None:
        self.world_id = world_id
        self.worldline_id = worldline_id
        self.agent_id = agent_id
        self.scene_id = scene_id
        self.conversation_id = conversation_id
        self.turn_ids = turn_ids


def _seed_graph(engine: Engine) -> _Graph:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    scene_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    turn_ids = (uuid.uuid4(), uuid.uuid4())
    with Session(engine) as session:
        session.add(User(id=user_id, email=f"{user_id}@example.test", display_name="Test"))
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug=f"world-{world_id.hex[:8]}",
                name="World",
            )
        )
        session.flush()
        worldline = ensure_primary_worldline(session, world_id)
        session.add(Scene(id=scene_id, world_id=world_id, scene_key="scene", name="Scene"))
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key="agent",
                display_name="Agent",
                kind="role_agent",
            )
        )
        session.add(
            ConversationSession(
                id=conversation_id,
                world_id=world_id,
                worldline_id=worldline.id,
                scene_id=scene_id,
                session_key="session",
                title="Session",
                scope_type="scene",
                mode="manual_chain",
                status="running",
                objective="",
                opening_prompt="",
                max_turns=3,
                next_turn_index=2,
                policy_config={},
                writer_config={},
                memory_config={},
            )
        )
        for index, turn_id in enumerate(turn_ids):
            session.add(
                ConversationTurn(
                    id=turn_id,
                    session_id=conversation_id,
                    turn_index=index,
                    speaker_kind="agent",
                    speaker_agent_id=agent_id,
                    input_text="hi",
                    output_text="hello",
                    status="succeeded",
                )
            )
        session.commit()
        return _Graph(world_id, worldline.id, agent_id, scene_id, conversation_id, turn_ids)


def _seed_provider(
    session: Session,
    world_id: uuid.UUID,
    provider_kind: ProviderKind,
    capability_key: str,
) -> uuid.UUID:
    provider = ProviderRegistryService(session).create_provider(
        ProviderIntegrationCreate(
            world_id=world_id,
            scope_kind=ProviderScopeKind.WORLD,
            provider_kind=provider_kind,
            adapter_kind=ProviderAdapterKind.FAKE,
            provider_key=f"fake-{provider_kind.value}",
            display_name=f"Fake {provider_kind.value}",
            capabilities=(ProviderCapabilityCreate(capability_key=capability_key),),
        )
    )
    return provider.id


def _seed_voice_binding(session: Session, graph: _Graph) -> None:
    voice_profile_id = uuid.uuid4()
    session.add(
        VoiceProfile(
            id=voice_profile_id,
            world_id=graph.world_id,
            worldline_id=graph.worldline_id,
            profile_key="default",
            display_name="Default Voice",
            status="active",
            visibility="world_admin",
            owner_kind="agent",
            owner_agent_id=graph.agent_id,
            default_language="en",
            supported_languages_json=["en"],
            voice_kind="preset",
            consent_status="not_required",
            usage_policy_json={},
            metadata_json={},
        )
    )
    session.add(
        AgentVoiceProfileBinding(
            id=uuid.uuid4(),
            world_id=graph.world_id,
            worldline_id=graph.worldline_id,
            agent_id=graph.agent_id,
            voice_profile_id=voice_profile_id,
            binding_role="default",
            priority=0,
            is_default=True,
            style_overrides_json={},
        )
    )
    session.flush()


def _seed_fork(engine: Engine, world_id: uuid.UUID, parent_worldline_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        fork = Worldline(
            world_id=world_id,
            worldline_key=f"fork-{uuid.uuid4().hex[:8]}",
            name="Fork",
            parent_worldline_id=parent_worldline_id,
            status="active",
            created_by_actor_ref="test",
            metadata_json={},
        )
        session.add(fork)
        session.commit()
        return fork.id


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
        cast(Table, ConversationTurn.__table__),
        cast(Table, ConversationTurnPresentation.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, MemoryWriteJob.__table__),
        cast(Table, ProviderIntegration.__table__),
        cast(Table, ProviderCapability.__table__),
        cast(Table, ProviderHealthCheck.__table__),
        cast(Table, MediaJob.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, MediaObject.__table__),
        cast(Table, MediaReference.__table__),
        cast(Table, NarrativeArtifact.__table__),
        cast(Table, MediaAssetContext.__table__),
        cast(Table, MediaAssetInput.__table__),
        cast(Table, MediaAssetTag.__table__),
        cast(Table, MediaAssetCollection.__table__),
        cast(Table, MediaAssetCollectionItem.__table__),
        cast(Table, ModelInvocation.__table__),
        cast(Table, PromptTemplate.__table__),
        cast(Table, PromptSnapshot.__table__),
        cast(Table, AgentRuntimeRunModelInvocation.__table__),
        cast(Table, ModelInvocationTag.__table__),
        cast(Table, VoiceProfile.__table__),
        cast(Table, AgentVoiceProfileBinding.__table__),
        cast(Table, SpeechTranscript.__table__),
        cast(Table, SpeechStyleMapping.__table__),
        cast(Table, CharacterSpriteSet.__table__),
        cast(Table, CharacterSpriteVariant.__table__),
        cast(Table, SceneBackgroundProfile.__table__),
        cast(Table, AssetGenerationPolicy.__table__),
        cast(Table, AssetGenerationRun.__table__),
        cast(Table, AssetGenerationProposal.__table__),
    ):
        table.create(engine)
    return engine
