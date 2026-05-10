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
from noveland.media.contracts import (
    MediaAssetCreate,
    MediaAssetInputCreate,
    MediaAssetKind,
    MediaAssetRole,
    MediaAssetStatus,
    MediaContextCreate,
    MediaJobCreate,
    MediaJobKind,
    MediaSourceKind,
    MediaVisibility,
)
from noveland.media.errors import MediaValidationError
from noveland.media.models import MediaAsset, MediaAssetContext, MediaAssetInput, MediaJob
from noveland.media.service import MediaJobService, MediaService
from noveland.media.storage import LocalMediaObjectStorage
from noveland.narrative.models import NarrativeArtifact
from noveland.worlds.models import World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_media_service_registers_assets_contexts_jobs_and_lineage(tmp_path: Path) -> None:
    engine = _engine()
    world_id, primary_id, _fork_id, agent_id, conversation_id, turn_id = _seed_world_graph(engine)
    event_id = _seed_event(engine, world_id)
    storage = LocalMediaObjectStorage(tmp_path)
    stored = storage.write_bytes(
        f"worlds/{world_id}/worldlines/{primary_id}/assets/original.png",
        b"image-bytes",
        content_type="image/png",
    )

    with Session(engine) as session:
        service = MediaService(session, storage)
        available = service.create_asset(
            MediaAssetCreate(
                world_id=world_id,
                worldline_id=primary_id,
                asset_kind=MediaAssetKind.IMAGE,
                asset_role=MediaAssetRole.ORIGINAL_IMAGE,
                source_kind=MediaSourceKind.MANUAL_UPLOAD,
                status=MediaAssetStatus.AVAILABLE,
                visibility=MediaVisibility.WORLD_MEMBER,
                storage_uri=stored.uri,
                mime_type="image/png",
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
                metadata={"source": "test"},
            ),
            actor_ref="user:test",
        )
        derived = service.create_asset(
            MediaAssetCreate(
                world_id=world_id,
                worldline_id=primary_id,
                asset_kind=MediaAssetKind.IMAGE,
                asset_role=MediaAssetRole.COMPOSITE_IMAGE,
                source_kind=MediaSourceKind.COMPOSED,
                visibility=MediaVisibility.PRIVATE,
            ),
            actor_ref="user:test",
        )
        context = service.attach_context(
            world_id,
            available.id,
            MediaContextCreate(
                world_id=world_id,
                worldline_id=primary_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                agent_id=agent_id,
                world_event_id=event_id,
            ),
        )
        lineage = service.add_input(
            world_id,
            derived.id,
            MediaAssetInputCreate(
                world_id=world_id,
                worldline_id=primary_id,
                input_asset_id=available.id,
            ),
        )
        job = MediaJobService(session).create_job(
            MediaJobCreate(
                world_id=world_id,
                worldline_id=primary_id,
                job_kind=MediaJobKind.IMAGE_GENERATION,
                request_json={"prompt": "not executed"},
            ),
            actor_ref="user:test",
        )
        session.commit()

    with Session(engine) as session:
        assert available.status == MediaAssetStatus.AVAILABLE
        assert context.turn_id == turn_id
        assert lineage.input_asset_id == available.id
        assert job.status == "queued"
        assert MediaService(session).references(world_id, available.id).input_count == 1
        assert (
            MediaService(session).lineage(world_id, derived.id).inputs[0].input_asset_id
            == available.id
        )
        assert session.scalars(select(WorldEventModel)).all()[0].payload == {"kind": "seed"}


def test_media_service_rejects_cross_worldline_and_narrative_artifact_contexts() -> None:
    engine = _engine()
    world_id, primary_id, fork_id, _agent_id, conversation_id, _turn_id = _seed_world_graph(engine)
    artifact_id = _seed_artifact(engine, world_id)

    with Session(engine) as session:
        service = MediaService(session)
        asset = service.create_asset(
            MediaAssetCreate(
                world_id=world_id,
                worldline_id=primary_id,
                asset_kind=MediaAssetKind.IMAGE,
                asset_role=MediaAssetRole.REFERENCE_IMAGE,
                source_kind=MediaSourceKind.IMPORTED_ORIGINAL,
            ),
            actor_ref="user:test",
        )

        with pytest.raises(MediaValidationError, match="asset and context worldline"):
            service.attach_context(
                world_id,
                asset.id,
                MediaContextCreate(
                    world_id=world_id,
                    worldline_id=fork_id,
                    conversation_id=conversation_id,
                ),
            )
        with pytest.raises(MediaValidationError, match="narrative artifact media contexts"):
            service.attach_context(
                world_id,
                asset.id,
                MediaContextCreate(
                    world_id=world_id,
                    worldline_id=primary_id,
                    narrative_artifact_id=artifact_id,
                ),
            )


def test_available_asset_requires_verified_storage(tmp_path: Path) -> None:
    engine = _engine()
    world_id, primary_id, _fork_id, _agent_id, _conversation_id, _turn_id = _seed_world_graph(
        engine
    )
    storage = LocalMediaObjectStorage(tmp_path)
    uri = storage.uri_for_key(f"worlds/{world_id}/worldlines/{primary_id}/assets/missing.png")

    with Session(engine) as session:
        with pytest.raises(MediaValidationError, match="does not exist"):
            MediaService(session, storage).create_asset(
                MediaAssetCreate(
                    world_id=world_id,
                    worldline_id=primary_id,
                    asset_kind=MediaAssetKind.IMAGE,
                    asset_role=MediaAssetRole.ORIGINAL_IMAGE,
                    source_kind=MediaSourceKind.MANUAL_UPLOAD,
                    status=MediaAssetStatus.AVAILABLE,
                    storage_uri=uri,
                    mime_type="image/png",
                    size_bytes=10,
                    checksum_sha256="0" * 64,
                ),
                actor_ref="user:test",
            )


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
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, MediaJob.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, NarrativeArtifact.__table__),
        cast(Table, MediaAssetContext.__table__),
        cast(Table, MediaAssetInput.__table__),
    ):
        table.create(engine)


def _seed_world_graph(
    engine: Engine,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    turn_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(User(id=user_id, email=f"{user_id}@example.test", display_name="Test"))
        session.add(
            World(
                id=world_id, owner_user_id=user_id, slug=f"world-{world_id.hex[:8]}", name="World"
            )
        )
        session.flush()
        primary = ensure_primary_worldline(session, world_id)
        fork = Worldline(
            world_id=world_id,
            worldline_key=f"fork-{uuid.uuid4().hex[:8]}",
            name="Fork",
            parent_worldline_id=primary.id,
            status="active",
            created_by_actor_ref="test",
            metadata_json={},
        )
        session.add(fork)
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key="agent",
                display_name="Agent",
                kind="role_agent",
            ),
        )
        session.add(
            ConversationSession(
                id=conversation_id,
                world_id=world_id,
                worldline_id=primary.id,
                session_key="session-1",
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
            ),
        )
        session.add(
            ConversationTurn(
                id=turn_id,
                session_id=conversation_id,
                turn_index=0,
                speaker_kind="operator",
                speaker_agent_id=None,
                input_text="hi",
                output_text="hello",
                status="succeeded",
            ),
        )
        session.commit()
        return world_id, primary.id, fork.id, agent_id, conversation_id, turn_id


def _seed_event(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        event = WorldEventStore(session).append_event(
            WorldEventAppend(
                world_id=world_id,
                event_name="media.seed_event",
                payload={"kind": "seed"},
                wall_time=datetime.now(UTC),
                actor_ref="test",
            ),
        )
        session.commit()
        return event.id


def _seed_artifact(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    artifact_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            NarrativeArtifact(
                id=artifact_id,
                world_id=world_id,
                title="Artifact",
                content="Text",
                artifact_kind="agent_note",
                artifact_metadata={},
            ),
        )
        session.commit()
    return artifact_id
