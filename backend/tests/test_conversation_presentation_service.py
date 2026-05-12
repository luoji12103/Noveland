from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path
from typing import cast

import pytest
from noveland.agents.models import Agent
from noveland.auth.models import User
from noveland.conversations import (
    ConversationPresentationService,
    ConversationTurnPresentationPatch,
    ConversationTurnPresentationUpsert,
)
from noveland.conversations.errors import ConversationValidationError
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
from noveland.narrative.models import NarrativeArtifact
from noveland.providers.models import ProviderCapability, ProviderHealthCheck, ProviderIntegration
from noveland.speech.models import (
    AgentVoiceProfileBinding,
    SpeechStyleMapping,
    SpeechTranscript,
    VoiceProfile,
)
from noveland.visual.contracts import (
    SpriteSetCreate,
    SpriteVariantCreate,
)
from noveland.visual.models import (
    CharacterSpriteSet,
    CharacterSpriteVariant,
    SceneBackgroundProfile,
)
from noveland.visual.service import VisualAssetService
from noveland.worlds.models import Scene, World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from PIL import Image
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_presentation_service_upserts_patches_and_validates_worldline(
    tmp_path: Path,
) -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    fork_id = _seed_fork(engine, graph.world_id, graph.worldline_id)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        sprite_asset = _seed_image_asset(
            session,
            storage,
            graph.world_id,
            graph.worldline_id,
            role=MediaAssetRole.CHARACTER_SPRITE,
        )
        background_asset = _seed_image_asset(
            session,
            storage,
            graph.world_id,
            graph.worldline_id,
            role=MediaAssetRole.SCENE_BACKGROUND,
        )
        fork_asset = _seed_image_asset(
            session,
            storage,
            graph.world_id,
            fork_id,
            role=MediaAssetRole.CHARACTER_SPRITE,
        )
        visual = VisualAssetService(session)
        sprite_set = visual.create_sprite_set(
            SpriteSetCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                agent_id=graph.agent_id,
                style_key="default",
                display_name="Default",
            )
        )
        variant = visual.create_sprite_variant(
            SpriteVariantCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                sprite_set_id=sprite_set.id,
                asset_id=sprite_asset,
                expression_key="happy",
                is_default=True,
            )
        )
        service = ConversationPresentationService(session)
        created = service.put_presentation(
            graph.world_id,
            graph.conversation_id,
            graph.turn_id,
            ConversationTurnPresentationUpsert(
                speaker_agent_id=graph.agent_id,
                emotion_key="Happy",
                emotion_intensity=0.8,
                sprite_set_id=sprite_set.id,
                sprite_variant_id=variant.id,
                background_asset_id=background_asset,
                presentation_json={"safe": {"asset_id": str(sprite_asset)}},
            ),
        )
        patched = service.patch_presentation(
            graph.world_id,
            graph.conversation_id,
            graph.turn_id,
            ConversationTurnPresentationPatch(emotion_key="shy"),
        )

        assert created.emotion_intensity == 0.8
        assert patched.emotion_key == "shy"
        assert patched.sprite_variant_id == variant.id
        assert session.scalars(select(WorldEventModel)).all() == []

        with pytest.raises(ConversationValidationError, match="worldline"):
            service.patch_presentation(
                graph.world_id,
                graph.conversation_id,
                graph.turn_id,
                ConversationTurnPresentationPatch(tts_media_asset_id=fork_asset),
            )

        with pytest.raises(ValueError, match="storage_uri"):
            ConversationTurnPresentationUpsert(
                presentation_json={"nested": {"storage_uri": "local://leak"}}
            )


class _Graph:
    def __init__(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
        scene_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
    ) -> None:
        self.world_id = world_id
        self.worldline_id = worldline_id
        self.agent_id = agent_id
        self.scene_id = scene_id
        self.conversation_id = conversation_id
        self.turn_id = turn_id


def _seed_graph(engine: Engine) -> _Graph:
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
        session.add(
            Scene(
                id=scene_id,
                world_id=world_id,
                scene_key="scene",
                name="Scene",
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
                speaker_kind="agent",
                speaker_agent_id=agent_id,
                input_text="hi",
                output_text="hello",
                status="succeeded",
            )
        )
        session.commit()
        return _Graph(world_id, worldline.id, agent_id, scene_id, conversation_id, turn_id)


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


def _seed_image_asset(
    session: Session,
    storage: LocalMediaObjectStorage,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    role: MediaAssetRole,
) -> uuid.UUID:
    asset_id = uuid.uuid4()
    stored = storage.write_bytes(
        f"worlds/{world_id}/worldlines/{worldline_id}/assets/{asset_id}/original.png",
        _png(),
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
            visibility=MediaVisibility.WORLD_ADMIN,
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
    return asset.id


def _png() -> bytes:
    image = Image.new("RGBA", (2, 2), (255, 0, 0, 255))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


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
        cast(Table, ConversationTurnPresentation.__table__),
    ):
        table.create(engine)
    return engine
