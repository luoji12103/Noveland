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
from noveland.media.errors import MediaValidationError
from noveland.media.image_contracts import (
    ImageComposeRequest,
    ImageGenerateRequest,
    ImageLayer,
    TransparentBackgroundPreference,
)
from noveland.media.image_service import ImageService
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
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderCapabilityCreate,
    ProviderIntegrationCreate,
    ProviderKind,
    ProviderScopeKind,
)
from noveland.providers.models import ProviderCapability, ProviderHealthCheck, ProviderIntegration
from noveland.providers.registry import ProviderRegistryService
from noveland.providers.service import ProviderExecutionError
from noveland.worlds.models import World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from PIL import Image
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_image_generate_fake_provider_writes_job_invocation_asset_and_object(
    tmp_path: Path,
) -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world_graph(engine)
    event_id = _seed_event(engine, world_id)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        provider_id = _seed_provider(
            session,
            world_id,
            ProviderKind.IMAGE_GENERATION,
            capabilities=("supports_image_generation",),
        )
        result = ImageService(session, storage).generate_image(
            world_id,
            ImageGenerateRequest(
                worldline_id=worldline_id,
                provider_id=provider_id,
                prompt="draw a tree",
                asset_role=MediaAssetRole.EVENT_CG,
            ),
            actor_ref="user:test",
        )
        session.commit()

    with Session(engine) as session:
        invocation = session.get(ModelInvocation, result.model_invocation_id)
        asset = session.get(MediaAsset, result.output_asset.id)
        job = session.get(MediaJob, result.media_job.id)
        event = session.get(WorldEventModel, event_id)
        assert invocation is not None
        assert invocation.media_job_id == result.media_job.id
        assert invocation.media_asset_id == result.output_asset.id
        assert job is not None
        assert job.status == "succeeded"
        assert asset is not None
        assert asset.asset_role == "event_cg"
        assert asset.source_invocation_id == invocation.id
        assert result.output_objects[0].mime_type == "image/png"
        assert event is not None
        assert event.payload == {"kind": "seed"}


def test_image_generate_rejects_required_transparency_when_provider_lacks_capability(
    tmp_path: Path,
) -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world_graph(engine)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        provider_id = _seed_provider(
            session,
            world_id,
            ProviderKind.IMAGE_GENERATION,
            capabilities=("supports_image_generation",),
        )
        with pytest.raises(MediaValidationError, match="transparent background"):
            ImageService(session, storage).generate_image(
                world_id,
                ImageGenerateRequest(
                    worldline_id=worldline_id,
                    provider_id=provider_id,
                    prompt="transparent sprite",
                    transparent_background=TransparentBackgroundPreference.REQUIRE,
                ),
                actor_ref="user:test",
            )


def test_image_compose_writes_composite_asset_without_invocation(tmp_path: Path) -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world_graph(engine)
    storage = LocalMediaObjectStorage(tmp_path)

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
            role=MediaAssetRole.REFERENCE_IMAGE,
        )
        result = ImageService(session, storage).compose_image(
            world_id,
            ImageComposeRequest(
                worldline_id=worldline_id,
                background_asset_id=background_id,
                layers=(
                    ImageLayer(asset_id=red_id, x=0, y=0, z_index=1),
                    ImageLayer(asset_id=green_id, x=0, y=0, z_index=2),
                ),
            ),
            actor_ref="user:test",
        )
        session.commit()

    with Session(engine) as session:
        assert session.scalars(select(ModelInvocation)).all() == []
        job = session.get(MediaJob, result.media_job.id)
        assert job is not None
        assert job.status == "succeeded"
        assert result.model_invocation_id is None
        assert result.output_asset.source_kind == MediaSourceKind.COMPOSED
        _, data = MediaService(session, storage).read_object_bytes(
            world_id,
            result.output_objects[0].id,
        )
        with Image.open(BytesIO(data)) as image:
            pixels = image.convert("RGBA")
            assert pixels.getpixel((0, 0)) == (0, 255, 0, 255)
            assert pixels.getpixel((1, 1)) == (255, 0, 0, 255)
        lineage = session.scalars(select(MediaAssetInput)).all()
        assert {item.input_asset_id for item in lineage} == {background_id, red_id, green_id}


def test_image_generate_rejects_reference_from_other_worldline(tmp_path: Path) -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world_graph(engine)
    storage = LocalMediaObjectStorage(tmp_path)
    fork_id = _seed_fork(engine, world_id, worldline_id)

    with Session(engine) as session:
        provider_id = _seed_provider(
            session,
            world_id,
            ProviderKind.IMAGE_GENERATION,
            capabilities=("supports_image_generation",),
        )
        reference_id = _seed_image_asset(
            session,
            storage,
            world_id,
            fork_id,
            _png((255, 0, 0, 255), 1, 1),
            role=MediaAssetRole.REFERENCE_IMAGE,
        )
        with pytest.raises(MediaValidationError, match="worldline"):
            ImageService(session, storage).generate_image(
                world_id,
                ImageGenerateRequest(
                    worldline_id=worldline_id,
                    provider_id=provider_id,
                    prompt="use ref",
                    reference_asset_ids=(reference_id,),
                ),
                actor_ref="user:test",
            )


def test_image_generate_blocks_disabled_provider_before_media_success(
    tmp_path: Path,
) -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world_graph(engine)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        provider_id = _seed_provider(
            session,
            world_id,
            ProviderKind.IMAGE_GENERATION,
            capabilities=("supports_image_generation",),
        )
        provider = session.get(ProviderIntegration, provider_id)
        assert provider is not None
        provider.status = "disabled"
        with pytest.raises(ProviderExecutionError, match="disabled"):
            ImageService(session, storage).generate_image(
                world_id,
                ImageGenerateRequest(
                    worldline_id=worldline_id,
                    provider_id=provider_id,
                    prompt="blocked image",
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
    ):
        table.create(engine)
    return engine


def _seed_world_graph(engine: Engine) -> tuple[uuid.UUID, uuid.UUID]:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
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
        session.commit()
        return world_id, worldline.id


def _seed_provider(
    session: Session,
    world_id: uuid.UUID,
    provider_kind: ProviderKind,
    *,
    capabilities: tuple[str, ...],
) -> uuid.UUID:
    provider = ProviderRegistryService(session).create_provider(
        ProviderIntegrationCreate(
            world_id=world_id,
            scope_kind=ProviderScopeKind.WORLD,
            provider_kind=provider_kind,
            adapter_kind=ProviderAdapterKind.FAKE,
            provider_key=f"fake-{provider_kind.value}",
            display_name=f"Fake {provider_kind.value}",
            capabilities=tuple(
                ProviderCapabilityCreate(capability_key=capability, capability_json={"value": True})
                for capability in capabilities
            ),
        )
    )
    return provider.id


def _seed_image_asset(
    session: Session,
    storage: LocalMediaObjectStorage,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    data: bytes,
    *,
    role: MediaAssetRole,
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
            visibility=MediaVisibility.WORLD_ADMIN,
            storage_uri=stored.uri,
            mime_type="image/png",
            file_ext="png",
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
            filename="image.png",
            mime_type="image/png",
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
                event_name="image.seed_event",
                payload={"kind": "seed"},
                wall_time=datetime.now(UTC),
                actor_ref="test",
            )
        )
        session.commit()
        return event.id


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


def _png(color: tuple[int, int, int, int], width: int, height: int) -> bytes:
    image = Image.new("RGBA", (width, height), color)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
