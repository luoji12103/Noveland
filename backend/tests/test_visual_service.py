from __future__ import annotations

import uuid
from datetime import UTC, datetime
from io import BytesIO
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
from noveland.narrative.models import NarrativeArtifact
from noveland.providers.models import ProviderCapability, ProviderHealthCheck, ProviderIntegration
from noveland.visual.composition import VisualCompositionService
from noveland.visual.contracts import (
    BackgroundResolveRequest,
    SceneBackgroundCreate,
    SceneComposeRequest,
    SceneLayer,
    SpriteResolveRequest,
    SpriteSetCreate,
    SpriteVariantCreate,
)
from noveland.visual.models import (
    CharacterSpriteSet,
    CharacterSpriteVariant,
    SceneBackgroundProfile,
)
from noveland.visual.resolver import VisualResolver
from noveland.visual.service import VisualAssetService, VisualNotFoundError, VisualValidationError
from noveland.worlds.models import Scene, World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from PIL import Image
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_visual_service_creates_sprite_set_variants_and_resolves_fallbacks(
    tmp_path: Path,
) -> None:
    engine = _engine()
    world_id, worldline_id, agent_id, _scene_id = _seed_world_graph(engine)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        happy_asset = _seed_image_asset(
            session,
            storage,
            world_id,
            worldline_id,
            _png((255, 0, 0, 255), 2, 2),
            role=MediaAssetRole.CHARACTER_SPRITE,
        )
        neutral_asset = _seed_image_asset(
            session,
            storage,
            world_id,
            worldline_id,
            _png((0, 255, 0, 255), 2, 2),
            role=MediaAssetRole.CHARACTER_SPRITE,
        )
        default_asset = _seed_image_asset(
            session,
            storage,
            world_id,
            worldline_id,
            _png((0, 0, 255, 255), 2, 2),
            role=MediaAssetRole.CHARACTER_EXPRESSION,
        )
        service = VisualAssetService(session)
        sprite_set = service.create_sprite_set(
            SpriteSetCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                style_key="Default",
                display_name="Default",
            )
        )
        happy = service.create_sprite_variant(
            SpriteVariantCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                sprite_set_id=sprite_set.id,
                asset_id=happy_asset,
                expression_key="Happy",
                pose_key="Standing",
                outfit_key="School",
                mood_tags=("warm", "Warm"),
                priority=10,
            )
        )
        neutral = service.create_sprite_variant(
            SpriteVariantCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                sprite_set_id=sprite_set.id,
                asset_id=neutral_asset,
                expression_key="neutral",
                pose_key="standing",
                outfit_key="school",
                priority=20,
            )
        )
        default = service.create_sprite_variant(
            SpriteVariantCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                sprite_set_id=sprite_set.id,
                asset_id=default_asset,
                expression_key="sad",
                is_default=True,
                priority=30,
            )
        )
        session.commit()

    with Session(engine) as session:
        resolver = VisualResolver(session)
        exact = resolver.resolve_sprite(
            world_id,
            SpriteResolveRequest(
                worldline_id=worldline_id,
                agent_id=agent_id,
                expression_key="happy",
                pose_key="standing",
                outfit_key="school",
                mood_tags=("warm",),
            ),
        )
        neutral_result = resolver.resolve_sprite(
            world_id,
            SpriteResolveRequest(
                worldline_id=worldline_id,
                agent_id=agent_id,
                expression_key="angry",
                pose_key="standing",
                outfit_key="school",
            ),
        )
        default_result = resolver.resolve_sprite(
            world_id,
            SpriteResolveRequest(
                worldline_id=worldline_id,
                agent_id=agent_id,
                expression_key="angry",
                pose_key="sitting",
            ),
        )

        assert exact.variant.id == happy.id
        assert exact.variant.mood_tags == ("warm",)
        assert exact.fallback_reason is None
        assert "storage_uri" not in exact.asset.model_dump()
        assert neutral_result.variant.id == neutral.id
        assert neutral_result.fallback_reason == "neutral_expression"
        assert default_result.variant.id == default.id
        assert default_result.fallback_reason == "default_variant"


def test_visual_resolver_rejects_missing_default_if_no_fallback(tmp_path: Path) -> None:
    engine = _engine()
    world_id, worldline_id, agent_id, _scene_id = _seed_world_graph(engine)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        asset_id = _seed_image_asset(
            session,
            storage,
            world_id,
            worldline_id,
            _png((255, 0, 0, 255), 2, 2),
            role=MediaAssetRole.CHARACTER_SPRITE,
        )
        sprite_set = VisualAssetService(session).create_sprite_set(
            SpriteSetCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                style_key="default",
                display_name="Default",
            )
        )
        VisualAssetService(session).create_sprite_variant(
            SpriteVariantCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                sprite_set_id=sprite_set.id,
                asset_id=asset_id,
                expression_key="happy",
            )
        )
        session.commit()

    with Session(engine) as session, pytest.raises(VisualValidationError, match="default"):
        VisualResolver(session).resolve_sprite(
            world_id,
            SpriteResolveRequest(
                worldline_id=worldline_id,
                agent_id=agent_id,
                expression_key="angry",
            ),
        )


def test_visual_background_resolves_exact_and_default(tmp_path: Path) -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id, scene_id = _seed_world_graph(engine)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        day_asset = _seed_image_asset(
            session,
            storage,
            world_id,
            worldline_id,
            _png((255, 255, 255, 255), 2, 2),
            role=MediaAssetRole.SCENE_BACKGROUND,
        )
        default_asset = _seed_image_asset(
            session,
            storage,
            world_id,
            worldline_id,
            _png((0, 0, 0, 255), 2, 2),
            role=MediaAssetRole.SCENE_BACKGROUND,
        )
        service = VisualAssetService(session)
        exact_profile = service.create_background(
            SceneBackgroundCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                scene_id=scene_id,
                location_key="Classroom",
                time_of_day="day",
                weather_key="clear",
                asset_id=day_asset,
                priority=10,
            )
        )
        default_profile = service.create_background(
            SceneBackgroundCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                scene_id=scene_id,
                location_key="classroom",
                asset_id=default_asset,
                is_default=True,
                priority=20,
            )
        )
        session.commit()

    with Session(engine) as session:
        resolver = VisualResolver(session)
        exact = resolver.resolve_background(
            world_id,
            BackgroundResolveRequest(
                worldline_id=worldline_id,
                scene_id=scene_id,
                location_key="classroom",
                time_of_day="day",
                weather_key="clear",
            ),
        )
        fallback = resolver.resolve_background(
            world_id,
            BackgroundResolveRequest(
                worldline_id=worldline_id,
                scene_id=scene_id,
                location_key="classroom",
                time_of_day="night",
                weather_key="rain",
            ),
        )

        assert exact.background.id == exact_profile.id
        assert exact.fallback_reason is None
        assert fallback.background.id == default_profile.id
        assert fallback.fallback_reason == "default_background"
        assert "storage_uri" not in fallback.asset.model_dump()


def test_visual_service_rejects_cross_world_and_cross_worldline_assets(tmp_path: Path) -> None:
    engine = _engine()
    world_id, worldline_id, agent_id, _scene_id = _seed_world_graph(engine)
    other_world_id, other_worldline_id, _other_agent_id, _other_scene_id = _seed_world_graph(engine)
    fork_id = _seed_fork(engine, world_id, worldline_id)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        sprite_set = VisualAssetService(session).create_sprite_set(
            SpriteSetCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                style_key="default",
                display_name="Default",
            )
        )
        other_world_asset = _seed_image_asset(
            session,
            storage,
            other_world_id,
            other_worldline_id,
            _png((255, 0, 0, 255), 2, 2),
            role=MediaAssetRole.CHARACTER_SPRITE,
        )
        fork_asset = _seed_image_asset(
            session,
            storage,
            world_id,
            fork_id,
            _png((0, 255, 0, 255), 2, 2),
            role=MediaAssetRole.CHARACTER_SPRITE,
        )

        with pytest.raises(VisualValidationError, match="worldline"):
            VisualAssetService(session).create_sprite_variant(
                SpriteVariantCreate(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    sprite_set_id=sprite_set.id,
                    asset_id=other_world_asset,
                    expression_key="happy",
                )
            )
        with pytest.raises(VisualValidationError, match="worldline"):
            VisualAssetService(session).create_sprite_variant(
                SpriteVariantCreate(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    sprite_set_id=sprite_set.id,
                    asset_id=fork_asset,
                    expression_key="happy",
                )
            )


def test_visual_resolver_suppresses_hidden_assets_unless_internal(tmp_path: Path) -> None:
    engine = _engine()
    world_id, worldline_id, agent_id, _scene_id = _seed_world_graph(engine)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        hidden_asset = _seed_image_asset(
            session,
            storage,
            world_id,
            worldline_id,
            _png((255, 0, 0, 255), 2, 2),
            role=MediaAssetRole.CHARACTER_SPRITE,
            visibility=MediaVisibility.HIDDEN,
        )
        sprite_set = VisualAssetService(session).create_sprite_set(
            SpriteSetCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                style_key="default",
                display_name="Default",
            )
        )
        VisualAssetService(session).create_sprite_variant(
            SpriteVariantCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                sprite_set_id=sprite_set.id,
                asset_id=hidden_asset,
                expression_key="neutral",
                is_default=True,
            )
        )
        session.commit()

    with Session(engine) as session:
        resolver = VisualResolver(session)
        with pytest.raises(VisualNotFoundError):
            resolver.resolve_sprite(
                world_id,
                SpriteResolveRequest(
                    worldline_id=worldline_id,
                    agent_id=agent_id,
                    expression_key="neutral",
                ),
            )
        internal = resolver.resolve_sprite(
            world_id,
            SpriteResolveRequest(
                worldline_id=worldline_id,
                agent_id=agent_id,
                expression_key="neutral",
                include_restricted=True,
            ),
        )
        assert internal.asset.id == hidden_asset


def test_visual_compose_scene_reuses_image_service_and_does_not_write_events(
    tmp_path: Path,
) -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id, _scene_id = _seed_world_graph(engine)
    storage = LocalMediaObjectStorage(tmp_path)
    event_id = _seed_event(engine, world_id, worldline_id)

    with Session(engine) as session:
        background_id = _seed_image_asset(
            session,
            storage,
            world_id,
            worldline_id,
            _png((0, 0, 255, 255), 2, 2),
            role=MediaAssetRole.SCENE_BACKGROUND,
        )
        red_id = _seed_image_asset(
            session,
            storage,
            world_id,
            worldline_id,
            _png((255, 0, 0, 255), 2, 2),
            role=MediaAssetRole.CHARACTER_SPRITE,
        )
        green_id = _seed_image_asset(
            session,
            storage,
            world_id,
            worldline_id,
            _png((0, 255, 0, 255), 1, 1),
            role=MediaAssetRole.CHARACTER_SPRITE,
        )
        result = VisualCompositionService(session, storage).compose_scene(
            world_id,
            SceneComposeRequest(
                worldline_id=worldline_id,
                background_asset_id=background_id,
                layers=(
                    SceneLayer(asset_id=red_id, x=0, y=0, z_index=1),
                    SceneLayer(asset_id=green_id, x=0, y=0, z_index=2),
                ),
            ),
            actor_ref="test",
        )
        session.commit()

    with Session(engine) as session:
        assert session.scalars(select(ModelInvocation)).all() == []
        assert result.output_asset.source_kind == MediaSourceKind.COMPOSED
        assert "storage_uri" not in result.output_asset.model_dump()
        assert "storage_uri" not in result.output_objects[0].model_dump()
        inputs = session.scalars(select(MediaAssetInput)).all()
        assert {item.input_asset_id for item in inputs} == {background_id, red_id, green_id}
        objects = session.scalars(
            select(MediaObject).where(MediaObject.asset_id == result.output_asset.id)
        ).all()
        assert len(objects) == 1
        _, data = MediaService(session, storage).read_object_bytes(world_id, objects[0].id)
        with Image.open(BytesIO(data)) as image:
            pixels = image.convert("RGBA")
            assert pixels.getpixel((0, 0)) == (0, 255, 0, 255)
            assert pixels.getpixel((1, 1)) == (255, 0, 0, 255)
        event = session.get(WorldEventModel, event_id)
        assert event is not None
        assert event.payload == {"kind": "seed"}


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
        cast(Table, Scene.__table__),
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
        cast(Table, CharacterSpriteSet.__table__),
        cast(Table, CharacterSpriteVariant.__table__),
        cast(Table, SceneBackgroundProfile.__table__),
    ):
        table.create(engine)
    return engine


def _seed_world_graph(engine: Engine) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    scene_id = uuid.uuid4()
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
                scene_key=f"scene-{scene_id.hex[:8]}",
                name="Scene",
            )
        )
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key=f"agent-{agent_id.hex[:8]}",
                display_name="Agent",
                kind="role_agent",
            )
        )
        session.commit()
        return world_id, worldline.id, agent_id, scene_id


def _seed_image_asset(
    session: Session,
    storage: LocalMediaObjectStorage,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    data: bytes,
    *,
    role: MediaAssetRole,
    visibility: MediaVisibility = MediaVisibility.WORLD_ADMIN,
) -> uuid.UUID:
    asset_id = uuid.uuid4()
    stored = storage.write_bytes(
        f"worlds/{world_id}/worldlines/{worldline_id}/assets/{asset_id}/original.png",
        data,
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
    return asset.id


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


def _seed_event(engine: Engine, world_id: uuid.UUID, worldline_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        event = WorldEventStore(session).append_event(
            WorldEventAppend(
                world_id=world_id,
                worldline_id=worldline_id,
                event_name="visual.seed_event",
                payload={"kind": "seed"},
                wall_time=datetime.now(UTC),
                actor_ref="test",
            )
        )
        session.commit()
        return event.id


def _png(color: tuple[int, int, int, int], width: int, height: int) -> bytes:
    image = Image.new("RGBA", (width, height), color)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
