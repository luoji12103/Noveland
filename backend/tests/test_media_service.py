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
from noveland.invocations.contracts import (
    InvocationActorKind,
    InvocationKind,
    InvocationProviderKind,
    InvocationRecordCreate,
    InvocationStatus,
)
from noveland.invocations.models import (
    AgentRuntimeRunModelInvocation,
    ModelInvocation,
    ModelInvocationTag,
    PromptSnapshot,
    PromptTemplate,
)
from noveland.invocations.service import InvocationLedgerService
from noveland.media.contracts import (
    ConversationTurnMediaAttachmentCreate,
    MediaAssetCreate,
    MediaAssetInputCreate,
    MediaAssetKind,
    MediaAssetRole,
    MediaAssetStatus,
    MediaAssetUploadRequest,
    MediaContextCreate,
    MediaJobCreate,
    MediaJobKind,
    MediaJobStatus,
    MediaJobUpdate,
    MediaObjectCreate,
    MediaObjectRole,
    MediaReferenceCreate,
    MediaReferenceKind,
    MediaReferenceListFilters,
    MediaReferenceRole,
    MediaSourceKind,
    MediaVisibility,
)
from noveland.media.errors import MediaConflictError, MediaStorageError, MediaValidationError
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
from noveland.media.service import MediaJobService, MediaReferenceService, MediaService
from noveland.media.storage import LocalMediaObjectStorage
from noveland.memory.models import MemoryBackendProfile, MemoryWriteJob
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


def test_media_service_upload_adds_object_and_downloads_bytes(tmp_path: Path) -> None:
    engine = _engine()
    world_id, primary_id, _fork_id, _agent_id, _conversation_id, _turn_id = _seed_world_graph(
        engine
    )
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        upload = MediaService(session, storage).upload_asset(
            MediaAssetUploadRequest(
                world_id=world_id,
                worldline_id=primary_id,
                asset_kind=MediaAssetKind.IMAGE,
                asset_role=MediaAssetRole.REFERENCE_IMAGE,
                visibility=MediaVisibility.WORLD_ADMIN,
                title="Reference",
                metadata={"kind": "upload"},
            ),
            data=b"image-bytes",
            filename="../unsafe.png",
            mime_type="image/png",
            actor_ref="user:test",
        )
        session.commit()

    with Session(engine) as session:
        service = MediaService(session, storage)
        objects = service.list_objects(world_id, upload.asset.id)
        media_object, data = service.read_object_bytes(world_id, upload.object.id)

    assert upload.asset.status == MediaAssetStatus.AVAILABLE
    assert upload.asset.storage_uri == upload.object.storage_uri
    assert upload.object.size_bytes == len(b"image-bytes")
    assert upload.object.checksum_sha256 == upload.asset.checksum_sha256
    assert objects[0].id == upload.object.id
    assert media_object.mime_type == "image/png"
    assert data == b"image-bytes"
    assert ".." not in upload.object.storage_uri


def test_media_service_adds_object_variant_and_rejects_path_traversal(tmp_path: Path) -> None:
    engine = _engine()
    world_id, primary_id, _fork_id, _agent_id, _conversation_id, _turn_id = _seed_world_graph(
        engine
    )
    storage = LocalMediaObjectStorage(tmp_path)
    stored = storage.write_bytes(
        f"worlds/{world_id}/worldlines/{primary_id}/assets/asset/preview.png",
        b"preview",
        content_type="image/png",
    )

    with pytest.raises(MediaStorageError, match="safe relative path"):
        storage.write_bytes("../escape.png", b"bad", content_type="image/png")

    with Session(engine) as session:
        service = MediaService(session, storage)
        asset = service.create_asset(
            MediaAssetCreate(
                world_id=world_id,
                worldline_id=primary_id,
                asset_kind=MediaAssetKind.IMAGE,
                asset_role=MediaAssetRole.REFERENCE_IMAGE,
                source_kind=MediaSourceKind.MANUAL_UPLOAD,
                visibility=MediaVisibility.WORLD_ADMIN,
            ),
            actor_ref="user:test",
        )
        variant = service.add_object(
            world_id,
            asset.id,
            MediaObjectCreate(
                world_id=world_id,
                worldline_id=primary_id,
                object_role=MediaObjectRole.PREVIEW,
                storage_uri=stored.uri,
                filename="preview.png",
                mime_type="image/png",
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
                metadata={"variant": "preview"},
            ),
        )
        session.commit()

    with Session(engine) as session:
        objects = MediaService(session, storage).list_objects(world_id, asset.id)

    assert variant.object_role == MediaObjectRole.PREVIEW
    assert [item.id for item in objects] == [variant.id]


def test_media_reference_service_creates_refs_and_rejects_cross_worldline() -> None:
    engine = _engine()
    world_id, primary_id, fork_id, _agent_id, conversation_id, turn_id = _seed_world_graph(engine)
    event_id = _seed_event(engine, world_id)
    artifact_id = _seed_artifact(engine, world_id, worldline_id=primary_id)

    with Session(engine) as session:
        asset = MediaService(session).create_asset(
            MediaAssetCreate(
                world_id=world_id,
                worldline_id=primary_id,
                asset_kind=MediaAssetKind.IMAGE,
                asset_role=MediaAssetRole.REFERENCE_IMAGE,
                source_kind=MediaSourceKind.MANUAL_UPLOAD,
            ),
            actor_ref="user:test",
        )
        reference_service = MediaReferenceService(session)
        turn_ref = reference_service.create_reference(
            MediaReferenceCreate(
                world_id=world_id,
                worldline_id=primary_id,
                asset_id=asset.id,
                ref_kind=MediaReferenceKind.CONVERSATION_TURN,
                ref_id=turn_id,
                ref_role=MediaReferenceRole.ATTACHMENT,
            )
        )
        event_ref = reference_service.create_reference(
            MediaReferenceCreate(
                world_id=world_id,
                worldline_id=primary_id,
                asset_id=asset.id,
                ref_kind=MediaReferenceKind.WORLD_EVENT,
                ref_id=event_id,
                ref_role=MediaReferenceRole.EVIDENCE,
            )
        )
        artifact_ref = reference_service.create_reference(
            MediaReferenceCreate(
                world_id=world_id,
                worldline_id=primary_id,
                asset_id=asset.id,
                ref_kind=MediaReferenceKind.NARRATIVE_ARTIFACT,
                ref_id=artifact_id,
                ref_role=MediaReferenceRole.PREVIEW,
            )
        )
        listed = reference_service.list_references(
            world_id,
            MediaReferenceListFilters(
                worldline_id=primary_id,
                ref_kind=MediaReferenceKind.WORLD_EVENT,
            ),
        )
        with pytest.raises(MediaValidationError, match="asset must belong"):
            reference_service.create_reference(
                MediaReferenceCreate(
                    world_id=world_id,
                    worldline_id=fork_id,
                    asset_id=asset.id,
                    ref_kind=MediaReferenceKind.CONVERSATION_SESSION,
                    ref_id=conversation_id,
                )
            )
        session.commit()

    assert turn_ref.ref_id == turn_id
    assert event_ref.ref_role == MediaReferenceRole.EVIDENCE
    assert artifact_ref.ref_kind == MediaReferenceKind.NARRATIVE_ARTIFACT
    assert [item.id for item in listed] == [event_ref.id]


def test_turn_media_reads_new_references_and_legacy_contexts() -> None:
    engine = _engine()
    world_id, primary_id, _fork_id, _agent_id, conversation_id, turn_id = _seed_world_graph(engine)

    with Session(engine) as session:
        service = MediaService(session)
        new_asset = service.create_asset(
            MediaAssetCreate(
                world_id=world_id,
                worldline_id=primary_id,
                asset_kind=MediaAssetKind.IMAGE,
                asset_role=MediaAssetRole.REFERENCE_IMAGE,
                source_kind=MediaSourceKind.MANUAL_UPLOAD,
            ),
            actor_ref="user:test",
        )
        legacy_asset = service.create_asset(
            MediaAssetCreate(
                world_id=world_id,
                worldline_id=primary_id,
                asset_kind=MediaAssetKind.IMAGE,
                asset_role=MediaAssetRole.ORIGINAL_IMAGE,
                source_kind=MediaSourceKind.MANUAL_UPLOAD,
            ),
            actor_ref="user:test",
        )
        service.attach_context(
            world_id,
            legacy_asset.id,
            MediaContextCreate(
                world_id=world_id,
                worldline_id=primary_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
            ),
        )
        reference_service = MediaReferenceService(session)
        reference_service.create_turn_media(
            world_id,
            conversation_id,
            turn_id,
            ConversationTurnMediaAttachmentCreate(
                worldline_id=primary_id,
                asset_id=new_asset.id,
                attachment_role=MediaReferenceRole.ATTACHMENT,
            ),
        )
        records = reference_service.list_turn_media(world_id, conversation_id, turn_id)
        session.commit()

    assert {record.asset.id for record in records} == {new_asset.id, legacy_asset.id}
    assert sum(record.reference is not None for record in records) == 1
    assert sum(record.legacy_context is not None for record in records) == 1


def test_media_job_update_cancel_and_terminal_cancel_rejection() -> None:
    engine = _engine()
    world_id, primary_id, _fork_id, _agent_id, _conversation_id, _turn_id = _seed_world_graph(
        engine
    )

    with Session(engine) as session:
        service = MediaJobService(session)
        job = service.create_job(
            MediaJobCreate(
                world_id=world_id,
                worldline_id=primary_id,
                job_kind=MediaJobKind.THUMBNAIL,
                provider_config_json={"preset": "small"},
                request_json={"asset": "pending"},
            ),
            actor_ref="user:test",
        )
        updated = service.update_job(
            world_id,
            job.id,
            MediaJobUpdate(
                status=MediaJobStatus.RUNNING,
                priority=10,
                result_json={"started": True},
            ),
        )
        cancelled = service.cancel_job(world_id, job.id)
        with pytest.raises(MediaConflictError, match="queued or running"):
            service.cancel_job(world_id, job.id)
        session.commit()

    assert updated.status == MediaJobStatus.RUNNING
    assert updated.priority == 10
    assert cancelled.status == MediaJobStatus.CANCELLED


def test_media_source_invocation_and_memory_reference_validation() -> None:
    engine = _engine()
    world_id, primary_id, fork_id, agent_id, _conversation_id, _turn_id = _seed_world_graph(engine)
    invocation_id = _seed_invocation(engine, world_id, primary_id)
    memory_job_id = _seed_memory_write_job(engine, world_id, primary_id, agent_id)

    with Session(engine) as session:
        service = MediaService(session)
        asset = service.create_asset(
            MediaAssetCreate(
                world_id=world_id,
                worldline_id=primary_id,
                asset_kind=MediaAssetKind.IMAGE,
                asset_role=MediaAssetRole.REFERENCE_IMAGE,
                source_kind=MediaSourceKind.PROVIDER_GENERATED,
                source_invocation_id=invocation_id,
            ),
            actor_ref="user:test",
        )
        job = MediaJobService(session).create_job(
            MediaJobCreate(
                world_id=world_id,
                worldline_id=primary_id,
                job_kind=MediaJobKind.IMAGE_GENERATION,
                source_invocation_id=invocation_id,
            ),
            actor_ref="user:test",
        )
        memory_ref = MediaReferenceService(session).create_reference(
            MediaReferenceCreate(
                world_id=world_id,
                worldline_id=primary_id,
                asset_id=asset.id,
                ref_kind=MediaReferenceKind.MEMORY_WRITE_JOB,
                ref_id=memory_job_id,
            )
        )
        with pytest.raises(MediaValidationError, match="source invocation"):
            service.create_asset(
                MediaAssetCreate(
                    world_id=world_id,
                    worldline_id=fork_id,
                    asset_kind=MediaAssetKind.IMAGE,
                    asset_role=MediaAssetRole.REFERENCE_IMAGE,
                    source_kind=MediaSourceKind.PROVIDER_GENERATED,
                    source_invocation_id=invocation_id,
                ),
                actor_ref="user:test",
            )
        session.commit()

    assert asset.source_invocation_id == invocation_id
    assert job.source_invocation_id == invocation_id
    assert memory_ref.ref_id == memory_job_id


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
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, MemoryWriteJob.__table__),
        cast(Table, ModelInvocation.__table__),
        cast(Table, PromptTemplate.__table__),
        cast(Table, PromptSnapshot.__table__),
        cast(Table, AgentRuntimeRunModelInvocation.__table__),
        cast(Table, ModelInvocationTag.__table__),
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


def _seed_artifact(
    engine: Engine,
    world_id: uuid.UUID,
    *,
    worldline_id: uuid.UUID | None = None,
) -> uuid.UUID:
    artifact_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            NarrativeArtifact(
                id=artifact_id,
                world_id=world_id,
                title="Artifact",
                content="Text",
                artifact_kind="agent_note",
                artifact_metadata=(
                    {} if worldline_id is None else {"worldline_id": str(worldline_id)}
                ),
            ),
        )
        session.commit()
    return artifact_id


def _seed_invocation(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> uuid.UUID:
    with Session(engine) as session:
        invocation = InvocationLedgerService(session).record(
            InvocationRecordCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                invocation_kind=InvocationKind.IMAGE_GENERATION,
                actor_kind=InvocationActorKind.SERVICE,
                provider_kind=InvocationProviderKind.LOCAL_STUB,
                status=InvocationStatus.SUCCEEDED,
                input_text="input",
                output_text="output",
            )
        )
        session.commit()
        return invocation.id


def _seed_memory_write_job(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> uuid.UUID:
    backend_id = uuid.uuid4()
    job_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            MemoryBackendProfile(
                id=backend_id,
                profile_key=f"profile-{backend_id.hex[:8]}",
                name="Local",
                backend_kind="local_pgvector",
                is_enabled=True,
                vector_store_config={},
                llm_config={},
                embedder_config={},
                reranker_config={},
                secret_refs={},
            )
        )
        session.add(
            MemoryWriteJob(
                id=job_id,
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                backend_profile_id=backend_id,
                source_kind="world_event",
                source_id=uuid.uuid4(),
                payload_json={},
                dedupe_key=f"dedupe-{job_id.hex}",
                status="pending",
                attempt_count=0,
            )
        )
        session.commit()
    return job_id
