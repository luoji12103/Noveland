from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

from fastapi.testclient import TestClient
from noveland.agents.models import Agent
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.conversations.models import ConversationSession, ConversationTurn
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
from noveland.providers.models import (
    ProviderBudgetPolicy,
    ProviderCapability,
    ProviderHealthCheck,
    ProviderIntegration,
)
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.services.api.visual import _visual_storage
from noveland.visual.models import (
    CharacterSpriteSet,
    CharacterSpriteVariant,
    SceneBackgroundProfile,
)
from noveland.worlds.models import Scene, World, Worldline, WorldMembership
from noveland.worlds.worldlines import ensure_primary_worldline
from PIL import Image
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_visual_api_sprite_background_compose_acl_and_safe_responses() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    platform_id, platform_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    world_id = _seed_world(engine, admin_id)
    worldline_id = _seed_worldline(engine, world_id)
    agent_id, scene_id = _seed_agent_and_scene(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    happy_asset = _seed_image_asset(
        engine,
        client.visual_storage,
        world_id,
        worldline_id,
        _png((255, 0, 0, 255), 2, 2),
        role=MediaAssetRole.CHARACTER_SPRITE,
    )
    neutral_asset = _seed_image_asset(
        engine,
        client.visual_storage,
        world_id,
        worldline_id,
        _png((0, 255, 0, 255), 2, 2),
        role=MediaAssetRole.CHARACTER_SPRITE,
    )
    background_asset = _seed_image_asset(
        engine,
        client.visual_storage,
        world_id,
        worldline_id,
        _png((0, 0, 255, 255), 2, 2),
        role=MediaAssetRole.SCENE_BACKGROUND,
    )

    _authenticate(client, member_token)
    member_create = client.post(
        f"/worlds/{world_id}/visual/sprite-sets",
        json={
            "worldline_id": str(worldline_id),
            "agent_id": str(agent_id),
            "style_key": "default",
            "display_name": "Default",
        },
    )

    _authenticate(client, admin_token)
    hidden_create = client.post(
        f"/worlds/{world_id}/visual/sprite-sets",
        json={
            "worldline_id": str(worldline_id),
            "agent_id": str(agent_id),
            "style_key": "hidden",
            "display_name": "Hidden",
            "visibility": "developer_only",
        },
    )
    sprite_set = client.post(
        f"/worlds/{world_id}/visual/sprite-sets",
        json={
            "worldline_id": str(worldline_id),
            "agent_id": str(agent_id),
            "style_key": "default",
            "display_name": "Default",
        },
    )
    sprite_set_id = sprite_set.json()["id"]
    variant = client.post(
        f"/worlds/{world_id}/visual/sprite-sets/{sprite_set_id}/variants",
        json={
            "worldline_id": str(worldline_id),
            "asset_id": str(happy_asset),
            "expression_key": "happy",
            "pose_key": "standing",
            "priority": 10,
        },
    )
    neutral = client.post(
        f"/worlds/{world_id}/visual/sprite-sets/{sprite_set_id}/variants",
        json={
            "worldline_id": str(worldline_id),
            "asset_id": str(neutral_asset),
            "expression_key": "neutral",
            "pose_key": "standing",
            "is_default": True,
            "priority": 20,
        },
    )
    resolved = client.post(
        f"/worlds/{world_id}/visual/resolve-sprite",
        json={
            "worldline_id": str(worldline_id),
            "agent_id": str(agent_id),
            "expression_key": "angry",
            "pose_key": "standing",
        },
    )
    background = client.post(
        f"/worlds/{world_id}/visual/backgrounds",
        json={
            "worldline_id": str(worldline_id),
            "scene_id": str(scene_id),
            "location_key": "classroom",
            "asset_id": str(background_asset),
            "is_default": True,
        },
    )
    background_resolved = client.post(
        f"/worlds/{world_id}/visual/resolve-background",
        json={
            "worldline_id": str(worldline_id),
            "scene_id": str(scene_id),
            "location_key": "classroom",
            "time_of_day": "night",
        },
    )
    composed = client.post(
        f"/worlds/{world_id}/visual/compose-scene",
        json={
            "worldline_id": str(worldline_id),
            "background_asset_id": str(background_asset),
            "layers": [{"asset_id": str(happy_asset), "x": 0, "y": 0, "z_index": 1}],
        },
    )
    listed = client.get(
        f"/worlds/{world_id}/visual/sprite-sets",
        params={"worldline_id": str(worldline_id)},
    )

    _authenticate(client, platform_token)
    platform_hidden = client.post(
        f"/worlds/{world_id}/visual/sprite-sets",
        json={
            "worldline_id": str(worldline_id),
            "agent_id": str(agent_id),
            "style_key": "platform-hidden",
            "display_name": "Platform Hidden",
            "visibility": "developer_only",
        },
    )
    platform_listed = client.get(
        f"/worlds/{world_id}/visual/sprite-sets",
        params={"worldline_id": str(worldline_id)},
    )

    assert platform_id
    assert member_create.status_code == 403
    assert hidden_create.status_code == 403
    assert sprite_set.status_code == 201
    assert variant.status_code == 201
    assert neutral.status_code == 201
    assert resolved.status_code == 200
    assert resolved.json()["fallback_reason"] == "neutral_expression"
    assert resolved.json()["variant"]["asset_id"] == str(neutral_asset)
    assert "storage_uri" not in _json_text(resolved.json())
    assert background.status_code == 201
    assert background_resolved.status_code == 200
    assert background_resolved.json()["fallback_reason"] == "default_background"
    assert "storage_uri" not in _json_text(background_resolved.json())
    assert composed.status_code == 201
    assert composed.json()["output_asset"]["source_kind"] == "composed"
    assert "storage_uri" not in _json_text(composed.json())
    assert listed.status_code == 200
    assert [item["style_key"] for item in listed.json()] == ["default"]
    assert platform_hidden.status_code == 201
    assert {item["style_key"] for item in platform_listed.json()} == {
        "default",
        "platform-hidden",
    }

    with Session(engine) as session:
        assert session.scalars(select(ModelInvocation)).all() == []
        assert len(session.scalars(select(MediaJob)).all()) == 1
        assert session.scalars(select(WorldEventModel)).all() == []


def test_visual_api_rejects_cross_worldline_asset() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    world_id = _seed_world(engine, admin_id)
    worldline_id = _seed_worldline(engine, world_id)
    fork_id = _seed_fork(engine, world_id, worldline_id)
    agent_id, _scene_id = _seed_agent_and_scene(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    fork_asset = _seed_image_asset(
        engine,
        client.visual_storage,
        world_id,
        fork_id,
        _png((255, 0, 0, 255), 2, 2),
        role=MediaAssetRole.CHARACTER_SPRITE,
    )

    _authenticate(client, admin_token)
    sprite_set = client.post(
        f"/worlds/{world_id}/visual/sprite-sets",
        json={
            "worldline_id": str(worldline_id),
            "agent_id": str(agent_id),
            "style_key": "default",
            "display_name": "Default",
        },
    )
    response = client.post(
        f"/worlds/{world_id}/visual/sprite-sets/{sprite_set.json()['id']}/variants",
        json={
            "worldline_id": str(worldline_id),
            "asset_id": str(fork_asset),
            "expression_key": "happy",
        },
    )

    assert sprite_set.status_code == 201
    assert response.status_code == 422
    assert "worldline" in response.json()["detail"]


class _VisualApiClient(TestClient):
    visual_storage: LocalMediaObjectStorage


def _client_with_database() -> tuple[_VisualApiClient, Engine]:
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
    app.dependency_overrides[_visual_storage] = lambda: storage
    app.state._visual_storage_tmp = storage_tmp
    client = _VisualApiClient(app)
    client.visual_storage = storage
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
        cast(Table, Scene.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, MemoryWriteJob.__table__),
        cast(Table, ProviderIntegration.__table__),
        cast(Table, ProviderCapability.__table__),
        cast(Table, ProviderHealthCheck.__table__),
        cast(Table, ProviderBudgetPolicy.__table__),
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


def _seed_user(
    engine: Engine,
    email: str,
    *,
    platform_admin: bool = False,
) -> tuple[uuid.UUID, str]:
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
            )
        )
        if platform_admin:
            session.add(
                PlatformRoleAssignment(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    role=AuthRole.PLATFORM_ADMIN.value,
                    assigned_at=now,
                )
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
            )
        )
        session.commit()
    return world_id


def _seed_worldline(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        primary = ensure_primary_worldline(session, world_id)
        session.commit()
        return primary.id


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


def _seed_agent_and_scene(engine: Engine, world_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    agent_id = uuid.uuid4()
    scene_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key=f"agent-{agent_id.hex[:8]}",
                display_name="Agent",
                kind="role_agent",
            )
        )
        session.add(
            Scene(
                id=scene_id,
                world_id=world_id,
                scene_key=f"scene-{scene_id.hex[:8]}",
                name="Scene",
            )
        )
        session.commit()
    return agent_id, scene_id


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
            )
        )
        session.commit()


def _seed_image_asset(
    engine: Engine,
    storage: LocalMediaObjectStorage,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    data: bytes,
    *,
    role: MediaAssetRole,
) -> uuid.UUID:
    with Session(engine) as session:
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
        session.commit()
        return asset.id


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _png(color: tuple[int, int, int, int], width: int, height: int) -> bytes:
    image = Image.new("RGBA", (width, height), color)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _json_text(value: Any) -> str:
    return str(value)
