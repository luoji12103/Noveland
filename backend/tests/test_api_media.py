from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from fastapi.testclient import TestClient
from noveland.agents.models import Agent
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.events import WorldEventAppend, WorldEventStore
from noveland.events.models import WorldEventModel
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
from noveland.narrative.models import NarrativeArtifact
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.services.api.media import _media_storage
from noveland.worlds.models import World, Worldline, WorldMembership
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_media_api_admin_crud_context_lineage_and_job_flow() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    primary_id, _fork_id = _seed_worldlines(engine, world_id)
    agent_id = _seed_agent(engine, world_id)
    conversation_id, turn_id = _seed_conversation(engine, world_id, primary_id)
    event_id = _seed_event(engine, world_id)

    _authenticate(client, owner_token)
    created = client.post(
        f"/worlds/{world_id}/media/assets",
        json={
            "worldline_id": str(primary_id),
            "asset_kind": "image",
            "asset_role": "reference_image",
            "source_kind": "manual_upload",
            "visibility": "world_member",
            "filename": "reference.png",
            "mime_type": "image/png",
            "metadata": {"tag": "reference"},
        },
    )
    asset_id = created.json()["id"]
    private = client.post(
        f"/worlds/{world_id}/media/assets",
        json={
            "worldline_id": str(primary_id),
            "asset_kind": "image",
            "asset_role": "composite_image",
            "source_kind": "composed",
            "visibility": "private",
        },
    )
    derived_id = private.json()["id"]
    context = client.post(
        f"/worlds/{world_id}/media/assets/{asset_id}/contexts",
        json={
            "worldline_id": str(primary_id),
            "conversation_id": str(conversation_id),
            "turn_id": str(turn_id),
            "agent_id": str(agent_id),
            "world_event_id": str(event_id),
            "context_role": "attachment",
        },
    )
    lineage = client.post(
        f"/worlds/{world_id}/media/assets/{derived_id}/inputs",
        json={
            "worldline_id": str(primary_id),
            "input_asset_id": asset_id,
            "input_role": "reference",
        },
    )
    job = client.post(
        f"/worlds/{world_id}/media/jobs",
        json={
            "worldline_id": str(primary_id),
            "conversation_id": str(conversation_id),
            "turn_id": str(turn_id),
            "agent_id": str(agent_id),
            "job_kind": "image_generation",
            "provider_kind": "manual",
            "request_json": {"prompt": "not executed"},
        },
    )
    cancelled = client.post(f"/worlds/{world_id}/media/jobs/{job.json()['id']}/cancel")
    listed = client.get(
        f"/worlds/{world_id}/media/assets", params={"worldline_id": str(primary_id)}
    )
    refs = client.get(f"/worlds/{world_id}/media/assets/{asset_id}/references")
    lineage_get = client.get(f"/worlds/{world_id}/media/assets/{derived_id}/lineage")

    assert created.status_code == 201
    assert created.json()["status"] == "registered"
    assert created.json()["storage_uri"] is None
    assert context.status_code == 201
    assert context.json()["turn_id"] == str(turn_id)
    assert lineage.status_code == 201
    assert job.status_code == 201
    assert job.json()["status"] == "queued"
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert len(listed.json()) == 2
    assert refs.json()["input_count"] == 1
    assert lineage_get.json()["inputs"][0]["input_asset_id"] == asset_id
    with Session(engine) as session:
        events = session.scalars(select(WorldEventModel)).all()
        assert [event.payload for event in events] == [{"kind": "seed"}]


def test_media_api_member_visibility_acl_and_csrf() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    stranger_id, stranger_token = _seed_user(engine, "stranger@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    primary_id, _fork_id = _seed_worldlines(engine, world_id)
    visible_id = _seed_asset(engine, world_id, primary_id, visibility="world_member")
    private_id = _seed_asset(engine, world_id, primary_id, visibility="private")
    stored = client.media_storage.write_bytes(
        f"worlds/{world_id}/worldlines/{primary_id}/assets/{visible_id}/member-visible",
        b"visible-bytes",
        content_type="image/png",
    )
    with Session(engine) as session:
        visible_asset = session.get(MediaAsset, visible_id)
        assert visible_asset is not None
        visible_asset.storage_uri = stored.uri
        visible_asset.preview_uri = stored.uri
        visible_asset.thumbnail_uri = stored.uri
        session.commit()

    _authenticate_session_only(client, owner_token)
    missing_csrf = client.post(
        f"/worlds/{world_id}/media/assets",
        json={
            "asset_kind": "image",
            "asset_role": "reference_image",
            "source_kind": "manual_upload",
        },
    )

    _authenticate(client, member_token)
    member_list = client.get(f"/worlds/{world_id}/media/assets")
    member_search = client.get(f"/worlds/{world_id}/media/assets/search")
    member_get_visible = client.get(f"/worlds/{world_id}/media/assets/{visible_id}")
    member_private_contexts = client.get(
        f"/worlds/{world_id}/media/assets/{private_id}/contexts"
    )
    member_private_references = client.get(
        f"/worlds/{world_id}/media/assets/{private_id}/references"
    )
    member_private_lineage = client.get(
        f"/worlds/{world_id}/media/assets/{private_id}/lineage"
    )
    member_create = client.post(
        f"/worlds/{world_id}/media/assets",
        json={
            "asset_kind": "image",
            "asset_role": "reference_image",
            "source_kind": "manual_upload",
        },
    )

    _authenticate(client, owner_token)
    admin_get_visible = client.get(f"/worlds/{world_id}/media/assets/{visible_id}")

    _authenticate(client, stranger_token)
    stranger_list = client.get(f"/worlds/{world_id}/media/assets")

    assert stranger_id
    assert missing_csrf.status_code == 403
    assert member_list.status_code == 200
    assert [asset["id"] for asset in member_list.json()] == [str(visible_id)]
    assert member_list.json()[0]["storage_uri"] is None
    assert member_list.json()[0]["preview_uri"] is None
    assert member_list.json()[0]["thumbnail_uri"] is None
    assert member_search.status_code == 200
    assert member_search.json()["assets"][0]["storage_uri"] is None
    assert member_search.json()["assets"][0]["preview_uri"] is None
    assert member_search.json()["assets"][0]["thumbnail_uri"] is None
    assert member_get_visible.status_code == 200
    assert member_get_visible.json()["storage_uri"] is None
    assert member_get_visible.json()["preview_uri"] is None
    assert member_get_visible.json()["thumbnail_uri"] is None
    assert admin_get_visible.status_code == 200
    assert admin_get_visible.json()["storage_uri"] == stored.uri
    assert admin_get_visible.json()["preview_uri"] == stored.uri
    assert admin_get_visible.json()["thumbnail_uri"] == stored.uri
    assert member_private_contexts.status_code == 404
    assert member_private_references.status_code == 404
    assert member_private_lineage.status_code == 404
    assert member_create.status_code == 403
    assert stranger_list.status_code == 404


def test_media_api_rejects_narrative_artifact_and_cross_worldline_contexts() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    primary_id, fork_id = _seed_worldlines(engine, world_id)
    conversation_id, _turn_id = _seed_conversation(engine, world_id, primary_id)
    artifact_id = _seed_artifact(engine, world_id)
    asset_id = _seed_asset(engine, world_id, primary_id, visibility="world_member")

    _authenticate(client, owner_token)
    cross_worldline = client.post(
        f"/worlds/{world_id}/media/assets/{asset_id}/contexts",
        json={"worldline_id": str(fork_id), "conversation_id": str(conversation_id)},
    )
    narrative_context = client.post(
        f"/worlds/{world_id}/media/assets/{asset_id}/contexts",
        json={"worldline_id": str(primary_id), "narrative_artifact_id": str(artifact_id)},
    )

    assert cross_worldline.status_code == 422
    assert "worldline" in cross_worldline.json()["detail"]
    assert narrative_context.status_code == 422
    assert "narrative artifact media contexts" in narrative_context.json()["detail"]


def test_media_api_member_can_read_visible_fork_asset_references() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    _primary_id, fork_id = _seed_worldlines(engine, world_id)
    source_id = _seed_asset(engine, world_id, fork_id, visibility="world_member")
    output_id = _seed_asset(engine, world_id, fork_id, visibility="world_member")

    _authenticate(client, owner_token)
    created_input = client.post(
        f"/worlds/{world_id}/media/assets/{output_id}/inputs",
        json={
            "worldline_id": str(fork_id),
            "input_asset_id": str(source_id),
            "input_role": "reference",
        },
    )

    _authenticate(client, member_token)
    lineage = client.get(f"/worlds/{world_id}/media/assets/{output_id}/lineage")
    references = client.get(f"/worlds/{world_id}/media/assets/{source_id}/references")

    assert created_input.status_code == 201
    assert lineage.status_code == 200
    assert lineage.json()["inputs"][0]["input_asset_id"] == str(source_id)
    assert references.status_code == 200
    assert references.json()["input_count"] == 1


def test_media_api_upload_download_objects_and_restricted_visibility() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    platform_id, platform_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    primary_id, _fork_id = _seed_worldlines(engine, world_id)

    _authenticate(client, owner_token)
    uploaded = client.post(
        f"/worlds/{world_id}/media/assets/upload",
        data={
            "worldline_id": str(primary_id),
            "asset_kind": "image",
            "asset_role": "reference_image",
            "visibility": "world_admin",
            "title": "Upload",
            "metadata_json": '{"source":"api"}',
        },
        files={"file": ("../unsafe.png", b"image-bytes", "image/png")},
    )
    asset_id = uploaded.json()["asset"]["id"]
    object_id = uploaded.json()["object"]["id"]
    objects = client.get(f"/worlds/{world_id}/media/assets/{asset_id}/objects")
    download = client.get(f"/worlds/{world_id}/media/objects/{object_id}/download")
    hidden_asset_id = _seed_asset(engine, world_id, primary_id, visibility="hidden")
    hidden_object_id = _seed_object(
        engine,
        client.media_storage,
        world_id,
        primary_id,
        hidden_asset_id,
    )
    owner_hidden_download = client.get(
        f"/worlds/{world_id}/media/objects/{hidden_object_id}/download"
    )

    _authenticate(client, member_token)
    member_download = client.get(f"/worlds/{world_id}/media/objects/{object_id}/download")

    _authenticate(client, platform_token)
    platform_hidden_download = client.get(
        f"/worlds/{world_id}/media/objects/{hidden_object_id}/download"
    )

    assert platform_id
    assert uploaded.status_code == 201
    assert uploaded.json()["asset"]["status"] == "available"
    assert uploaded.json()["asset"]["storage_uri"] == uploaded.json()["object"]["storage_uri"]
    assert uploaded.json()["asset"]["metadata"] == {"source": "api"}
    assert uploaded.json()["object"]["size_bytes"] == len(b"image-bytes")
    assert ".." not in uploaded.json()["object"]["storage_uri"]
    assert objects.status_code == 200
    assert [item["id"] for item in objects.json()] == [object_id]
    assert download.status_code == 200
    assert download.content == b"image-bytes"
    assert download.headers["content-type"].startswith("image/png")
    assert member_download.status_code == 403
    assert owner_hidden_download.status_code == 404
    assert platform_hidden_download.status_code == 200
    assert platform_hidden_download.content == b"hidden-bytes"


def test_media_api_generic_references_turn_media_and_job_patch() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    primary_id, _fork_id = _seed_worldlines(engine, world_id)
    conversation_id, turn_id = _seed_conversation(engine, world_id, primary_id)
    event_id = _seed_event(engine, world_id)
    asset_id = _seed_asset(engine, world_id, primary_id, visibility="world_admin")
    legacy_asset_id = _seed_asset(engine, world_id, primary_id, visibility="world_admin")
    _seed_context(engine, world_id, primary_id, legacy_asset_id, conversation_id, turn_id)

    _authenticate(client, owner_token)
    reference = client.post(
        f"/worlds/{world_id}/media/references",
        json={
            "worldline_id": str(primary_id),
            "asset_id": str(asset_id),
            "ref_kind": "world_event",
            "ref_id": str(event_id),
            "ref_role": "evidence",
        },
    )
    reference_id = reference.json()["id"]
    listed_refs = client.get(
        f"/worlds/{world_id}/media/references",
        params={"worldline_id": str(primary_id), "ref_kind": "world_event"},
    )
    turn_ref = client.post(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/media",
        json={
            "worldline_id": str(primary_id),
            "asset_id": str(asset_id),
            "attachment_role": "attachment",
        },
    )
    turn_media = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/media"
    )
    job = client.post(
        f"/worlds/{world_id}/media/jobs",
        json={
            "worldline_id": str(primary_id),
            "job_kind": "thumbnail",
            "priority": 120,
            "provider_kind": "local",
            "provider_config_json": {"preset": "small"},
            "request_json": {"asset_id": str(asset_id)},
        },
    )
    patched = client.patch(
        f"/worlds/{world_id}/media/jobs/{job.json()['id']}",
        json={
            "status": "running",
            "priority": 10,
            "result_json": {"started": True},
        },
    )
    filtered_jobs = client.get(
        f"/worlds/{world_id}/media/jobs",
        params={
            "worldline_id": str(primary_id),
            "job_kind": "thumbnail",
            "priority_max": 10,
        },
    )
    cancelled = client.post(f"/worlds/{world_id}/media/jobs/{job.json()['id']}/cancel")
    cancel_again = client.post(f"/worlds/{world_id}/media/jobs/{job.json()['id']}/cancel")
    deleted_ref = client.delete(f"/worlds/{world_id}/media/references/{reference_id}")
    listed_after_delete = client.get(
        f"/worlds/{world_id}/media/references",
        params={"worldline_id": str(primary_id), "ref_kind": "world_event"},
    )

    assert reference.status_code == 201
    assert reference.json()["ref_role"] == "evidence"
    assert listed_refs.status_code == 200
    assert [item["id"] for item in listed_refs.json()] == [reference_id]
    assert turn_ref.status_code == 201
    assert turn_media.status_code == 200
    assert {item["asset"]["id"] for item in turn_media.json()} == {
        str(asset_id),
        str(legacy_asset_id),
    }
    assert job.status_code == 201
    assert patched.status_code == 200
    assert patched.json()["status"] == "running"
    assert patched.json()["priority"] == 10
    assert filtered_jobs.status_code == 200
    assert [item["id"] for item in filtered_jobs.json()] == [job.json()["id"]]
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancel_again.status_code == 409
    assert deleted_ref.status_code == 204
    assert listed_after_delete.json() == []


def test_media_api_rejects_cross_worldline_references_and_bad_upload_metadata() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    primary_id, fork_id = _seed_worldlines(engine, world_id)
    conversation_id, _turn_id = _seed_conversation(engine, world_id, primary_id)
    asset_id = _seed_asset(engine, world_id, primary_id, visibility="world_admin")

    _authenticate(client, owner_token)
    bad_metadata = client.post(
        f"/worlds/{world_id}/media/assets/upload",
        data={
            "worldline_id": str(primary_id),
            "asset_kind": "image",
            "asset_role": "reference_image",
            "metadata_json": "[1, 2, 3]",
        },
        files={"file": ("image.png", b"image-bytes", "image/png")},
    )
    cross_worldline_reference = client.post(
        f"/worlds/{world_id}/media/references",
        json={
            "worldline_id": str(fork_id),
            "asset_id": str(asset_id),
            "ref_kind": "conversation_session",
            "ref_id": str(conversation_id),
        },
    )

    assert bad_metadata.status_code == 422
    assert "metadata_json" in bad_metadata.json()["detail"]
    assert cross_worldline_reference.status_code == 422
    assert "asset must belong" in cross_worldline_reference.json()["detail"]


class _MediaApiClient(TestClient):
    media_storage: LocalMediaObjectStorage


def _client_with_database() -> tuple[_MediaApiClient, Engine]:
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
    app.dependency_overrides[_media_storage] = lambda: storage
    app.state._media_storage_tmp = storage_tmp
    client = _MediaApiClient(app)
    client.media_storage = storage
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
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, WorldEventModel.__table__),
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


def _seed_agent(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key="agent",
                display_name="Agent",
                kind="role_agent",
            ),
        )
        session.commit()
    return agent_id


def _seed_conversation(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> tuple[uuid.UUID, uuid.UUID]:
    conversation_id = uuid.uuid4()
    turn_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            ConversationSession(
                id=conversation_id,
                world_id=world_id,
                worldline_id=worldline_id,
                session_key=f"session-{conversation_id.hex[:8]}",
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
                input_text="input",
                output_text="output",
                status="succeeded",
            ),
        )
        session.commit()
    return conversation_id, turn_id


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


def _seed_asset(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
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


def _seed_object(
    engine: Engine,
    storage: LocalMediaObjectStorage,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    asset_id: uuid.UUID,
) -> uuid.UUID:
    object_id = uuid.uuid4()
    stored = storage.write_bytes(
        f"worlds/{world_id}/worldlines/{worldline_id}/assets/{asset_id}/original-hidden",
        b"hidden-bytes",
        content_type="application/octet-stream",
    )
    with Session(engine) as session:
        session.add(
            MediaObject(
                id=object_id,
                asset_id=asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                object_role="original",
                storage_uri=stored.uri,
                filename="hidden.bin",
                mime_type="application/octet-stream",
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
                metadata_json={},
            ),
        )
        session.commit()
    return object_id


def _seed_context(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    asset_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
) -> uuid.UUID:
    context_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            MediaAssetContext(
                id=context_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_id=asset_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                context_role="attachment",
                metadata_json={},
            )
        )
        session.commit()
    return context_id


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


def _authenticate(client: TestClient, token: str) -> None:
    _authenticate_session_only(client, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _authenticate_session_only(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
