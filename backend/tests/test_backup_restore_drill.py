from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient
from noveland.agents.models import Agent
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.conversations.models import (
    ConversationSession,
    ConversationTurn,
    ConversationTurnPresentation,
)
from noveland.events.models import WorldEventModel, WorldSnapshotModel
from noveland.media.models import MediaAsset, MediaObject
from noveland.media.storage import LocalMediaObjectStorage
from noveland.memory.models import AgentMemoryItem
from noveland.providers.models import ProviderIntegration
from noveland.services.api.app import create_app
from noveland.services.api.csrf import SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.storage import LocalObjectStorage
from noveland.storage.integrity import StorageIntegrityAuditService
from noveland.storage.restore_drill import BackupRestoreDrillService
from noveland.worlds.models import Scene, World, Worldline
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

FORBIDDEN_RESTORE_TOKENS = (
    "storage_uri",
    "media://",
    "object://",
    "/tmp/private-file",
    "sk-live-secret",
    "Bearer",
    "raw prompt",
    "raw output",
    "base64",
    "invite-token",
)


def test_backup_restore_drill_passes_restored_local_fixture(tmp_path: Path) -> None:
    engine = _engine()
    storage = LocalMediaObjectStorage(tmp_path / "media")
    object_storage = LocalObjectStorage(tmp_path / "objects")
    _seed_restored_fixture(engine, storage, object_storage)

    with Session(engine) as session:
        report = BackupRestoreDrillService(
            session,
            storage_audit=StorageIntegrityAuditService(
                session,
                media_storage=storage,
                object_storage=object_storage,
            ).audit(include_ok=True),
            openspec_root_exists=True,
            current_specs_exist=True,
            archived_change_count=2,
        ).report()

    checks = {check.check_key: check for check in report.checks}
    assert report.status == "ok"
    assert report.target_profile == "fresh_local_single_host"
    assert checks["database_state"].status == "ok"
    assert checks["media_and_snapshot_integrity"].status == "ok"
    assert checks["provider_config_without_secrets"].status == "ok"
    assert checks["openspec_docs_provenance"].status == "ok"
    assert checks["safe_restore_report"].status == "ok"
    _assert_no_forbidden_tokens(str(report))


def test_backup_restore_drill_blocks_missing_media_safely(tmp_path: Path) -> None:
    engine = _engine()
    storage = LocalMediaObjectStorage(tmp_path / "media")
    object_storage = LocalObjectStorage(tmp_path / "objects")
    stored_media_uri = _seed_restored_fixture(engine, storage, object_storage)
    storage.delete(stored_media_uri)

    with Session(engine) as session:
        report = BackupRestoreDrillService(
            session,
            storage_audit=StorageIntegrityAuditService(
                session,
                media_storage=storage,
                object_storage=object_storage,
            ).audit(include_ok=True),
            openspec_root_exists=True,
            current_specs_exist=True,
            archived_change_count=2,
        ).report()

    checks = {check.check_key: check for check in report.checks}
    assert report.status == "blocked"
    assert checks["media_and_snapshot_integrity"].status == "blocked"
    assert "Storage integrity audit is not clean." in checks[
        "media_and_snapshot_integrity"
    ].blockers
    _assert_no_forbidden_tokens(str(report))


def test_backup_restore_drill_blocks_provider_config_secret_markers(tmp_path: Path) -> None:
    engine = _engine()
    storage = LocalMediaObjectStorage(tmp_path / "media")
    object_storage = LocalObjectStorage(tmp_path / "objects")
    _seed_restored_fixture(
        engine,
        storage,
        object_storage,
        provider_config={"resolved_secret": "sk-live-secret"},
    )

    with Session(engine) as session:
        report = BackupRestoreDrillService(
            session,
            storage_audit=StorageIntegrityAuditService(
                session,
                media_storage=storage,
                object_storage=object_storage,
            ).audit(include_ok=True),
            openspec_root_exists=True,
            current_specs_exist=True,
            archived_change_count=2,
        ).report()

    checks = {check.check_key: check for check in report.checks}
    assert report.status == "blocked"
    assert checks["provider_config_without_secrets"].status == "blocked"
    assert "sk-live-secret" not in str(report)
    _assert_no_forbidden_tokens(str(report))


def test_backup_restore_drill_endpoint_is_admin_only_and_safe(tmp_path: Path) -> None:
    client, engine = _client_with_database()
    platform_user_id, platform_token = _seed_user(
        engine,
        "restore-admin@example.test",
        platform_admin=True,
    )
    storage = LocalMediaObjectStorage(tmp_path / "media")
    object_storage = LocalObjectStorage(tmp_path / "objects")
    _seed_restored_fixture(engine, storage, object_storage, owner_user_id=platform_user_id)
    _authenticate(client, platform_token)

    response = client.get("/observability/readiness/backup-restore-drill")

    assert response.status_code == 200
    assert response.json()["readiness_kind"] == "backup_restore_drill"
    assert response.json()["target_profile"] == "fresh_local_single_host"
    assert response.json()["status"] in {"ok", "blocked"}
    _assert_no_forbidden_tokens(response.text)

    _member_id, member_token = _seed_user(
        engine,
        "restore-member@example.test",
        platform_admin=False,
    )
    _authenticate(client, member_token)
    forbidden = client.get("/observability/readiness/backup-restore-drill")

    assert forbidden.status_code == 403
    _assert_no_forbidden_tokens(forbidden.text)


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        cast(Table, User.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, Scene.__table__),
        cast(Table, Agent.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, WorldSnapshotModel.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, MediaObject.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, ConversationTurnPresentation.__table__),
        cast(Table, AgentMemoryItem.__table__),
        cast(Table, ProviderIntegration.__table__),
    ):
        table.create(engine)
    return engine


def _client_with_database() -> tuple[TestClient, Engine]:
    engine = _engine()
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
    return TestClient(app), engine


def _seed_user(engine: Engine, email: str, *, platform_admin: bool) -> tuple[uuid.UUID, str]:
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
                expires_at=now.replace(year=now.year + 1),
            ),
        )
        if platform_admin:
            session.add(
                PlatformRoleAssignment(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    role="platform_admin",
                    assigned_at=now,
                    assigned_by_user_id=None,
                ),
            )
        session.commit()
    return user_id, token


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)


def _seed_restored_fixture(
    engine: Engine,
    storage: LocalMediaObjectStorage,
    object_storage: LocalObjectStorage,
    *,
    owner_user_id: uuid.UUID | None = None,
    provider_config: dict[str, object] | None = None,
) -> str:
    world_id = uuid.uuid4()
    worldline_id = uuid.uuid4()
    owner_id = owner_user_id or uuid.uuid4()
    agent_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    media_bytes = b"restore-drill-media"
    stored_media = storage.write_bytes(
        f"worlds/{world_id}/worldlines/{worldline_id}/assets/{asset_id}/original.png",
        media_bytes,
        content_type="image/png",
    )
    event_id = uuid.uuid4()
    stored_snapshot = object_storage.write_json(
        f"worlds/{world_id}/worldlines/{worldline_id}/snapshots/1.json",
        {"world_id": str(world_id), "worldline_id": str(worldline_id), "sequence": 1},
    )
    conversation_id = uuid.uuid4()
    turn_id = uuid.uuid4()
    with Session(engine) as session:
        if owner_user_id is None:
            session.add(
                User(
                    id=owner_id,
                    email=f"restore-{world_id.hex[:8]}@example.test",
                    display_name="Restore Owner",
                    is_active=True,
                ),
            )
        session.add(
            World(
                id=world_id,
                owner_user_id=owner_id,
                slug=f"restore-{world_id.hex[:8]}",
                name="Restore Drill World",
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
                created_by_actor_ref="system:restore-drill",
                metadata={},
            ),
        )
        session.add(
            Scene(
                id=uuid.uuid4(),
                world_id=world_id,
                scene_key="restore-room",
                name="Restore Room",
                description=None,
                region_key="restore",
                location_tags=[],
                opening_rules={},
                is_active=True,
            ),
        )
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key="restore-guide",
                display_name="Restore Guide",
                kind="role_agent",
                narrative_role="supporting_cast",
                importance="minor",
                canon_status="original_expansion",
                character_category="side_character",
                character_profile={"summary": "Safe restore fixture."},
                config={},
                is_enabled=True,
            ),
        )
        session.add(
            WorldEventModel(
                id=event_id,
                world_id=world_id,
                worldline_id=worldline_id,
                sequence=1,
                event_name="restore.drill",
                importance="system",
                payload={},
                wall_time=datetime.now(UTC),
                world_time=None,
                actor_ref="system:restore-drill",
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
                created_by_event_id=event_id,
            ),
        )
        session.add(
            MediaAsset(
                id=asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind="image",
                asset_role="original_image",
                source_kind="test_fixture",
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
                title="Restore Media",
                description=None,
                created_by_actor_ref="system:restore-drill",
                metadata_json={},
            ),
        )
        session.add(
            MediaObject(
                id=uuid.uuid4(),
                asset_id=asset_id,
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
            ConversationSession(
                id=conversation_id,
                world_id=world_id,
                worldline_id=worldline_id,
                scene_id=None,
                session_key=f"restore-{conversation_id.hex[:8]}",
                title="Restore Conversation",
                scope_type="world",
                mode="manual_chain",
                status="completed",
                objective="restore drill",
                opening_prompt="",
                max_turns=1,
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
                speaker_kind="agent",
                speaker_agent_id=agent_id,
                input_text="hello",
                output_text="restored",
                status="succeeded",
            ),
        )
        session.add(
            ConversationTurnPresentation(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                speaker_agent_id=agent_id,
                emotion_key="neutral",
                emotion_intensity=0.5,
                background_asset_id=asset_id,
                presentation_json={"safe": True},
                render_state="visual_rendered",
            ),
        )
        session.add(
            AgentMemoryItem(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                source_event_id=event_id,
                content="Restored memory.",
                metadata_json={"source": "restore_drill"},
                embedding=[0.1, 0.2, 0.3],
                visibility="private",
                is_active=True,
            ),
        )
        session.add(
            ProviderIntegration(
                id=uuid.uuid4(),
                world_id=world_id,
                scope_kind="world",
                scope_key=str(world_id),
                provider_kind="text_generation",
                adapter_kind="fake",
                provider_key="restore-provider",
                display_name="Restore Provider",
                base_url=None,
                auth_ref="env:RESTORE_PROVIDER",
                config_json=provider_config or {"template": "safe"},
                default_params_json={"model": "fake-model"},
                status="active",
                visibility="world_admin",
            ),
        )
        session.commit()
    return stored_media.uri


def _assert_no_forbidden_tokens(text: str) -> None:
    for token in FORBIDDEN_RESTORE_TOKENS:
        assert token not in text
