from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from noveland.agents.models import Agent
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
from noveland.media.storage import LocalMediaObjectStorage
from noveland.memory.models import MemoryBackendProfile, MemoryWriteJob
from noveland.multimodal_eval import MultimodalEvalService
from noveland.narrative.models import NarrativeArtifact
from noveland.providers.models import ProviderCapability, ProviderHealthCheck, ProviderIntegration
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
from noveland.worlds.models import LongRunEvalRun, Scene, World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_multimodal_eval_passes_sample_world(tmp_path: Path) -> None:
    engine = _engine()
    storage = LocalMediaObjectStorage(tmp_path)
    graph = _seed_sample_world(engine, storage)

    with Session(engine) as session:
        service = MultimodalEvalService(session, storage)
        diagnostics = service.diagnostics(graph.world_id, worldline_id=graph.worldline_id)
        run = service.run_eval(
            graph.world_id,
            request=_run_request(graph.worldline_id),
        )
        session.commit()

    assert diagnostics.status == "completed"
    assert diagnostics.blockers == []
    assert diagnostics.metrics["media_assets"]["missing_object_count"] == 0
    assert diagnostics.metrics["invocations"]["estimated_cost_total"] == 0.03
    assert run.status == "completed"
    assert run.eval_key == "multimodal-smoke"

    with Session(engine) as session:
        persisted = session.scalars(select(LongRunEvalRun)).one()
        assert persisted.eval_key == "multimodal-smoke"
        assert persisted.metrics["visual"]["sprite_sets_missing_default_count"] == 0


def test_multimodal_eval_detects_integrity_and_leak_failures(tmp_path: Path) -> None:
    engine = _engine()
    storage = LocalMediaObjectStorage(tmp_path)
    graph = _seed_sample_world(engine, storage)
    with Session(engine) as session:
        missing_asset = MediaAsset(
            id=uuid.uuid4(),
            world_id=graph.world_id,
            worldline_id=graph.worldline_id,
            asset_kind="image",
            asset_role="event_cg",
            source_kind="manual_upload",
            status="available",
            visibility="world_admin",
            mime_type="image/png",
            size_bytes=10,
            checksum_sha256="0" * 64,
            created_by_actor_ref="test",
            metadata_json={},
        )
        leaky_event = WorldEventModel(
            id=uuid.uuid4(),
            world_id=graph.world_id,
            worldline_id=graph.worldline_id,
            sequence=1,
            event_name="test.leak",
            importance="system",
            payload={"storage_uri": "media://worlds/leak.png", "raw_prompt": "secret prompt"},
            wall_time=datetime.now(UTC),
            actor_ref="test",
        )
        leaky_snapshot = session.scalars(select(PromptSnapshot)).first()
        assert leaky_snapshot is not None
        leaky_snapshot.raw_request_json = {"headers": {"clientSecret": "sk-real-secret"}}
        session.add(missing_asset)
        session.add(leaky_event)
        session.commit()

    with Session(engine) as session:
        diagnostics = MultimodalEvalService(session, storage).diagnostics(
            graph.world_id,
            worldline_id=graph.worldline_id,
        )

    codes = {finding.code for finding in diagnostics.blockers}
    assert diagnostics.status == "failed"
    assert "media_asset_missing_object" in codes
    assert "world_event_payload_leak" in codes
    assert "prompt_snapshot_secret_leak" in codes
    assert diagnostics.metrics["events"]["payload_leak_count"] == 1


def test_multimodal_eval_detects_missing_sprite_voice_and_storage(tmp_path: Path) -> None:
    engine = _engine()
    storage = LocalMediaObjectStorage(tmp_path)
    graph = _seed_sample_world(engine, storage)
    with Session(engine) as session:
        sprite_set = session.get(CharacterSpriteSet, graph.sprite_set_id)
        assert sprite_set is not None
        sprite_set.default_variant_id = None
        session.query(CharacterSpriteVariant).delete()
        session.query(AgentVoiceProfileBinding).delete()
        media_object = session.scalars(select(MediaObject)).first()
        assert media_object is not None
        media_object.storage_uri = storage.uri_for_key("missing/object.bin")
        session.commit()

    with Session(engine) as session:
        diagnostics = MultimodalEvalService(session, storage).diagnostics(
            graph.world_id,
            worldline_id=graph.worldline_id,
        )

    codes = {finding.code for finding in diagnostics.blockers}
    assert "sprite_set_missing_default" in codes
    assert "sprite_set_missing_neutral" in codes
    assert "agent_missing_default_voice" in codes
    assert "media_object_storage_missing" in codes
    assert diagnostics.metrics["media_assets"]["missing_storage_count"] == 1


class _Graph:
    def __init__(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
        sprite_set_id: uuid.UUID,
    ) -> None:
        self.world_id = world_id
        self.worldline_id = worldline_id
        self.agent_id = agent_id
        self.conversation_id = conversation_id
        self.turn_id = turn_id
        self.sprite_set_id = sprite_set_id


def _run_request(worldline_id: uuid.UUID) -> object:
    from noveland.multimodal_eval.contracts import MultimodalEvalRunRequest

    return MultimodalEvalRunRequest(worldline_id=worldline_id)


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
        cast(Table, Agent.__table__),
        cast(Table, Scene.__table__),
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
        cast(Table, LongRunEvalRun.__table__),
    ):
        table.create(engine)


def _seed_sample_world(engine: Engine, storage: LocalMediaObjectStorage) -> _Graph:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    scene_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    turn_id = uuid.uuid4()
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
                session_key="session",
                title="Session",
                scope_type="world",
                mode="manual_chain",
                status="running",
                objective="",
                opening_prompt="",
                max_turns=3,
                next_turn_index=1,
                policy_config={},
                writer_config={},
                memory_config={},
            )
        )
        session.add(
            ConversationTurn(
                id=turn_id,
                session_id=conversation_id,
                turn_index=0,
                speaker_kind="agent",
                speaker_agent_id=agent_id,
                input_text="hi",
                output_text="hello",
                status="succeeded",
            )
        )
        provider_id = _provider(session, world_id)
        job_id = _media_job(session, world_id, worldline.id, conversation_id, turn_id)
        invocation_id = _invocation(session, world_id, worldline.id, job_id, 0.03)
        asset_ids = [
            _asset_object(
                session,
                storage,
                world_id,
                worldline.id,
                asset_role="character_sprite",
                key_suffix="sprite",
                source_job_id=job_id,
                source_invocation_id=invocation_id,
            ),
            _asset_object(
                session,
                storage,
                world_id,
                worldline.id,
                asset_role="scene_background",
                key_suffix="background",
            ),
            _asset_object(
                session,
                storage,
                world_id,
                worldline.id,
                asset_role="speech_audio",
                key_suffix="audio",
                asset_kind="audio",
                mime_type="audio/wav",
                source_kind="provider_generated",
                source_job_id=job_id,
                source_invocation_id=invocation_id,
            ),
        ]
        sprite_set_id = uuid.uuid4()
        variant_id = uuid.uuid4()
        session.add(
            CharacterSpriteSet(
                id=sprite_set_id,
                world_id=world_id,
                worldline_id=worldline.id,
                agent_id=agent_id,
                style_key="default",
                display_name="Default",
                default_variant_id=variant_id,
                status="active",
                visibility="world_admin",
                metadata_json={},
            )
        )
        session.add(
            CharacterSpriteVariant(
                id=variant_id,
                world_id=world_id,
                worldline_id=worldline.id,
                sprite_set_id=sprite_set_id,
                asset_id=asset_ids[0],
                expression_key="neutral",
                priority=0,
                is_default=True,
                status="active",
                visibility="world_admin",
                mood_tags_json=[],
                metadata_json={},
            )
        )
        session.add(
            SceneBackgroundProfile(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline.id,
                scene_id=scene_id,
                location_key="classroom",
                asset_id=asset_ids[1],
                priority=0,
                is_default=True,
                status="active",
                visibility="world_admin",
                metadata_json={},
            )
        )
        voice_profile_id = uuid.uuid4()
        session.add(
            VoiceProfile(
                id=voice_profile_id,
                world_id=world_id,
                worldline_id=worldline.id,
                profile_key="default",
                display_name="Default Voice",
                status="active",
                visibility="world_admin",
                owner_kind="agent",
                owner_agent_id=agent_id,
                voice_kind="preset",
                consent_status="not_required",
                usage_policy_json={},
                metadata_json={},
                supported_languages_json=["en"],
                provider_integration_id=provider_id,
            )
        )
        session.add(
            AgentVoiceProfileBinding(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline.id,
                agent_id=agent_id,
                voice_profile_id=voice_profile_id,
                binding_role="default",
                priority=0,
                is_default=True,
                style_overrides_json={},
            )
        )
        session.add(
            SpeechTranscript(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline.id,
                source_asset_id=asset_ids[2],
                media_job_id=job_id,
                model_invocation_id=invocation_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                transcript_text="hello",
                status="available",
                visibility="world_admin",
            )
        )
        session.add(
            ConversationTurnPresentation(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline.id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                speaker_agent_id=agent_id,
                emotion_key="neutral",
                sprite_set_id=sprite_set_id,
                sprite_variant_id=variant_id,
                voice_profile_id=voice_profile_id,
                tts_media_asset_id=asset_ids[2],
                background_asset_id=asset_ids[1],
                composite_scene_asset_id=asset_ids[0],
                presentation_json={},
                render_state="speech_rendered",
            )
        )
        session.commit()
        return _Graph(world_id, worldline.id, agent_id, conversation_id, turn_id, sprite_set_id)


def _provider(session: Session, world_id: uuid.UUID) -> uuid.UUID:
    provider_id = uuid.uuid4()
    session.add(
        ProviderIntegration(
            id=provider_id,
            world_id=world_id,
            scope_kind="world",
            scope_key=f"world:{world_id}",
            provider_kind="text_to_speech",
            adapter_kind="fake",
            provider_key="fake-tts",
            display_name="Fake TTS",
            auth_ref="env:OPENAI_API_KEY",
            config_json={},
            default_params_json={},
            status="active",
            visibility="world_admin",
        )
    )
    session.add(
        ProviderCapability(
            id=uuid.uuid4(),
            provider_integration_id=provider_id,
            capability_key="supports_tts",
            capability_json={},
        )
    )
    session.add(
        ProviderHealthCheck(
            id=uuid.uuid4(),
            provider_integration_id=provider_id,
            status="healthy",
            latency_ms=1,
            metadata_json={"auth_resolved": True},
        )
    )
    return provider_id


def _media_job(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
) -> uuid.UUID:
    job_id = uuid.uuid4()
    session.add(
        MediaJob(
            id=job_id,
            world_id=world_id,
            worldline_id=worldline_id,
            conversation_id=conversation_id,
            turn_id=turn_id,
            job_kind="speech_generation",
            status="succeeded",
            priority=0,
            request_json={"text": "hello"},
            result_json={},
            provider_config_json={},
            created_by_actor_ref="test",
        )
    )
    return job_id


def _invocation(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    job_id: uuid.UUID,
    cost: float,
) -> uuid.UUID:
    invocation_id = uuid.uuid4()
    session.add(
        ModelInvocation(
            id=invocation_id,
            world_id=world_id,
            worldline_id=worldline_id,
            trace_id=uuid.uuid4(),
            invocation_kind="text_to_speech",
            actor_kind="service",
            actor_ref="test",
            media_job_id=job_id,
            provider_kind="local_stub",
            model_name="fake",
            input_text=None,
            output_text=None,
            input_json={},
            output_json={},
            request_params_json={"auth_resolved": True},
            response_metadata_json={},
            usage_json={},
            latency_ms=12,
            estimated_cost=cost,
            status="succeeded",
            visibility="world_admin",
            redaction_status="redacted",
            retention_policy="eval_only",
        )
    )
    session.add(
        PromptSnapshot(
            id=uuid.uuid4(),
            invocation_id=invocation_id,
            raw_prompt_text=None,
            raw_messages_json=None,
            raw_request_json={"headers": {"authorization": "[REDACTED]"}},
            raw_response_json={"status": "ok"},
            raw_output_text=None,
            normalized_output_json={},
            prompt_checksum_sha256="1" * 64,
            visibility="world_admin",
            redaction_status="redacted",
        )
    )
    return invocation_id


def _asset_object(
    session: Session,
    storage: LocalMediaObjectStorage,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    asset_role: str,
    key_suffix: str,
    asset_kind: str = "image",
    mime_type: str = "image/png",
    source_kind: str = "manual_upload",
    source_job_id: uuid.UUID | None = None,
    source_invocation_id: uuid.UUID | None = None,
) -> uuid.UUID:
    asset_id = uuid.uuid4()
    data = f"{asset_id}:{key_suffix}".encode()
    checksum = hashlib.sha256(data).hexdigest()
    storage_record = storage.write_bytes(
        f"worlds/{world_id}/worldlines/{worldline_id}/assets/{asset_id}/{key_suffix}.bin",
        data,
        content_type=mime_type,
    )
    session.add(
        MediaAsset(
            id=asset_id,
            world_id=world_id,
            worldline_id=worldline_id,
            asset_kind=asset_kind,
            asset_role=asset_role,
            source_kind=source_kind,
            status="available",
            visibility="world_admin",
            storage_uri=storage_record.uri,
            mime_type=mime_type,
            size_bytes=storage_record.size_bytes,
            checksum_sha256=checksum,
            source_job_id=source_job_id,
            source_invocation_id=source_invocation_id,
            created_by_actor_ref="test",
            metadata_json={},
        )
    )
    session.add(
        MediaObject(
            id=uuid.uuid4(),
            asset_id=asset_id,
            world_id=world_id,
            worldline_id=worldline_id,
            object_role="original",
            storage_uri=storage_record.uri,
            mime_type=mime_type,
            size_bytes=storage_record.size_bytes,
            checksum_sha256=checksum,
            metadata_json={},
        )
    )
    return asset_id
