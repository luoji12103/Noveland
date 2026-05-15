from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from noveland.auth.models import User
from noveland.events.models import WorldEventModel, WorldSnapshotModel
from noveland.media.models import MediaAsset, MediaObject
from noveland.media.storage import LocalMediaObjectStorage
from noveland.storage import LocalObjectStorage
from noveland.storage.integrity import StorageIntegrityAuditService
from noveland.worlds.models import Scene, World, Worldline
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_storage_integrity_audit_passes_matching_media_and_snapshot(tmp_path: Path) -> None:
    engine = _engine()
    storage = LocalMediaObjectStorage(tmp_path / "media")
    object_storage = LocalObjectStorage(tmp_path / "objects")
    world_id, worldline_id = _seed_world(engine)
    media_asset_id = uuid.uuid4()
    media_bytes = b"media-bytes"
    stored_media = storage.write_bytes(
        f"worlds/{world_id}/worldlines/{worldline_id}/assets/{media_asset_id}/original.png",
        media_bytes,
        content_type="image/png",
    )
    snapshot_event_id = uuid.uuid4()
    snapshot_payload = {"world_id": str(world_id), "source_sequence": 1, "clock": None}
    stored_snapshot = object_storage.write_json(
        f"worlds/{world_id}/worldlines/{worldline_id}/snapshots/1.json",
        snapshot_payload,
    )

    with Session(engine) as session:
        session.add(
            MediaAsset(
                id=media_asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind="image",
                asset_role="original_image",
                source_kind="manual_upload",
                status="available",
                visibility="private",
                storage_uri=stored_media.uri,
                preview_uri=None,
                thumbnail_uri=None,
                mime_type="image/png",
                file_ext="png",
                size_bytes=stored_media.size_bytes,
                checksum_sha256=stored_media.checksum_sha256,
                width=None,
                height=None,
                duration_ms=None,
                sample_rate_hz=None,
                audio_channels=None,
                has_alpha=None,
                color_mode=None,
                provider_kind=None,
                source_job_id=None,
                source_event_id=None,
                source_invocation_id=None,
                title="Example",
                description=None,
                created_by_actor_ref="user:test",
                metadata_json={},
            ),
        )
        session.add(
            MediaObject(
                id=uuid.uuid4(),
                asset_id=media_asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                object_role="original",
                storage_uri=stored_media.uri,
                filename="original.png",
                mime_type="image/png",
                size_bytes=stored_media.size_bytes,
                checksum_sha256=stored_media.checksum_sha256,
                width=None,
                height=None,
                duration_ms=None,
                sample_rate_hz=None,
                audio_channels=None,
                frame_rate=None,
                metadata_json={},
            ),
        )
        session.add(
            WorldEventModel(
                id=snapshot_event_id,
                world_id=world_id,
                worldline_id=worldline_id,
                sequence=1,
                event_name="world.clock_advanced",
                importance="system",
                payload={},
                wall_time=datetime.now(UTC),
                world_time=None,
                actor_ref="system:runtime",
            ),
        )
        session.add(
            WorldSnapshotModel(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                covers_event_sequence=1,
                schema_version="world_state.v1",
                status="valid",
                payload=None,
                payload_uri=stored_snapshot.uri,
                snapshot_metadata={},
                created_by_event_id=snapshot_event_id,
            ),
        )
        session.commit()

    with Session(engine) as session:
        result = StorageIntegrityAuditService(
            session,
            media_storage=storage,
            object_storage=object_storage,
        ).audit()

    assert result.status == "ok"
    assert result.media_object_count == 1
    assert result.snapshot_payload_count == 1
    assert result.ok_count == 2
    assert result.missing_count == 0
    assert result.size_mismatch_count == 0
    assert result.checksum_mismatch_count == 0
    assert result.unreadable_count == 0
    assert result.invalid_metadata_count == 0
    assert all("storage_uri" not in finding.reason for finding in result.findings)
    assert "media://" not in repr(result)
    assert str(tmp_path) not in repr(result)


def test_storage_integrity_audit_detects_missing_and_mismatched_media(tmp_path: Path) -> None:
    engine = _engine()
    storage = LocalMediaObjectStorage(tmp_path / "media")
    object_storage = LocalObjectStorage(tmp_path / "objects")
    world_id, worldline_id = _seed_world(engine)
    media_asset_id = uuid.uuid4()
    stored_media = storage.write_bytes(
        f"worlds/{world_id}/worldlines/{worldline_id}/assets/{media_asset_id}/original.png",
        b"media-bytes",
        content_type="image/png",
    )
    missing_object_uri = stored_media.uri
    storage.delete(missing_object_uri)
    mismatch_asset_id = uuid.uuid4()
    mismatch_uri = storage.write_bytes(
        f"worlds/{world_id}/worldlines/{worldline_id}/assets/{mismatch_asset_id}/original.png",
        b"correct-bytes",
        content_type="image/png",
    ).uri

    with Session(engine) as session:
        session.add(
            MediaAsset(
                id=media_asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind="image",
                asset_role="original_image",
                source_kind="manual_upload",
                status="available",
                visibility="private",
                storage_uri=missing_object_uri,
                preview_uri=None,
                thumbnail_uri=None,
                mime_type="image/png",
                file_ext="png",
                size_bytes=len(b"media-bytes"),
                checksum_sha256=hashlib.sha256(b"media-bytes").hexdigest(),
                width=None,
                height=None,
                duration_ms=None,
                sample_rate_hz=None,
                audio_channels=None,
                has_alpha=None,
                color_mode=None,
                provider_kind=None,
                source_job_id=None,
                source_event_id=None,
                source_invocation_id=None,
                title="Missing",
                description=None,
                created_by_actor_ref="user:test",
                metadata_json={},
            ),
        )
        session.add(
            MediaObject(
                id=uuid.uuid4(),
                asset_id=media_asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                object_role="original",
                storage_uri=missing_object_uri,
                filename="original.png",
                mime_type="image/png",
                size_bytes=len(b"media-bytes"),
                checksum_sha256=hashlib.sha256(b"media-bytes").hexdigest(),
                width=None,
                height=None,
                duration_ms=None,
                sample_rate_hz=None,
                audio_channels=None,
                frame_rate=None,
                metadata_json={},
            ),
        )
        session.add(
            MediaAsset(
                id=mismatch_asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind="image",
                asset_role="original_image",
                source_kind="manual_upload",
                status="available",
                visibility="private",
                storage_uri=mismatch_uri,
                preview_uri=None,
                thumbnail_uri=None,
                mime_type="image/png",
                file_ext="png",
                size_bytes=len(b"wrong-size"),
                checksum_sha256="0" * 64,
                width=None,
                height=None,
                duration_ms=None,
                sample_rate_hz=None,
                audio_channels=None,
                has_alpha=None,
                color_mode=None,
                provider_kind=None,
                source_job_id=None,
                source_event_id=None,
                source_invocation_id=None,
                title="Mismatch",
                description=None,
                created_by_actor_ref="user:test",
                metadata_json={},
            ),
        )
        session.add(
            MediaObject(
                id=uuid.uuid4(),
                asset_id=mismatch_asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                object_role="original",
                storage_uri=mismatch_uri,
                filename="original.png",
                mime_type="image/png",
                size_bytes=len(b"wrong-size"),
                checksum_sha256="0" * 64,
                width=None,
                height=None,
                duration_ms=None,
                sample_rate_hz=None,
                audio_channels=None,
                frame_rate=None,
                metadata_json={},
            ),
        )
        session.commit()

    with Session(engine) as session:
        result = StorageIntegrityAuditService(
            session,
            media_storage=storage,
            object_storage=object_storage,
        ).audit()

    assert result.status == "error"
    assert result.missing_count == 1
    assert result.size_mismatch_count == 1
    assert result.checksum_mismatch_count == 1
    codes = {finding.status for finding in result.findings}
    assert "media_object_missing_or_unreadable" in codes
    assert "media_object_size_mismatch" in codes
    assert "media_object_checksum_mismatch" in codes


def test_storage_integrity_audit_detects_missing_snapshot_payload(tmp_path: Path) -> None:
    engine = _engine()
    storage = LocalMediaObjectStorage(tmp_path / "media")
    object_storage = LocalObjectStorage(tmp_path / "objects")
    world_id, worldline_id = _seed_world(engine)

    with Session(engine) as session:
        event_id = uuid.uuid4()
        session.add(
            WorldEventModel(
                id=event_id,
                world_id=world_id,
                worldline_id=worldline_id,
                sequence=1,
                event_name="world.clock_advanced",
                importance="system",
                payload={},
                wall_time=__import__("datetime").datetime.now(__import__("datetime").UTC),
                world_time=None,
                actor_ref="system:runtime",
            ),
        )
        session.add(
            WorldSnapshotModel(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                covers_event_sequence=1,
                schema_version="world_state.v1",
                status="valid",
                payload=None,
                payload_uri="object://worlds/missing-snapshot.json",
                snapshot_metadata={},
                created_by_event_id=event_id,
            ),
        )
        session.commit()

    with Session(engine) as session:
        result = StorageIntegrityAuditService(
            session,
            media_storage=storage,
            object_storage=object_storage,
        ).audit()

    assert result.status == "error"
    assert result.unreadable_count == 1
    assert any(
        finding.status == "snapshot_payload_missing_or_unreadable"
        for finding in result.findings
    )


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        cast(Table, World.__table__),
        cast(Table, User.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, Scene.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, WorldSnapshotModel.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, MediaObject.__table__),
    ):
        table.create(engine)
    return engine


def _seed_world(engine: Engine) -> tuple[uuid.UUID, uuid.UUID]:
    world_id = uuid.uuid4()
    worldline_id = uuid.uuid4()
    with Session(engine) as session:
        owner_id = uuid.uuid4()
        session.add(User(id=owner_id, email="audit@example.test", display_name="Audit"))
        session.add(
            World(
                id=world_id,
                owner_user_id=owner_id,
                slug=f"world-{world_id.hex[:8]}",
                name="Audit World",
                rules_config={},
            ),
        )
        session.add(
            Worldline(
                id=worldline_id,
                world_id=world_id,
                worldline_key="primary",
                name="Primary",
                description=None,
                parent_worldline_id=None,
                forked_from_snapshot_id=None,
                fork_event_sequence=None,
                status="active",
                created_by_actor_ref="system:test",
                metadata={},
            ),
        )
        session.add(
            Scene(
                id=uuid.uuid4(),
                world_id=world_id,
                scene_key="home",
                name="Home",
                description=None,
                region_key="home",
                location_tags=[],
                opening_rules={},
                is_active=True,
            ),
        )
        session.commit()
    return world_id, worldline_id
