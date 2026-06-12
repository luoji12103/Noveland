from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

from fastapi.testclient import TestClient
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.media.models import MediaAsset, MediaObject, MediaReference
from noveland.media.storage import LocalMediaObjectStorage
from noveland.moderation.models import ModerationAction, ModerationIncident, ModerationReport
from noveland.narrative.models import NarrativeArtifact, NarrativePublication
from noveland.services.api.app import create_app
from noveland.services.api.csrf import SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.services.api.media import _media_storage
from noveland.services.api.reader_media import _reader_media_storage
from noveland.worlds.models import World, Worldline, WorldMembership
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

FORBIDDEN_RESPONSE_MARKERS = (
    "storage_uri",
    "media://",
    "filesystem",
    "base64",
    "raw_prompt",
    "raw_output",
    "api_key",
    "bearer_token",
    "authorization",
    "secret",
)


def test_reader_media_lists_fetches_and_downloads_published_media() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    worldline_id, _fork_id = _seed_worldlines(engine, world_id)
    artifact_id = _seed_published_artifact(engine, world_id, worldline_id)
    asset_id, object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        worldline_id,
        visibility="reader_visible",
        data=b"reader-image",
    )
    _seed_reference(engine, world_id, worldline_id, asset_id, "narrative_artifact", artifact_id)

    unauthenticated = client.get(f"/worlds/{world_id}/reader/media")
    _authenticate_session_only(client, member_token)
    listed = client.get(f"/worlds/{world_id}/reader/media")
    detail = client.get(f"/worlds/{world_id}/reader/media/{asset_id}")
    downloaded = client.get(f"/worlds/{world_id}/reader/media/objects/{object_id}/download")
    scoped_downloaded = client.get(_reader_media_download_path(world_id, worldline_id, object_id))

    _authenticate_session_only(client, owner_token)
    admin_listed = client.get(
        f"/worlds/{world_id}/reader/media",
        params={"worldline_id": str(worldline_id)},
    )

    assert unauthenticated.status_code == 401
    assert listed.status_code == 200
    assert [item["asset_id"] for item in listed.json()] == [str(asset_id)]
    assert detail.status_code == 200
    assert detail.json()["asset_id"] == str(asset_id)
    assert detail.json()["objects"][0]["object_id"] == str(object_id)
    assert detail.json()["objects"][0]["download_url"] == _reader_media_download_path(
        world_id, worldline_id, object_id
    )
    assert downloaded.status_code == 404
    assert scoped_downloaded.status_code == 200
    assert scoped_downloaded.content == b"reader-image"
    assert scoped_downloaded.headers["content-type"].startswith("image/png")
    assert scoped_downloaded.headers["x-content-type-options"] == "nosniff"
    assert admin_listed.status_code == 200
    _assert_no_forbidden_markers(listed.json())
    _assert_no_forbidden_markers(detail.json())


def test_reader_media_suppresses_active_content_type_objects() -> None:
    client, engine = _client_with_database()
    owner_id, _owner_token = _seed_user(engine, "owner-active-media@example.test")
    member_id, member_token = _seed_user(engine, "member-active-media@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    worldline_id, _fork_id = _seed_worldlines(engine, world_id)
    artifact_id = _seed_published_artifact(engine, world_id, worldline_id)
    safe_video_id, safe_object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        worldline_id,
        visibility="reader_visible",
        asset_kind="video",
        asset_role="video_clip",
        object_role="original",
        filename="reader.mp4",
        content_type="video/mp4",
        data=b"safe-video-bytes",
    )
    unsafe_video_id, unsafe_object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        worldline_id,
        visibility="reader_visible",
        asset_kind="video",
        asset_role="video_clip",
        object_role="original",
        filename="reader.html",
        content_type="text/html",
        data=b"<html><script>window.__noveland_probe=1</script></html>",
    )
    _seed_reference(
        engine, world_id, worldline_id, safe_video_id, "narrative_artifact", artifact_id
    )
    _seed_reference(
        engine,
        world_id,
        worldline_id,
        unsafe_video_id,
        "narrative_artifact",
        artifact_id,
    )

    _authenticate_session_only(client, member_token)
    listed = client.get(f"/worlds/{world_id}/reader/media")
    unsafe_detail = client.get(f"/worlds/{world_id}/reader/media/{unsafe_video_id}")
    unsafe_download = client.get(
        _reader_media_download_path(world_id, worldline_id, unsafe_object_id)
    )
    safe_download = client.get(_reader_media_download_path(world_id, worldline_id, safe_object_id))

    assert listed.status_code == 200
    assert [item["asset_id"] for item in listed.json()] == [str(safe_video_id)]
    assert listed.json()[0]["objects"][0]["content_type"] == "video/mp4"
    assert unsafe_detail.status_code == 404
    assert unsafe_download.status_code == 404
    assert safe_download.status_code == 200
    assert safe_download.headers["content-type"].startswith("video/mp4")


def test_reader_media_suppresses_non_deliverable_assets() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    worldline_id, _fork_id = _seed_worldlines(engine, world_id)
    artifact_id = _seed_published_artifact(engine, world_id, worldline_id)
    hidden_id, hidden_object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        worldline_id,
        visibility="hidden",
    )
    private_id, _private_object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        worldline_id,
        visibility="private",
    )
    unreferenced_id, _unreferenced_object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        worldline_id,
        visibility="reader_visible",
    )
    registered_id = _seed_registered_asset(engine, world_id, worldline_id, "reader_visible")
    deleted_id, _deleted_object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        worldline_id,
        visibility="reader_visible",
        status="deleted",
    )
    for asset_id in (hidden_id, private_id, registered_id, deleted_id):
        _seed_reference(engine, world_id, worldline_id, asset_id, "narrative_artifact", artifact_id)

    _authenticate_session_only(client, owner_token)
    listed = client.get(f"/worlds/{world_id}/reader/media")
    hidden_detail = client.get(f"/worlds/{world_id}/reader/media/{hidden_id}")
    hidden_download = client.get(
        _reader_media_download_path(world_id, worldline_id, hidden_object_id)
    )
    private_detail = client.get(f"/worlds/{world_id}/reader/media/{private_id}")
    unreferenced_detail = client.get(f"/worlds/{world_id}/reader/media/{unreferenced_id}")
    registered_detail = client.get(f"/worlds/{world_id}/reader/media/{registered_id}")
    deleted_detail = client.get(f"/worlds/{world_id}/reader/media/{deleted_id}")

    assert listed.status_code == 200
    assert listed.json() == []
    assert hidden_detail.status_code == 404
    assert hidden_download.status_code == 404
    assert private_detail.status_code == 404
    assert unreferenced_detail.status_code == 404
    assert registered_detail.status_code == 404
    assert deleted_detail.status_code == 404


def test_reader_media_rejects_cross_world_and_cross_worldline_requests() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    other_id, _other_token = _seed_user(engine, "other@example.test")
    world_id = _seed_world(engine, owner_id)
    other_world_id = _seed_world(engine, other_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    worldline_id, fork_id = _seed_worldlines(engine, world_id)
    other_worldline_id, _other_fork_id = _seed_worldlines(engine, other_world_id)
    artifact_id = _seed_published_artifact(engine, world_id, worldline_id)
    other_artifact_id = _seed_published_artifact(engine, other_world_id, other_worldline_id)
    asset_id, object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        worldline_id,
        visibility="reader_visible",
    )
    fork_asset_id, fork_object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        fork_id,
        visibility="reader_visible",
    )
    other_asset_id, _other_object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        other_world_id,
        other_worldline_id,
        visibility="reader_visible",
    )
    _seed_reference(engine, world_id, worldline_id, asset_id, "narrative_artifact", artifact_id)
    _seed_reference(engine, world_id, fork_id, fork_asset_id, "narrative_artifact", artifact_id)
    _seed_reference(
        engine,
        other_world_id,
        other_worldline_id,
        other_asset_id,
        "narrative_artifact",
        other_artifact_id,
    )

    _authenticate_session_only(client, owner_token)
    wrong_worldline_list = client.get(
        f"/worlds/{world_id}/reader/media",
        params={"worldline_id": str(other_worldline_id)},
    )
    wrong_world = client.get(f"/worlds/{world_id}/reader/media/{other_asset_id}")
    wrong_worldline = client.get(
        f"/worlds/{world_id}/reader/media/{fork_asset_id}",
        params={"worldline_id": str(worldline_id)},
    )
    unscoped_object = client.get(
        f"/worlds/{world_id}/reader/media/objects/{fork_object_id}/download"
    )
    wrong_object_worldline = client.get(
        f"/worlds/{world_id}/reader/media/objects/{fork_object_id}/download",
        params={"worldline_id": str(worldline_id)},
    )
    wrong_object_worldline_path = client.get(
        _reader_media_download_path(world_id, worldline_id, fork_object_id)
    )
    valid_object = client.get(_reader_media_download_path(world_id, worldline_id, object_id))

    assert wrong_worldline_list.status_code == 404
    assert wrong_world.status_code == 404
    assert wrong_worldline.status_code == 404
    assert unscoped_object.status_code == 404
    assert wrong_object_worldline.status_code == 404
    assert wrong_object_worldline_path.status_code == 404
    assert valid_object.status_code == 200


def test_reader_media_requires_reader_visible_reference_context() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    worldline_id, _fork_id = _seed_worldlines(engine, world_id)
    unpublished_artifact_id = _seed_published_artifact(
        engine,
        world_id,
        worldline_id,
        status="unpublished",
        reader_visible=False,
    )
    asset_id, object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        worldline_id,
        visibility="reader_visible",
    )
    _seed_reference(
        engine,
        world_id,
        worldline_id,
        asset_id,
        "narrative_artifact",
        unpublished_artifact_id,
    )

    _authenticate_session_only(client, owner_token)
    listed = client.get(f"/worlds/{world_id}/reader/media")
    detail = client.get(f"/worlds/{world_id}/reader/media/{asset_id}")
    download = client.get(_reader_media_download_path(world_id, worldline_id, object_id))

    assert listed.status_code == 200
    assert listed.json() == []
    assert detail.status_code == 404
    assert download.status_code == 404


def test_reader_media_suppresses_moderated_reference_targets() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner-moderated-reference@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    worldline_id, _fork_id = _seed_worldlines(engine, world_id)
    conversation_id, turn_id = _seed_conversation(engine, world_id, worldline_id)
    turn_asset_id, turn_object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        worldline_id,
        visibility="reader_visible",
        data=b"turn-media",
    )
    session_asset_id, session_object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        worldline_id,
        visibility="reader_visible",
        data=b"session-media",
    )
    _seed_reference(
        engine, world_id, worldline_id, turn_asset_id, "conversation_turn", turn_id
    )
    _seed_reference(
        engine,
        world_id,
        worldline_id,
        session_asset_id,
        "conversation_session",
        conversation_id,
    )
    _seed_moderation_action(
        engine,
        world_id,
        worldline_id,
        target_ref_kind="conversation_turn",
        target_ref_id=turn_id,
    )
    _seed_moderation_action(
        engine,
        world_id,
        worldline_id,
        target_ref_kind="conversation_session",
        target_ref_id=conversation_id,
    )

    _authenticate_session_only(client, owner_token)
    listed = client.get(f"/worlds/{world_id}/reader/media")
    turn_detail = client.get(f"/worlds/{world_id}/reader/media/{turn_asset_id}")
    session_detail = client.get(f"/worlds/{world_id}/reader/media/{session_asset_id}")
    turn_download = client.get(
        _reader_media_download_path(world_id, worldline_id, turn_object_id)
    )
    session_download = client.get(
        _reader_media_download_path(world_id, worldline_id, session_object_id)
    )

    assert listed.status_code == 200
    assert listed.json() == []
    assert turn_detail.status_code == 404
    assert session_detail.status_code == 404
    assert turn_download.status_code == 404
    assert session_download.status_code == 404


def test_reader_media_suppresses_moderated_worldline_and_publication_targets() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner-moderated-surface@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    worldline_id, fork_id = _seed_worldlines(engine, world_id)
    artifact_id = _seed_published_artifact(engine, world_id, worldline_id)
    publication_id = _publication_id_for_artifact(engine, artifact_id)
    publication_asset_id, publication_object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        worldline_id,
        visibility="reader_visible",
        data=b"publication-media",
    )
    fork_artifact_id = _seed_published_artifact(engine, world_id, fork_id)
    worldline_asset_id, worldline_object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        fork_id,
        visibility="reader_visible",
        data=b"worldline-media",
    )
    _seed_reference(
        engine,
        world_id,
        worldline_id,
        publication_asset_id,
        "narrative_artifact",
        artifact_id,
    )
    _seed_reference(
        engine,
        world_id,
        fork_id,
        worldline_asset_id,
        "narrative_artifact",
        fork_artifact_id,
    )
    _seed_moderation_action(
        engine,
        world_id,
        worldline_id,
        target_ref_kind="narrative_publication",
        target_ref_id=publication_id,
    )
    _seed_moderation_action(
        engine,
        world_id,
        fork_id,
        target_ref_kind="worldline",
        target_ref_id=fork_id,
    )

    _authenticate_session_only(client, owner_token)
    listed = client.get(f"/worlds/{world_id}/reader/media")
    publication_detail = client.get(
        f"/worlds/{world_id}/reader/media/{publication_asset_id}"
    )
    worldline_detail = client.get(f"/worlds/{world_id}/reader/media/{worldline_asset_id}")
    publication_download = client.get(
        _reader_media_download_path(world_id, worldline_id, publication_object_id)
    )
    worldline_download = client.get(
        _reader_media_download_path(world_id, fork_id, worldline_object_id)
    )

    assert listed.status_code == 200
    assert listed.json() == []
    assert publication_detail.status_code == 404
    assert worldline_detail.status_code == 404
    assert publication_download.status_code == 404
    assert worldline_download.status_code == 404


def test_reader_media_keeps_unsuppressed_references_when_one_reference_is_moderated() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner-mixed-reference@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    worldline_id, _fork_id = _seed_worldlines(engine, world_id)
    _conversation_id, turn_id = _seed_conversation(engine, world_id, worldline_id)
    artifact_id = _seed_published_artifact(engine, world_id, worldline_id)
    asset_id, object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        worldline_id,
        visibility="reader_visible",
        data=b"mixed-media",
    )
    _seed_reference(engine, world_id, worldline_id, asset_id, "conversation_turn", turn_id)
    _seed_reference(engine, world_id, worldline_id, asset_id, "narrative_artifact", artifact_id)
    _seed_moderation_action(
        engine,
        world_id,
        worldline_id,
        target_ref_kind="conversation_turn",
        target_ref_id=turn_id,
    )

    _authenticate_session_only(client, owner_token)
    listed = client.get(f"/worlds/{world_id}/reader/media")
    detail = client.get(f"/worlds/{world_id}/reader/media/{asset_id}")
    download = client.get(_reader_media_download_path(world_id, worldline_id, object_id))

    assert listed.status_code == 200
    assert [item["asset_id"] for item in listed.json()] == [str(asset_id)]
    assert detail.status_code == 200
    assert [reference["ref_kind"] for reference in detail.json()["references"]] == [
        "narrative_artifact"
    ]
    assert download.status_code == 200
    assert download.content == b"mixed-media"


def test_admin_media_download_route_is_unchanged() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    worldline_id, _fork_id = _seed_worldlines(engine, world_id)
    _asset_id, object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        worldline_id,
        visibility="world_admin",
        data=b"admin-media",
    )

    _authenticate_session_only(client, owner_token)
    admin_download = client.get(f"/worlds/{world_id}/media/objects/{object_id}/download")

    assert admin_download.status_code == 200
    assert admin_download.content == b"admin-media"


class _ReaderMediaApiClient(TestClient):
    reader_media_storage: LocalMediaObjectStorage


def _client_with_database() -> tuple[_ReaderMediaApiClient, Engine]:
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
    app.dependency_overrides[_reader_media_storage] = lambda: storage
    app.dependency_overrides[_media_storage] = lambda: storage
    app.state._reader_media_storage_tmp = storage_tmp
    client = _ReaderMediaApiClient(app)
    client.reader_media_storage = storage
    return client, engine


def _create_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, NarrativeArtifact.__table__),
        cast(Table, NarrativePublication.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, MediaObject.__table__),
        cast(Table, MediaReference.__table__),
        cast(Table, ModerationReport.__table__),
        cast(Table, ModerationIncident.__table__),
        cast(Table, ModerationAction.__table__),
    ):
        table.create(engine)


def _seed_user(engine: Engine, email: str, platform_admin: bool = False) -> tuple[uuid.UUID, str]:
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
            ),
        )
        if platform_admin:
            session.add(
                PlatformRoleAssignment(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    role=AuthRole.PLATFORM_ADMIN.value,
                    assigned_at=now,
                ),
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
            ),
        )
        session.commit()
    return world_id


def _seed_worldlines(engine: Engine, world_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    with Session(engine) as session:
        primary = ensure_primary_worldline(session, world_id)
        fork = Worldline(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_key=f"fork-{uuid.uuid4().hex[:8]}",
            name="Fork",
            parent_worldline_id=primary.id,
            status="active",
            created_by_actor_ref="test",
            metadata_json={},
        )
        session.add(fork)
        session.commit()
        return primary.id, fork.id


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
            ),
        )
        session.commit()


def _seed_conversation(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> tuple[uuid.UUID, uuid.UUID]:
    conversation_id = uuid.uuid4()
    turn_id = uuid.uuid4()
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(
            ConversationSession(
                id=conversation_id,
                world_id=world_id,
                worldline_id=worldline_id,
                session_key=f"conversation-{conversation_id.hex[:8]}",
                title="Reader Conversation",
                scope_type="world",
                mode="manual_chain",
                status="completed",
                objective="Reader-safe conversation.",
                opening_prompt="Begin.",
                max_turns=1,
                next_turn_index=1,
                policy_config={},
                writer_config={},
                memory_config={},
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            ConversationTurn(
                id=turn_id,
                session_id=conversation_id,
                turn_index=0,
                speaker_kind="agent",
                speaker_agent_id=None,
                input_text="Reader input.",
                output_text="Reader output.",
                status="succeeded",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return conversation_id, turn_id


def _seed_published_artifact(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    status: str = "published",
    reader_visible: bool = True,
) -> uuid.UUID:
    artifact_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            NarrativeArtifact(
                id=artifact_id,
                world_id=world_id,
                worldline_id=worldline_id,
                title="Chapter",
                content="Reader-safe content",
                artifact_kind="chapter_draft",
                artifact_metadata={},
            ),
        )
        session.add(
            NarrativePublication(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                artifact_id=artifact_id,
                status=status,
                reader_visible=reader_visible,
                published_metadata={},
                published_at=datetime.now(UTC) if status == "published" else None,
            ),
        )
        session.commit()
    return artifact_id


def _publication_id_for_artifact(engine: Engine, artifact_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        publication_id = session.scalars(
            select(NarrativePublication.id).where(
                NarrativePublication.artifact_id == artifact_id
            )
        ).one()
    return publication_id


def _seed_available_asset_with_object(
    engine: Engine,
    storage: LocalMediaObjectStorage,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    visibility: str,
    status: str = "available",
    data: bytes = b"image-bytes",
    asset_kind: str = "image",
    asset_role: str = "reference_image",
    object_role: str = "original",
    filename: str = "reader.png",
    content_type: str = "image/png",
) -> tuple[uuid.UUID, uuid.UUID]:
    asset_id = uuid.uuid4()
    object_id = uuid.uuid4()
    stored = storage.write_bytes(
        f"worlds/{world_id}/worldlines/{worldline_id}/assets/{asset_id}/{filename}",
        data,
        content_type=content_type,
    )
    with Session(engine) as session:
        session.add(
            MediaAsset(
                id=asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind=asset_kind,
                asset_role=asset_role,
                source_kind="manual_upload",
                status=status,
                visibility=visibility,
                storage_uri=stored.uri,
                mime_type=content_type,
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
                created_by_actor_ref="test",
                title="Reader image",
                metadata_json={
                    "source_note": "safe",
                    "redaction_probe": "not an api_key or storage path",
                },
            ),
        )
        session.add(
            MediaObject(
                id=object_id,
                asset_id=asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                object_role=object_role,
                storage_uri=stored.uri,
                filename=filename,
                mime_type=content_type,
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
                width=100,
                height=100,
                metadata_json={"secret": "must not leak"},
            ),
        )
        session.commit()
    return asset_id, object_id


def _seed_registered_asset(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    visibility: str,
) -> uuid.UUID:
    asset_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            MediaAsset(
                id=asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind="image",
                asset_role="reference_image",
                source_kind="manual_upload",
                status="registered",
                visibility=visibility,
                created_by_actor_ref="test",
                metadata_json={},
            ),
        )
        session.commit()
    return asset_id


def _seed_reference(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    asset_id: uuid.UUID,
    ref_kind: str,
    ref_id: uuid.UUID,
) -> uuid.UUID:
    reference_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            MediaReference(
                id=reference_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_id=asset_id,
                ref_kind=ref_kind,
                ref_id=ref_id,
                ref_role="attachment",
                display_order=0,
                metadata_json={"storage_uri": "must not leak"},
            ),
        )
        session.commit()
    return reference_id


def _seed_moderation_action(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    target_ref_kind: str,
    target_ref_id: uuid.UUID,
    action_kind: str = "takedown_content",
) -> uuid.UUID:
    action_id = uuid.uuid4()
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(
            ModerationAction(
                id=action_id,
                world_id=world_id,
                worldline_id=worldline_id,
                action_kind=action_kind,
                status="applied",
                target_ref_kind=target_ref_kind,
                target_ref_id=target_ref_id,
                reason="Reviewed takedown.",
                created_by_actor_ref="test",
                audit_summary_json={"reader_delivery_suppression": True},
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return action_id


def _reader_media_download_path(
    world_id: uuid.UUID, worldline_id: uuid.UUID, object_id: uuid.UUID
) -> str:
    return (
        f"/worlds/{world_id}/reader/media/worldlines/"
        f"{worldline_id}/objects/{object_id}/download"
    )


def _authenticate_session_only(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)


def _assert_no_forbidden_markers(payload: Any) -> None:
    serialized = json.dumps(payload, sort_keys=True).lower()
    for marker in FORBIDDEN_RESPONSE_MARKERS:
        assert marker not in serialized
