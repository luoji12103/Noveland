from __future__ import annotations

import uuid
from pathlib import Path
from typing import cast

import pytest
from noveland.agents.models import Agent
from noveland.auth.models import User
from noveland.conversations.models import ConversationSession, ConversationTurn
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
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderIntegrationCreate,
    ProviderKind,
    ProviderScopeKind,
)
from noveland.providers.models import ProviderCapability, ProviderHealthCheck, ProviderIntegration
from noveland.providers.registry import ProviderRegistryService
from noveland.speech.contracts import (
    AgentVoiceProfileBindingCreate,
    VoiceBindingRole,
    VoiceKind,
    VoiceProfileCreate,
)
from noveland.speech.models import (
    AgentVoiceProfileBinding,
    SpeechStyleMapping,
    SpeechTranscript,
    VoiceProfile,
)
from noveland.speech.voice_profiles import SpeechValidationError, VoiceProfileService
from noveland.worlds.models import World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_voice_profile_binding_and_default_resolution(tmp_path: Path) -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_graph(engine)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        provider_id = _seed_provider(session, world_id)
        reference_asset_id = _seed_audio_asset(session, storage, world_id, worldline_id)
        service = VoiceProfileService(session)
        profile = service.create_profile(
            VoiceProfileCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                profile_key="hero",
                display_name="Hero",
                owner_agent_id=agent_id,
                provider_integration_id=provider_id,
                provider_voice_id="voice_123",
                voice_kind=VoiceKind.EXTERNAL_PROVIDER,
                reference_asset_id=reference_asset_id,
                supported_languages=["ja", "zh"],
            )
        )
        binding = service.bind_agent_voice(
            AgentVoiceProfileBindingCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                voice_profile_id=profile.id,
                is_default=True,
                style_overrides_json={"speed": 0.95},
            )
        )
        resolved_profile, resolved_binding = service.resolve_agent_default(
            world_id,
            agent_id,
            worldline_id,
        )

    assert profile.reference_asset_id == reference_asset_id
    assert profile.supported_languages == ["ja", "zh"]
    assert binding.is_default is True
    assert resolved_profile.id == profile.id
    assert resolved_binding is not None
    assert resolved_binding.style_overrides_json == {"speed": 0.95}


def test_voice_profile_allows_many_agents_and_one_default_per_agent(tmp_path: Path) -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_graph(engine)
    second_agent_id = _seed_agent(engine, world_id, "agent-2")
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        reference_asset_id = _seed_audio_asset(session, storage, world_id, worldline_id)
        service = VoiceProfileService(session)
        shared = service.create_profile(
            VoiceProfileCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                profile_key="shared",
                display_name="Shared",
                reference_asset_id=reference_asset_id,
            )
        )
        fallback = service.create_profile(
            VoiceProfileCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                profile_key="fallback",
                display_name="Fallback",
            )
        )
        service.bind_agent_voice(
            AgentVoiceProfileBindingCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                voice_profile_id=shared.id,
                is_default=True,
            )
        )
        service.bind_agent_voice(
            AgentVoiceProfileBindingCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=second_agent_id,
                voice_profile_id=shared.id,
                is_default=True,
            )
        )
        service.bind_agent_voice(
            AgentVoiceProfileBindingCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                voice_profile_id=fallback.id,
                binding_role=VoiceBindingRole.ALTERNATE,
                is_default=True,
            )
        )
        session.flush()
        first_agent_bindings = service.list_agent_bindings(
            world_id,
            agent_id,
            worldline_id=worldline_id,
        )
        second_agent_bindings = service.list_agent_bindings(
            world_id,
            second_agent_id,
            worldline_id=worldline_id,
        )

    assert len(first_agent_bindings) == 2
    assert sum(1 for binding in first_agent_bindings if binding.is_default) == 1
    assert first_agent_bindings[0].voice_profile_id == fallback.id
    assert len(second_agent_bindings) == 1
    assert second_agent_bindings[0].voice_profile_id == shared.id


def test_world_level_voice_profile_rejects_worldline_reference_asset(tmp_path: Path) -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_graph(engine)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        reference_asset_id = _seed_audio_asset(session, storage, world_id, worldline_id)
        with pytest.raises(SpeechValidationError, match="world-level voice profiles"):
            VoiceProfileService(session).create_profile(
                VoiceProfileCreate(
                    world_id=world_id,
                    worldline_id=None,
                    profile_key="world-ref",
                    display_name="World Ref",
                    reference_asset_id=reference_asset_id,
                )
            )


def test_voice_profile_rejects_reference_asset_from_other_worldline(tmp_path: Path) -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_graph(engine)
    fork_id = _seed_fork(engine, world_id, worldline_id)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        reference_asset_id = _seed_audio_asset(session, storage, world_id, fork_id)
        with pytest.raises(SpeechValidationError, match="match profile worldline"):
            VoiceProfileService(session).create_profile(
                VoiceProfileCreate(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    profile_key="bad-ref",
                    display_name="Bad Ref",
                    reference_asset_id=reference_asset_id,
                )
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
        cast(Table, Agent.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, MemoryWriteJob.__table__),
        cast(Table, ProviderIntegration.__table__),
        cast(Table, ProviderCapability.__table__),
        cast(Table, ProviderHealthCheck.__table__),
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


def _seed_world_graph(engine: Engine) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
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
        session.commit()
        return world_id, worldline.id, agent_id


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
            )
        )
        session.commit()
    return agent_id


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


def _seed_provider(session: Session, world_id: uuid.UUID) -> uuid.UUID:
    provider = ProviderRegistryService(session).create_provider(
        ProviderIntegrationCreate(
            world_id=world_id,
            scope_kind=ProviderScopeKind.WORLD,
            provider_kind=ProviderKind.TEXT_TO_SPEECH,
            adapter_kind=ProviderAdapterKind.FAKE,
            provider_key="fake-tts",
            display_name="Fake TTS",
        )
    )
    return provider.id


def _seed_audio_asset(
    session: Session,
    storage: LocalMediaObjectStorage,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> uuid.UUID:
    asset_id = uuid.uuid4()
    stored = storage.write_bytes(
        f"worlds/{world_id}/worldlines/{worldline_id}/assets/{asset_id}/voice.wav",
        _wav_bytes(),
        content_type="audio/wav",
    )
    asset = MediaService(session, storage).create_asset(
        MediaAssetCreate(
            world_id=world_id,
            worldline_id=worldline_id,
            asset_kind=MediaAssetKind.AUDIO,
            asset_role=MediaAssetRole.VOICE_SAMPLE,
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
            filename="voice.wav",
            mime_type="audio/wav",
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
        ),
    )
    return asset.id


def _wav_bytes() -> bytes:
    return (
        b"RIFF(\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
        b"\x01\x00\x01\x00@\x1f\x00\x00@\x1f\x00\x00"
        b"\x01\x00\x08\x00data\x04\x00\x00\x00\x00\x00\x00\x00"
    )
