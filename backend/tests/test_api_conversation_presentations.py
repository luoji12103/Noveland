from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

from fastapi.testclient import TestClient
from noveland.agents.models import Agent
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
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
from noveland.media.contracts import (
    MediaAssetCreate,
    MediaAssetKind,
    MediaAssetRole,
    MediaAssetStatus,
    MediaObjectCreate,
    MediaObjectRole,
    MediaReferenceKind,
    MediaReferenceRole,
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
from noveland.moderation.models import ModerationAction
from noveland.narrative.models import NarrativeArtifact
from noveland.providers.models import (
    ProviderBudgetPolicy,
    ProviderCapability,
    ProviderHealthCheck,
    ProviderIntegration,
)
from noveland.services.api.app import create_app
from noveland.services.api.conversation_presentations import _presentation_storage
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.speech.models import (
    AgentVoiceProfileBinding,
    SpeechStyleMapping,
    SpeechTranscript,
    VoiceProfile,
)
from noveland.visual.contracts import (
    SceneBackgroundCreate,
    SpriteSetCreate,
    SpriteVariantCreate,
)
from noveland.visual.models import (
    CharacterSpriteSet,
    CharacterSpriteVariant,
    SceneBackgroundProfile,
)
from noveland.visual.service import VisualAssetService
from noveland.worlds.models import Scene, World, Worldline, WorldMembership
from noveland.worlds.worldlines import ensure_primary_worldline
from PIL import Image
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_conversation_presentation_api_renders_visual_speech_and_transcript() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    agent_id, scene_id, conversation_id, turn_id = _seed_agent_scene_conversation(
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
    sprite_asset = _seed_image_asset(
        engine,
        client.presentation_storage,
        world_id,
        worldline_id,
        role=MediaAssetRole.CHARACTER_SPRITE,
        color=(255, 0, 0, 255),
    )
    neutral_asset = _seed_image_asset(
        engine,
        client.presentation_storage,
        world_id,
        worldline_id,
        role=MediaAssetRole.CHARACTER_SPRITE,
        color=(0, 255, 0, 255),
    )
    background_asset = _seed_image_asset(
        engine,
        client.presentation_storage,
        world_id,
        worldline_id,
        role=MediaAssetRole.SCENE_BACKGROUND,
        color=(0, 0, 255, 255),
    )
    source_audio_asset = _seed_audio_asset(
        engine,
        client.presentation_storage,
        world_id,
        worldline_id,
    )
    sprite_set_id, happy_variant_id, neutral_variant_id = _seed_visual_bindings(
        engine,
        world_id,
        worldline_id,
        agent_id,
        scene_id,
        sprite_asset,
        neutral_asset,
        background_asset,
    )
    voice_profile_id = _seed_voice_profile(
        engine,
        world_id,
        worldline_id,
        agent_id,
        tts_provider_id,
    )

    _authenticate(client, member_token)
    member_put = client.put(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation",
        json={"emotion_key": "happy"},
    )
    member_patch = client.patch(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation",
        json={"emotion_key": "happy"},
    )
    member_render_visual = client.post(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation/render-visual",
        json={"location_key": "classroom"},
    )

    _authenticate(client, owner_token)
    put_response = client.put(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation",
        json={
            "speaker_agent_id": str(agent_id),
            "emotion_key": "happy",
            "emotion_intensity": 0.75,
            "sprite_set_id": str(sprite_set_id),
            "sprite_variant_id": str(happy_variant_id),
            "voice_profile_id": str(voice_profile_id),
            "presentation_json": {"panel": "main"},
        },
    )
    patch_response = client.patch(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation",
        json={"emotion_key": "shy"},
    )
    visual_response = client.post(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation/render-visual",
        json={
            "emotion_key": "angry",
            "emotion_intensity": 0.8,
            "scene_id": str(scene_id),
            "location_key": "classroom",
            "time_of_day": "night",
        },
    )
    speech_response = client.post(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation/render-speech",
        json={
            "provider_id": str(tts_provider_id),
            "emotion_key": "shy",
            "emotion_intensity": 0.8,
        },
    )
    stt_response = client.post(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation/transcribe-audio",
        json={
            "provider_id": str(stt_provider_id),
            "source_asset_id": str(source_audio_asset),
        },
    )
    dirty_presentation_json: dict[str, Any] = {
        "caption": "safe caption",
        "storage_uri": "media://private/presentation",
        "rawPrompt": "operator prompt",
        "promptSnapshotId": str(uuid.uuid4()),
        "provider": {"adapter_kind": "fake"},
        "visual": {
            "sprite_fallback_reason": "default",
            "compose_media_job_id": str(uuid.uuid4()),
        },
        "speech": {
            "tts_media_job_id": str(uuid.uuid4()),
            "model_invocation_id": str(uuid.uuid4()),
        },
        "nested": [
            {"safe": "keep"},
            {
                "raw_output": "provider output",
                "rawOutput": "provider camel output",
                "storageUri": "opaque-presentation-storage",
                "path": "/tmp/presentation.json",
            },
        ],
    }
    with Session(engine) as session:
        presentation = session.get(
            ConversationTurnPresentation,
            uuid.UUID(stt_response.json()["id"]),
        )
        assert presentation is not None
        presentation.presentation_json = dirty_presentation_json
        session.commit()

    get_response = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation",
    )
    leak_response = client.patch(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation",
        json={"presentation_json": {"nested": {"storage_uri": "local://leak"}}},
    )
    _authenticate(client, member_token)
    member_get = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation",
    )

    assert member_put.status_code == 403
    assert member_patch.status_code == 403
    assert member_render_visual.status_code == 403
    assert put_response.status_code == 200
    assert put_response.json()["emotion_intensity"] == 0.75
    assert patch_response.status_code == 200
    assert patch_response.json()["emotion_key"] == "shy"
    assert visual_response.status_code == 201
    assert visual_response.json()["sprite_variant_id"] == str(neutral_variant_id)
    assert visual_response.json()["background_asset_id"] == str(background_asset)
    assert visual_response.json()["composite_scene_asset_id"] is not None
    assert speech_response.status_code == 201
    assert speech_response.json()["tts_media_asset_id"] is not None
    assert stt_response.status_code == 201
    assert stt_response.json()["transcript_id"] is not None
    assert get_response.status_code == 200
    assert get_response.json()["transcript_id"] == stt_response.json()["transcript_id"]
    assert get_response.json()["sprite_set_id"] == str(sprite_set_id)
    assert get_response.json()["sprite_variant_id"] == str(neutral_variant_id)
    assert "media://private/presentation" in _json_text(get_response.json())
    assert "model_invocation_id" in _json_text(get_response.json())
    assert leak_response.status_code == 422
    assert member_get.status_code == 200
    member_presentation = member_get.json()
    assert member_presentation["speaker_agent_id"] == str(agent_id)
    assert member_presentation["background_asset_id"] is None
    assert member_presentation["composite_scene_asset_id"] is None
    assert member_presentation["tts_media_asset_id"] is None
    assert member_presentation["sprite_set_id"] is None
    assert member_presentation["sprite_variant_id"] is None
    assert member_presentation["voice_profile_id"] is None
    assert member_presentation["transcript_id"] is None
    assert member_presentation["presentation_json"]["caption"] == "safe caption"
    assert member_presentation["presentation_json"]["nested"][0]["safe"] == "keep"
    member_presentation_text = _json_text(member_presentation)
    for forbidden_marker in (
        "media://private/presentation",
        "model_invocation_id",
        "media_job",
        "raw_output",
        "rawOutput",
        "rawPrompt",
        "promptSnapshot",
        "storageUri",
        "/tmp/presentation.json",
        "adapter_kind",
    ):
        assert forbidden_marker not in member_presentation_text
    assert "storage_uri" not in _json_text(visual_response.json())
    assert "storage_uri" not in _json_text(speech_response.json())
    assert "storage_uri" not in _json_text(stt_response.json())

    with Session(engine) as session:
        assert len(session.scalars(select(ModelInvocation)).all()) == 2
        assert len(session.scalars(select(SpeechTranscript)).all()) == 1
        assert session.scalars(select(WorldEventModel)).all() == []
        assert len(session.scalars(select(MediaJob)).all()) == 3
        refs = session.scalars(select(MediaReference)).all()
        assert {ref.ref_role for ref in refs} >= {
            "character_sprite",
            "background",
            "output",
            "input",
        }
        turn = session.get(ConversationTurn, turn_id)
        assert turn is not None
        assert turn.input_text == "hi"
        assert turn.output_text == "hello"
        assert session.scalars(select(MemoryWriteJob)).all() == []


def test_member_presentation_get_only_keeps_reader_deliverable_media_ids() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner-media-filter@example.test")
    member_id, member_token = _seed_user(engine, "member-media-filter@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    agent_id, _scene_id, conversation_id, turn_id = _seed_agent_scene_conversation(
        engine,
        world_id,
        worldline_id,
    )
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    admin_background_id = _seed_image_asset(
        engine,
        client.presentation_storage,
        world_id,
        worldline_id,
        role=MediaAssetRole.SCENE_BACKGROUND,
        color=(10, 20, 30, 255),
    )
    hidden_composite_id = _seed_image_asset(
        engine,
        client.presentation_storage,
        world_id,
        worldline_id,
        role=MediaAssetRole.COMPOSITE_IMAGE,
        color=(40, 50, 60, 255),
        visibility=MediaVisibility.HIDDEN,
    )
    private_tts_id = _seed_audio_asset(
        engine,
        client.presentation_storage,
        world_id,
        worldline_id,
        visibility=MediaVisibility.PRIVATE,
    )

    _authenticate(client, owner_token)
    admin_put = client.put(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation",
        json={
            "speaker_agent_id": str(agent_id),
            "background_asset_id": str(admin_background_id),
            "composite_scene_asset_id": str(hidden_composite_id),
            "tts_media_asset_id": str(private_tts_id),
        },
    )
    admin_get = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation",
    )
    _authenticate(client, member_token)
    member_get = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation",
    )

    assert admin_put.status_code == 200
    assert admin_get.status_code == 200
    assert admin_get.json()["background_asset_id"] == str(admin_background_id)
    assert admin_get.json()["composite_scene_asset_id"] == str(hidden_composite_id)
    assert admin_get.json()["tts_media_asset_id"] == str(private_tts_id)
    assert member_get.status_code == 200
    assert member_get.json()["background_asset_id"] is None
    assert member_get.json()["composite_scene_asset_id"] is None
    assert member_get.json()["tts_media_asset_id"] is None

    visible_background_id = _seed_image_asset(
        engine,
        client.presentation_storage,
        world_id,
        worldline_id,
        role=MediaAssetRole.SCENE_BACKGROUND,
        color=(70, 80, 90, 255),
        visibility=MediaVisibility.READER_VISIBLE,
    )
    visible_composite_id = _seed_image_asset(
        engine,
        client.presentation_storage,
        world_id,
        worldline_id,
        role=MediaAssetRole.COMPOSITE_IMAGE,
        color=(100, 110, 120, 255),
        visibility=MediaVisibility.READER_VISIBLE,
    )
    visible_tts_id = _seed_audio_asset(
        engine,
        client.presentation_storage,
        world_id,
        worldline_id,
        visibility=MediaVisibility.READER_VISIBLE,
    )
    _attach_reader_turn_media(engine, world_id, worldline_id, turn_id, visible_background_id)
    _attach_reader_turn_media(engine, world_id, worldline_id, turn_id, visible_composite_id)
    _attach_reader_turn_media(engine, world_id, worldline_id, turn_id, visible_tts_id)

    _authenticate(client, owner_token)
    visible_put = client.put(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation",
        json={
            "speaker_agent_id": str(agent_id),
            "background_asset_id": str(visible_background_id),
            "composite_scene_asset_id": str(visible_composite_id),
            "tts_media_asset_id": str(visible_tts_id),
        },
    )
    _authenticate(client, member_token)
    visible_member_get = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation",
    )

    assert visible_put.status_code == 200
    assert visible_member_get.status_code == 200
    assert visible_member_get.json()["background_asset_id"] == str(visible_background_id)
    assert visible_member_get.json()["composite_scene_asset_id"] == str(visible_composite_id)
    assert visible_member_get.json()["tts_media_asset_id"] == str(visible_tts_id)


def test_conversation_presentation_api_rejects_cross_worldline_asset() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    fork_id = _seed_fork(engine, world_id, worldline_id)
    agent_id, _scene_id, conversation_id, turn_id = _seed_agent_scene_conversation(
        engine,
        world_id,
        worldline_id,
    )
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    fork_asset = _seed_image_asset(
        engine,
        client.presentation_storage,
        world_id,
        fork_id,
        role=MediaAssetRole.SCENE_BACKGROUND,
        color=(0, 0, 0, 255),
    )

    _authenticate(client, owner_token)
    response = client.put(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation",
        json={
            "speaker_agent_id": str(agent_id),
            "background_asset_id": str(fork_asset),
        },
    )

    assert response.status_code == 422
    assert "worldline" in response.json()["detail"]


class _PresentationApiClient(TestClient):
    presentation_storage: LocalMediaObjectStorage


def _client_with_database() -> tuple[_PresentationApiClient, Engine]:
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
    app.dependency_overrides[_presentation_storage] = lambda: storage
    app.state._presentation_storage_tmp = storage_tmp
    client = _PresentationApiClient(app)
    client.presentation_storage = storage
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
        cast(Table, Scene.__table__),
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
        cast(Table, NarrativeArtifact.__table__),
        cast(Table, ModerationAction.__table__),
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
        cast(Table, ConversationTurnPresentation.__table__),
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


def _seed_agent_scene_conversation(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    agent_id = uuid.uuid4()
    scene_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    turn_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Scene(
                id=scene_id,
                world_id=world_id,
                scene_key="classroom",
                name="Classroom",
            )
        )
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
                speaker_kind="agent",
                speaker_agent_id=agent_id,
                input_text="hi",
                output_text="hello",
                status="succeeded",
            )
        )
        session.commit()
    return agent_id, scene_id, conversation_id, turn_id


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


def _seed_visual_bindings(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    agent_id: uuid.UUID,
    scene_id: uuid.UUID,
    sprite_asset_id: uuid.UUID,
    neutral_asset_id: uuid.UUID,
    background_asset_id: uuid.UUID,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    with Session(engine) as session:
        service = VisualAssetService(session)
        sprite_set = service.create_sprite_set(
            SpriteSetCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                style_key="default",
                display_name="Default",
            )
        )
        happy = service.create_sprite_variant(
            SpriteVariantCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                sprite_set_id=sprite_set.id,
                asset_id=sprite_asset_id,
                expression_key="happy",
                priority=10,
            )
        )
        neutral = service.create_sprite_variant(
            SpriteVariantCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                sprite_set_id=sprite_set.id,
                asset_id=neutral_asset_id,
                expression_key="neutral",
                is_default=True,
                priority=20,
            )
        )
        service.create_background(
            SceneBackgroundCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                scene_id=scene_id,
                location_key="classroom",
                asset_id=background_asset_id,
                is_default=True,
            )
        )
        session.commit()
        return sprite_set.id, happy.id, neutral.id


def _seed_voice_profile(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    agent_id: uuid.UUID,
    provider_id: uuid.UUID,
) -> uuid.UUID:
    profile_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            VoiceProfile(
                id=profile_id,
                world_id=world_id,
                worldline_id=worldline_id,
                profile_key="hero",
                display_name="Hero",
                status="active",
                visibility="world_admin",
                owner_kind="world",
                provider_integration_id=provider_id,
                provider_voice_id="voice_123",
                supported_languages_json=[],
                voice_kind="preset",
                consent_status="not_required",
                usage_policy_json={},
                metadata_json={},
            )
        )
        session.add(
            AgentVoiceProfileBinding(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                voice_profile_id=profile_id,
                binding_role="default",
                priority=100,
                is_default=True,
                style_overrides_json={},
            )
        )
        session.commit()
    return profile_id


def _seed_image_asset(
    engine: Engine,
    storage: LocalMediaObjectStorage,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    role: MediaAssetRole,
    color: tuple[int, int, int, int],
    visibility: MediaVisibility = MediaVisibility.WORLD_ADMIN,
) -> uuid.UUID:
    with Session(engine) as session:
        asset_id = uuid.uuid4()
        stored = storage.write_bytes(
            f"worlds/{world_id}/worldlines/{worldline_id}/assets/{asset_id}/original.png",
            _png(color),
            content_type="image/png",
        )
        asset = MediaService(session, storage).create_asset(
            MediaAssetCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind=MediaAssetKind.IMAGE,
                asset_role=role,
                source_kind=MediaSourceKind.MANUAL_UPLOAD,
                status=MediaAssetStatus.AVAILABLE,
                visibility=visibility,
                storage_uri=stored.uri,
                mime_type="image/png",
                file_ext="png",
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
            ),
            actor_ref="test",
        )
        MediaService(session, storage).add_object(
            world_id,
            asset.id,
            MediaObjectCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                object_role=MediaObjectRole.ORIGINAL,
                storage_uri=stored.uri,
                filename="image.png",
                mime_type="image/png",
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
            ),
        )
        session.commit()
        return asset.id


def _seed_audio_asset(
    engine: Engine,
    storage: LocalMediaObjectStorage,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    visibility: MediaVisibility = MediaVisibility.WORLD_ADMIN,
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
                asset_role="transcript_audio",
                source_kind="manual_upload",
                status="available",
                visibility=visibility.value,
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


def _attach_reader_turn_media(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    turn_id: uuid.UUID,
    asset_id: uuid.UUID,
) -> None:
    with Session(engine) as session:
        session.add(
            MediaReference(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                asset_id=asset_id,
                ref_kind=MediaReferenceKind.CONVERSATION_TURN.value,
                ref_id=turn_id,
                ref_role=MediaReferenceRole.OUTPUT.value,
                metadata_json={},
            )
        )
        session.commit()


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _png(color: tuple[int, int, int, int]) -> bytes:
    image = Image.new("RGBA", (2, 2), color)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _wav_bytes() -> bytes:
    return (
        b"RIFF(\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
        b"\x01\x00\x01\x00@\x1f\x00\x00@\x1f\x00\x00"
        b"\x01\x00\x08\x00data\x04\x00\x00\x00\x00\x00\x00\x00"
    )


def _json_text(value: Any) -> str:
    return str(value)
