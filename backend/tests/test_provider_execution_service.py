from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

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
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderExecutionRequest,
    ProviderIntegrationCreate,
    ProviderKind,
    ProviderScopeKind,
)
from noveland.providers.models import ProviderCapability, ProviderHealthCheck, ProviderIntegration
from noveland.providers.registry import ProviderRegistryService
from noveland.providers.service import ProviderExecutionService
from noveland.worlds.models import World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_fake_text_execution_writes_invocation_and_snapshot() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)

    with Session(engine) as session:
        provider = _seed_provider(session, world_id, ProviderKind.TEXT_GENERATION)
        result = ProviderExecutionService(session).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=provider,
                input_text="hello",
                request_json={"purpose": "test"},
            )
        )
        session.commit()

    with Session(engine) as session:
        snapshot = session.scalars(
            select(PromptSnapshot).where(PromptSnapshot.invocation_id == result.invocation.id)
        ).one()
        invocation = session.get(ModelInvocation, result.invocation.id)
        assert invocation is not None
        assert invocation.status == "succeeded"
        assert invocation.provider_kind == "local_stub"
        assert result.output_text == "fake text: hello"
        assert snapshot.raw_prompt_text == "hello"
        assert snapshot.raw_response_json == {"text": "fake text: hello"}


def test_fake_image_and_speech_execution_write_media_and_links(tmp_path: Path) -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    event_id = _seed_event(engine, world_id)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        image_provider = _seed_provider(session, world_id, ProviderKind.IMAGE_GENERATION)
        speech_provider = _seed_provider(session, world_id, ProviderKind.TEXT_TO_SPEECH)
        image = ProviderExecutionService(session, storage).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=image_provider,
                input_text="draw a test image",
            )
        )
        speech = ProviderExecutionService(session, storage).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=speech_provider,
                input_text="speak test",
            )
        )
        session.commit()

    with Session(engine) as session:
        image_invocation = session.get(ModelInvocation, image.invocation.id)
        speech_invocation = session.get(ModelInvocation, speech.invocation.id)
        assert image.media_job is not None
        assert image.output_asset is not None
        assert image.output_objects[0].mime_type == "image/png"
        assert speech.output_asset is not None
        assert speech.output_objects[0].mime_type == "audio/wav"
        assert image_invocation is not None
        assert image_invocation.media_job_id == image.media_job.id
        assert image_invocation.media_asset_id == image.output_asset.id
        assert speech_invocation is not None
        assert speech_invocation.media_asset_id == speech.output_asset.id
        asset = session.get(MediaAsset, image.output_asset.id)
        event = session.get(WorldEventModel, event_id)
        assert asset is not None
        assert event is not None
        assert asset.source_invocation_id == image.invocation.id
        assert event.payload == {"kind": "seed"}


def test_fake_stt_execution_returns_transcript_without_media(tmp_path: Path) -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)

    with Session(engine) as session:
        provider = _seed_provider(session, world_id, ProviderKind.SPEECH_TO_TEXT)
        result = ProviderExecutionService(session, LocalMediaObjectStorage(tmp_path)).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=provider,
                request_json={"transcript": "recognized words"},
            )
        )
        session.commit()

    assert result.output_text == "recognized words"
    assert result.media_job is None
    assert result.output_asset is None


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


def _seed_world(engine: Engine) -> tuple[uuid.UUID, uuid.UUID]:
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


def _seed_provider(session: Session, world_id: uuid.UUID, provider_kind: ProviderKind) -> uuid.UUID:
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
    return provider.id


def _seed_event(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        event = WorldEventStore(session).append_event(
            WorldEventAppend(
                world_id=world_id,
                event_name="provider.seed_event",
                payload={"kind": "seed"},
                wall_time=datetime.now(UTC),
                actor_ref="test",
            )
        )
        session.commit()
        return event.id
