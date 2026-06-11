from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from fastapi.testclient import TestClient
from noveland.agents.models import Agent
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.conversations.models import ConversationSession, ConversationTurn
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
from noveland.providers.models import (
    ProviderBudgetPolicy,
    ProviderCapability,
    ProviderHealthCheck,
    ProviderIntegration,
)
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.services.api.speech import _speech_storage
from noveland.speech.models import (
    AgentVoiceProfileBinding,
    SpeechStyleMapping,
    SpeechTranscript,
    VoiceProfile,
)
from noveland.worlds.models import World, Worldline, WorldMembership
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_speech_api_voice_profiles_tts_stt_and_acl() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    platform_id, platform_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    agent_id, conversation_id, turn_id = _seed_agent_and_conversation(
        engine,
        world_id,
        worldline_id,
    )
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    tts_provider_id = _seed_provider(
        engine,
        world_id,
        provider_kind="text_to_speech",
        provider_key="fake-tts",
        capabilities=("supports_tts",),
    )
    stt_provider_id = _seed_provider(
        engine,
        world_id,
        provider_kind="speech_to_text",
        provider_key="fake-stt",
        capabilities=("supports_stt",),
    )
    source_asset_id = _seed_audio_asset(
        engine,
        client.speech_storage,
        world_id,
        worldline_id,
        role="transcript_audio",
    )

    _authenticate(client, member_token)
    member_create = client.post(
        f"/worlds/{world_id}/speech/voice-profiles",
        json={"profile_key": "member", "display_name": "Member"},
    )

    _authenticate(client, owner_token)
    developer_only = client.post(
        f"/worlds/{world_id}/speech/voice-profiles",
        json={
            "profile_key": "hidden-voice",
            "display_name": "Hidden Voice",
            "visibility": "developer_only",
        },
    )
    profile = client.post(
        f"/worlds/{world_id}/speech/voice-profiles",
        json={
            "worldline_id": str(worldline_id),
            "profile_key": "hero",
            "display_name": "Hero",
            "provider_integration_id": str(tts_provider_id),
            "provider_voice_id": "voice_123",
            "reference_asset_id": str(source_asset_id),
        },
    )
    profile_id = profile.json()["id"]
    binding = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/voice-profiles",
        json={
            "worldline_id": str(worldline_id),
            "voice_profile_id": profile_id,
            "is_default": True,
        },
    )
    style = client.post(
        f"/worlds/{world_id}/speech/style-mappings",
        json={
            "mapping_key": "fake-shy",
            "provider_kind": "fake",
            "emotion_key": "shy",
            "style_json": {"emotion": "soft"},
        },
    )
    tts = client.post(
        f"/worlds/{world_id}/speech/tts",
        json={
            "worldline_id": str(worldline_id),
            "provider_id": str(tts_provider_id),
            "agent_id": str(agent_id),
            "text": "hello",
            "emotion": "shy",
            "conversation_id": str(conversation_id),
            "turn_id": str(turn_id),
        },
    )
    stt = client.post(
        f"/worlds/{world_id}/speech/stt",
        json={
            "worldline_id": str(worldline_id),
            "provider_id": str(stt_provider_id),
            "source_asset_id": str(source_asset_id),
            "conversation_id": str(conversation_id),
            "turn_id": str(turn_id),
        },
    )
    transcripts = client.get(f"/worlds/{world_id}/speech/transcripts")
    owner_profiles = client.get(f"/worlds/{world_id}/speech/voice-profiles")

    _authenticate(client, platform_token)
    platform_profile = client.post(
        f"/worlds/{world_id}/speech/voice-profiles",
        json={
            "profile_key": "platform-hidden",
            "display_name": "Platform Hidden",
            "visibility": "developer_only",
        },
    )
    platform_profiles = client.get(f"/worlds/{world_id}/speech/voice-profiles")

    assert platform_id
    assert member_create.status_code == 403
    assert developer_only.status_code == 403
    assert profile.status_code == 201
    assert binding.status_code == 201
    assert binding.json()["is_default"] is True
    assert style.status_code == 201
    assert tts.status_code == 201
    tts_body = tts.json()
    assert tts_body["output_asset"]["asset_role"] == "speech_audio"
    assert tts_body["output_objects"][0]["mime_type"] == "audio/wav"
    _assert_safe_speech_response(tts_body)
    assert stt.status_code == 201
    stt_body = stt.json()
    assert stt_body["transcript"]["transcript_text"] == "fake transcript"
    _assert_safe_speech_response(stt_body)
    assert transcripts.status_code == 200
    assert transcripts.json()[0]["source_asset_id"] == str(source_asset_id)
    assert owner_profiles.status_code == 200
    assert [record["profile_key"] for record in owner_profiles.json()] == ["hero"]
    assert platform_profile.status_code == 201
    assert {record["profile_key"] for record in platform_profiles.json()} == {
        "hero",
        "platform-hidden",
    }

    with Session(engine) as session:
        invocations = session.scalars(select(ModelInvocation)).all()
        assert len(invocations) == 2
        assert {invocation.invocation_kind for invocation in invocations} == {
            "text_to_speech",
            "speech_to_text",
        }
        assert len(session.scalars(select(MediaReference)).all()) == 2
        turn = session.get(ConversationTurn, turn_id)
        assert turn is not None
        assert turn.input_text == "hi"
        assert turn.output_text == "hello"
        assert session.scalars(select(MemoryWriteJob)).all() == []


class _SpeechApiClient(TestClient):
    speech_storage: LocalMediaObjectStorage


def _assert_safe_speech_response(body: dict[str, object]) -> None:
    serialized = json.dumps(body)
    assert "storage_uri" not in serialized
    assert "media://" not in serialized
    assert "request_json" not in serialized
    assert "result_json" not in serialized
    assert "provider_config_json" not in serialized
    invocation = body["model_invocation"]
    assert isinstance(invocation, dict)
    for forbidden_field in (
        "input_text",
        "output_text",
        "input_json",
        "output_json",
        "request_params_json",
        "response_metadata_json",
        "error_text",
    ):
        assert forbidden_field not in invocation



def _client_with_database() -> tuple[_SpeechApiClient, Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _create_tables(engine)
    app = create_app()

    def override_get_db_session() -> Iterator[Session]:
        with Session(engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session
    storage_tmp = TemporaryDirectory()
    storage = LocalMediaObjectStorage(Path(storage_tmp.name))
    app.dependency_overrides[_speech_storage] = lambda: storage
    app.state._speech_storage_tmp = storage_tmp
    client = _SpeechApiClient(app)
    client.speech_storage = storage
    return client, engine


def _create_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, Agent.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
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


def _seed_user(
    engine: Engine,
    email: str,
    *,
    platform_admin: bool = False,
) -> tuple[uuid.UUID, str]:
    user_id = uuid.uuid4()
    token = f"token-{user_id}"
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(User(id=user_id, email=email, display_name=email, is_active=True))
        session.add(
            AuthSession(
                id=uuid.uuid4(),
                user_id=user_id,
                token_hash=hash_session_token(token),
                status=AuthSessionStatus.ACTIVE.value,
                expires_at=now + timedelta(hours=1),
            )
        )
        if platform_admin:
            session.add(
                PlatformRoleAssignment(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    role=AuthRole.PLATFORM_ADMIN.value,
                    assigned_at=now,
                )
            )
        session.commit()
    return user_id, token


def _seed_world(engine: Engine, owner_user_id: uuid.UUID) -> uuid.UUID:
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=owner_user_id,
                slug=f"world-{world_id.hex[:8]}",
                name="World",
                is_active=True,
            )
        )
        session.commit()
    return world_id


def _seed_worldline(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        primary = ensure_primary_worldline(session, world_id)
        session.commit()
        return primary.id


def _seed_agent_and_conversation(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    agent_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    turn_id = uuid.uuid4()
    with Session(engine) as session:
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
                worldline_id=worldline_id,
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
        return agent_id, conversation_id, turn_id


def _add_membership(
    engine: Engine,
    world_id: uuid.UUID,
    user_id: uuid.UUID,
    role: AuthRole,
) -> None:
    with Session(engine) as session:
        session.add(
            WorldMembership(
                id=uuid.uuid4(),
                world_id=world_id,
                user_id=user_id,
                role=role.value,
            )
        )
        session.commit()


def _seed_provider(
    engine: Engine,
    world_id: uuid.UUID,
    *,
    provider_kind: str,
    provider_key: str,
    capabilities: tuple[str, ...],
) -> uuid.UUID:
    provider_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            ProviderIntegration(
                id=provider_id,
                world_id=world_id,
                scope_kind="world",
                scope_key=f"world:{world_id}",
                provider_kind=provider_kind,
                adapter_kind="fake",
                provider_key=provider_key,
                display_name=provider_key,
                config_json={},
                default_params_json={},
                status="active",
                visibility="world_admin",
            )
        )
        for capability_key in capabilities:
            session.add(
                ProviderCapability(
                    id=uuid.uuid4(),
                    provider_integration_id=provider_id,
                    capability_key=capability_key,
                    capability_json={"value": True},
                )
            )
        session.commit()
    return provider_id


def _seed_audio_asset(
    engine: Engine,
    storage: LocalMediaObjectStorage,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    role: str,
) -> uuid.UUID:
    asset_id = uuid.uuid4()
    stored = storage.write_bytes(
        f"worlds/{world_id}/worldlines/{worldline_id}/assets/{asset_id}/source.wav",
        _wav_bytes(),
        content_type="audio/wav",
    )
    with Session(engine) as session:
        session.add(
            MediaAsset(
                id=asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind="audio",
                asset_role=role,
                source_kind="manual_upload",
                status="available",
                visibility="world_admin",
                storage_uri=stored.uri,
                mime_type="audio/wav",
                file_ext="wav",
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
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
                storage_uri=stored.uri,
                filename="source.wav",
                mime_type="audio/wav",
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
                metadata_json={},
            )
        )
        session.commit()
    return asset_id


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _wav_bytes() -> bytes:
    return (
        b"RIFF(\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
        b"\x01\x00\x01\x00@\x1f\x00\x00@\x1f\x00\x00"
        b"\x01\x00\x08\x00data\x04\x00\x00\x00\x00\x00\x00\x00"
    )
