from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from noveland.agents.models import Agent
from noveland.auth.models import User
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.events import WorldEventAppend, WorldEventStore
from noveland.events.models import WorldEventModel
from noveland.invocations.models import (
    AgentRuntimeRunModelInvocation,
    ModelInvocation,
    ModelInvocationTag,
    PromptSnapshot,
    PromptTemplate,
)
from noveland.media.contracts import (
    MediaAssetCreate,
    MediaAssetKind,
    MediaAssetRole,
    MediaAssetStatus,
    MediaObjectCreate,
    MediaObjectRole,
    MediaSourceKind,
    MediaVisibility,
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
from noveland.media.service import MediaService
from noveland.media.storage import LocalMediaObjectStorage
from noveland.memory.models import MemoryBackendProfile, MemoryWriteJob
from noveland.providers.budget import ProviderBudgetService
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderBudgetPolicyCreate,
    ProviderCapabilityCreate,
    ProviderIntegrationCreate,
    ProviderKind,
    ProviderScopeKind,
)
from noveland.providers.models import (
    ProviderBudgetPolicy,
    ProviderCapability,
    ProviderHealthCheck,
    ProviderIntegration,
)
from noveland.providers.registry import ProviderRegistryService
from noveland.providers.service import ProviderExecutionError
from noveland.speech.contracts import (
    SpeechStyleMappingCreate,
    STTRequest,
    TTSRequest,
    VoiceProfileCreate,
)
from noveland.speech.models import (
    AgentVoiceProfileBinding,
    SpeechStyleMapping,
    SpeechTranscript,
    VoiceProfile,
)
from noveland.speech.service import SpeechService
from noveland.speech.style_mapping import SpeechStyleMappingService
from noveland.speech.voice_profiles import SpeechValidationError, VoiceProfileService
from noveland.worlds.models import World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_tts_fake_provider_writes_invocation_media_job_asset_and_turn_reference(
    tmp_path: Path,
) -> None:
    engine = _engine()
    graph = _seed_world_graph(engine)
    event_id = _seed_event(engine, graph.world_id)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        provider_id = _seed_provider(
            session,
            graph.world_id,
            ProviderKind.TEXT_TO_SPEECH,
            capabilities=("supports_tts",),
        )
        voice_profile_id = _seed_voice_profile(
            session,
            graph.world_id,
            graph.worldline_id,
            provider_id=provider_id,
        )
        result = SpeechService(session, storage).text_to_speech(
            graph.world_id,
            TTSRequest(
                worldline_id=graph.worldline_id,
                provider_id=provider_id,
                voice_profile_id=voice_profile_id,
                text="read this line",
                emotion="shy",
                output_format="wav",
                conversation_id=graph.conversation_id,
                turn_id=graph.turn_id,
            ),
            actor_ref="user:test",
        )
        session.commit()

    with Session(engine) as session:
        invocation = session.get(ModelInvocation, result.model_invocation_id)
        snapshot = session.scalars(
            select(PromptSnapshot).where(PromptSnapshot.invocation_id == result.model_invocation_id)
        ).one()
        asset = session.get(MediaAsset, result.output_asset.id)
        job = session.get(MediaJob, result.media_job.id)
        ref = session.scalars(select(MediaReference)).one()
        event = session.get(WorldEventModel, event_id)
        assert invocation is not None
        assert invocation.invocation_kind == "text_to_speech"
        assert invocation.media_job_id == result.media_job.id
        assert invocation.media_asset_id == result.output_asset.id
        assert snapshot.raw_prompt_text == "read this line"
        assert asset is not None
        assert asset.asset_role == "speech_audio"
        assert asset.source_invocation_id == invocation.id
        assert result.output_objects[0].mime_type == "audio/wav"
        assert job is not None
        assert job.status == "succeeded"
        assert job.source_invocation_id == invocation.id
        assert ref.ref_kind == "conversation_turn"
        assert ref.ref_role == "output"
        assert event is not None
        assert event.payload == {"kind": "seed"}


def test_speech_service_accepts_template_capability_keys(tmp_path: Path) -> None:
    engine = _engine()
    graph = _seed_world_graph(engine)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        tts_provider_id = _seed_provider(
            session,
            graph.world_id,
            ProviderKind.TEXT_TO_SPEECH,
            capabilities=("speech.tts",),
        )
        stt_provider_id = _seed_provider(
            session,
            graph.world_id,
            ProviderKind.SPEECH_TO_TEXT,
            provider_key="fake-template-stt",
            capabilities=("speech.asr",),
        )
        voice_profile_id = _seed_voice_profile(
            session,
            graph.world_id,
            graph.worldline_id,
            provider_id=tts_provider_id,
        )
        source_asset_id = _seed_audio_asset(
            session,
            storage,
            graph.world_id,
            graph.worldline_id,
        )

        tts = SpeechService(session, storage).text_to_speech(
            graph.world_id,
            TTSRequest(
                worldline_id=graph.worldline_id,
                provider_id=tts_provider_id,
                voice_profile_id=voice_profile_id,
                text="template capability tts",
            ),
            actor_ref="user:test",
        )
        stt = SpeechService(session, storage).speech_to_text(
            graph.world_id,
            STTRequest(
                worldline_id=graph.worldline_id,
                provider_id=stt_provider_id,
                source_asset_id=source_asset_id,
            ),
            actor_ref="user:test",
        )

    assert tts.output_asset.asset_role == "speech_audio"
    assert stt.transcript.transcript_text == "fake transcript"


def test_stt_fake_provider_writes_invocation_transcript_job_and_turn_reference(
    tmp_path: Path,
) -> None:
    engine = _engine()
    graph = _seed_world_graph(engine)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        provider_id = _seed_provider(
            session,
            graph.world_id,
            ProviderKind.SPEECH_TO_TEXT,
            capabilities=("supports_stt",),
        )
        source_asset_id = _seed_audio_asset(session, storage, graph.world_id, graph.worldline_id)
        result = SpeechService(session, storage).speech_to_text(
            graph.world_id,
            STTRequest(
                worldline_id=graph.worldline_id,
                provider_id=provider_id,
                source_asset_id=source_asset_id,
                language="ja",
                timestamps=True,
                conversation_id=graph.conversation_id,
                turn_id=graph.turn_id,
                speaker_actor_ref="agent:test",
            ),
            actor_ref="user:test",
        )
        session.commit()

    with Session(engine) as session:
        invocation = session.get(ModelInvocation, result.model_invocation_id)
        transcript = session.get(SpeechTranscript, result.transcript.id)
        job = session.get(MediaJob, result.media_job.id)
        references = session.scalars(select(MediaReference)).all()
        assert invocation is not None
        assert invocation.invocation_kind == "speech_to_text"
        assert invocation.media_job_id == result.media_job.id
        assert invocation.media_asset_id == source_asset_id
        assert transcript is not None
        assert transcript.model_invocation_id == invocation.id
        assert transcript.transcript_text == "fake transcript"
        assert transcript.speaker_actor_ref == "agent:test"
        assert job is not None
        assert job.status == "succeeded"
        assert job.source_invocation_id == invocation.id
        assert len(references) == 1
        assert references[0].asset_id == source_asset_id
        assert references[0].ref_role == "input"
        assert references[0].metadata_json["source"] == "stt"
        assert session.scalars(select(MemoryWriteJob)).all() == []
        turn = session.get(ConversationTurn, graph.turn_id)
        assert turn is not None
        assert turn.input_text == "hi"
        assert turn.output_text == "hello"


def test_style_mapping_and_unsupported_emotion_fallback(tmp_path: Path) -> None:
    engine = _engine()
    graph = _seed_world_graph(engine)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        provider_id = _seed_provider(
            session,
            graph.world_id,
            ProviderKind.TEXT_TO_SPEECH,
            capabilities=("supports_tts",),
        )
        voice_profile_id = _seed_voice_profile(
            session,
            graph.world_id,
            graph.worldline_id,
            provider_id=provider_id,
        )
        SpeechStyleMappingService(session).create_mapping(
            SpeechStyleMappingCreate(
                world_id=graph.world_id,
                mapping_key="mimo-shy",
                provider_kind="fake",
                emotion_key="shy",
                style_json={"emotion": "soft", "speed": 0.9},
            )
        )
        mapped = SpeechService(session, storage).text_to_speech(
            graph.world_id,
            TTSRequest(
                worldline_id=graph.worldline_id,
                provider_id=provider_id,
                voice_profile_id=voice_profile_id,
                text="mapped",
                emotion="shy",
            ),
            actor_ref="user:test",
        )
        fallback = SpeechService(session, storage).text_to_speech(
            graph.world_id,
            TTSRequest(
                worldline_id=graph.worldline_id,
                provider_id=provider_id,
                voice_profile_id=voice_profile_id,
                text="fallback",
                emotion="angry",
            ),
            actor_ref="user:test",
        )
        session.commit()

    with Session(engine) as session:
        mapped_invocation = session.get(ModelInvocation, mapped.model_invocation_id)
        fallback_invocation = session.get(ModelInvocation, fallback.model_invocation_id)
        assert mapped_invocation is not None
        assert fallback_invocation is not None
        assert mapped_invocation.request_params_json is not None
        assert fallback_invocation.request_params_json is not None
        assert mapped_invocation.request_params_json["request"]["style_json"] == {
            "emotion": "soft",
            "speed": 0.9,
        }
        assert fallback_invocation.request_params_json["request"]["style_json"] == {
            "emotion": "angry"
        }


def test_speech_service_rejects_missing_capability_and_cross_worldline_source(
    tmp_path: Path,
) -> None:
    engine = _engine()
    graph = _seed_world_graph(engine)
    fork_id = _seed_fork(engine, graph.world_id, graph.worldline_id)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        tts_provider_id = _seed_provider(
            session,
            graph.world_id,
            ProviderKind.TEXT_TO_SPEECH,
            capabilities=(),
        )
        voice_profile_id = _seed_voice_profile(
            session,
            graph.world_id,
            graph.worldline_id,
            provider_id=tts_provider_id,
        )
        with pytest.raises(SpeechValidationError, match="supports_tts"):
            SpeechService(session, storage).text_to_speech(
                graph.world_id,
                TTSRequest(
                    worldline_id=graph.worldline_id,
                    provider_id=tts_provider_id,
                    voice_profile_id=voice_profile_id,
                    text="blocked",
                ),
                actor_ref="user:test",
            )

        stt_provider_id = _seed_provider(
            session,
            graph.world_id,
            ProviderKind.SPEECH_TO_TEXT,
            provider_key="fake-stt",
            capabilities=("supports_stt",),
        )
        fork_audio_id = _seed_audio_asset(session, storage, graph.world_id, fork_id)
        with pytest.raises(SpeechValidationError, match="request worldline"):
            SpeechService(session, storage).speech_to_text(
                graph.world_id,
                STTRequest(
                    worldline_id=graph.worldline_id,
                    provider_id=stt_provider_id,
                    source_asset_id=fork_audio_id,
                ),
                actor_ref="user:test",
            )


def test_tts_blocks_disabled_provider_and_marks_job_failed(tmp_path: Path) -> None:
    engine = _engine()
    graph = _seed_world_graph(engine)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        provider_id = _seed_provider(
            session,
            graph.world_id,
            ProviderKind.TEXT_TO_SPEECH,
            capabilities=("supports_tts",),
        )
        voice_profile_id = _seed_voice_profile(
            session,
            graph.world_id,
            graph.worldline_id,
            provider_id=provider_id,
        )
        provider = session.get(ProviderIntegration, provider_id)
        assert provider is not None
        provider.status = "disabled"
        with pytest.raises(ProviderExecutionError, match="disabled"):
            SpeechService(session, storage).text_to_speech(
                graph.world_id,
                TTSRequest(
                    worldline_id=graph.worldline_id,
                    provider_id=provider_id,
                    voice_profile_id=voice_profile_id,
                    text="blocked speech",
                ),
                actor_ref="user:test",
            )
        invocation = session.scalars(select(ModelInvocation)).one()
        job = session.scalars(select(MediaJob)).one()
        assert invocation.status == "failed"
        assert invocation.request_params_json is not None
        assert invocation.request_params_json["provider_status"] == "disabled"
        assert job.status == "failed"
        assert session.scalars(select(MediaAsset)).all() == []


def test_tts_budget_block_marks_job_failed(tmp_path: Path) -> None:
    engine = _engine()
    graph = _seed_world_graph(engine)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        provider_id = _seed_provider(
            session,
            graph.world_id,
            ProviderKind.TEXT_TO_SPEECH,
            capabilities=("supports_tts",),
        )
        voice_profile_id = _seed_voice_profile(
            session,
            graph.world_id,
            graph.worldline_id,
            provider_id=provider_id,
        )
        ProviderBudgetService(session).create_policy(
            ProviderBudgetPolicyCreate(
                world_id=graph.world_id,
                provider_id=provider_id,
                policy_key="stop-speech",
                emergency_stop_enabled=True,
            )
        )
        with pytest.raises(ProviderExecutionError, match="emergency_stop"):
            SpeechService(session, storage).text_to_speech(
                graph.world_id,
                TTSRequest(
                    worldline_id=graph.worldline_id,
                    provider_id=provider_id,
                    voice_profile_id=voice_profile_id,
                    text="blocked speech",
                ),
                actor_ref="user:test",
            )
        invocation = session.scalars(select(ModelInvocation)).one()
        job = session.scalars(select(MediaJob)).one()
        assert invocation.status == "failed"
        assert invocation.request_params_json is not None
        assert invocation.request_params_json["budget_blocked"] is True
        assert job.status == "failed"
        assert session.scalars(select(MediaAsset)).all() == []


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
        cast(Table, Agent.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, MemoryWriteJob.__table__),
        cast(Table, ProviderIntegration.__table__),
        cast(Table, ProviderCapability.__table__),
        cast(Table, ProviderHealthCheck.__table__),
        cast(Table, ProviderBudgetPolicy.__table__),
        cast(Table, MediaJob.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, MediaObject.__table__),
        cast(Table, MediaReference.__table__),
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
    ):
        table.create(engine)
    return engine


class _Graph:
    def __init__(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
    ) -> None:
        self.world_id = world_id
        self.worldline_id = worldline_id
        self.agent_id = agent_id
        self.conversation_id = conversation_id
        self.turn_id = turn_id


def _seed_world_graph(engine: Engine) -> _Graph:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
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
                status="draft",
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
                speaker_kind="operator",
                input_text="hi",
                output_text="hello",
                status="succeeded",
            )
        )
        session.commit()
        return _Graph(world_id, worldline.id, agent_id, conversation_id, turn_id)


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


def _seed_provider(
    session: Session,
    world_id: uuid.UUID,
    provider_kind: ProviderKind,
    *,
    capabilities: tuple[str, ...],
    provider_key: str | None = None,
) -> uuid.UUID:
    provider = ProviderRegistryService(session).create_provider(
        ProviderIntegrationCreate(
            world_id=world_id,
            scope_kind=ProviderScopeKind.WORLD,
            provider_kind=provider_kind,
            adapter_kind=ProviderAdapterKind.FAKE,
            provider_key=provider_key or f"fake-{provider_kind.value}",
            display_name=f"Fake {provider_kind.value}",
            capabilities=tuple(
                ProviderCapabilityCreate(capability_key=capability, capability_json={"value": True})
                for capability in capabilities
            ),
        )
    )
    return provider.id


def _seed_voice_profile(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    provider_id: uuid.UUID,
) -> uuid.UUID:
    profile = VoiceProfileService(session).create_profile(
        VoiceProfileCreate(
            world_id=world_id,
            worldline_id=worldline_id,
            profile_key=f"voice-{uuid.uuid4().hex[:8]}",
            display_name="Voice",
            provider_integration_id=provider_id,
            provider_voice_id="voice_123",
        )
    )
    return profile.id


def _seed_audio_asset(
    session: Session,
    storage: LocalMediaObjectStorage,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> uuid.UUID:
    asset_id = uuid.uuid4()
    stored = storage.write_bytes(
        f"worlds/{world_id}/worldlines/{worldline_id}/assets/{asset_id}/source.wav",
        _wav_bytes(),
        content_type="audio/wav",
    )
    asset = MediaService(session, storage).create_asset(
        MediaAssetCreate(
            world_id=world_id,
            worldline_id=worldline_id,
            asset_kind=MediaAssetKind.AUDIO,
            asset_role=MediaAssetRole.TRANSCRIPT_AUDIO,
            source_kind=MediaSourceKind.MANUAL_UPLOAD,
            status=MediaAssetStatus.AVAILABLE,
            visibility=MediaVisibility.WORLD_ADMIN,
            storage_uri=stored.uri,
            mime_type="audio/wav",
            file_ext="wav",
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
        ),
        actor_ref="user:test",
    )
    MediaService(session, storage).add_object(
        world_id,
        asset.id,
        MediaObjectCreate(
            world_id=world_id,
            worldline_id=worldline_id,
            object_role=MediaObjectRole.ORIGINAL,
            storage_uri=stored.uri,
            filename="source.wav",
            mime_type="audio/wav",
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
        ),
    )
    return asset.id


def _seed_event(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        event = WorldEventStore(session).append_event(
            WorldEventAppend(
                world_id=world_id,
                event_name="speech.seed_event",
                payload={"kind": "seed"},
                wall_time=datetime.now(UTC),
                actor_ref="test",
            )
        )
        session.commit()
        return event.id


def _wav_bytes() -> bytes:
    return (
        b"RIFF(\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
        b"\x01\x00\x01\x00@\x1f\x00\x00@\x1f\x00\x00"
        b"\x01\x00\x08\x00data\x04\x00\x00\x00\x00\x00\x00\x00"
    )
