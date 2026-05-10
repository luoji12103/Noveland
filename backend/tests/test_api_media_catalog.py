from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi.testclient import TestClient
from noveland.agents.models import Agent
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.events.models import WorldEventModel
from noveland.media.models import (
    MediaAsset,
    MediaAssetCollection,
    MediaAssetCollectionItem,
    MediaAssetContext,
    MediaAssetInput,
    MediaAssetTag,
    MediaJob,
)
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import World, Worldline, WorldMembership
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_media_catalog_api_search_route_tags_collections_and_visibility() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    primary_id = _seed_worldline(engine, world_id)
    agent_id = _seed_agent(engine, world_id)
    visible_id = _seed_asset(
        engine,
        world_id,
        primary_id,
        visibility="world_member",
        title="Shy sprite",
        description="Classroom expression",
    )
    private_id = _seed_asset(
        engine,
        world_id,
        primary_id,
        visibility="world_member",
        title="Hidden match",
        description="Private tag only",
    )

    _authenticate(client, owner_token)
    visible_tag = client.post(
        f"/worlds/{world_id}/media/assets/{visible_id}/tags",
        json={
            "worldline_id": str(primary_id),
            "tag_type": "Emotion",
            "tag_key": "Mood",
            "tag_value": "shy:soft",
            "visibility": "world_member",
        },
    )
    hidden_tag = client.post(
        f"/worlds/{world_id}/media/assets/{private_id}/tags",
        json={
            "worldline_id": str(primary_id),
            "tag_type": "emotion",
            "tag_key": "mood",
            "tag_value": "secret",
            "visibility": "hidden",
        },
    )
    collection = client.post(
        f"/worlds/{world_id}/media/collections",
        json={
            "worldline_id": str(primary_id),
            "collection_kind": "Sprite_Set",
            "title": "Sprite set",
            "owner_agent_id": str(agent_id),
            "visibility": "world_member",
        },
    )
    item = client.post(
        f"/worlds/{world_id}/media/collections/{collection.json()['id']}/items",
        json={
            "worldline_id": str(primary_id),
            "asset_id": str(visible_id),
            "role": "primary",
        },
    )

    _authenticate(client, member_token)
    search = client.get(
        f"/worlds/{world_id}/media/assets/search",
        params=[
            ("worldline_id", str(primary_id)),
            ("contains_text", " shy "),
            ("collection_id", collection.json()["id"]),
            ("tag", "emotion:mood:shy:soft"),
        ],
    )
    hidden_search = client.get(
        f"/worlds/{world_id}/media/assets/search",
        params=[("worldline_id", str(primary_id)), ("tag", "emotion:mood:secret")],
    )
    malformed = client.get(
        f"/worlds/{world_id}/media/assets/search",
        params=[("worldline_id", str(primary_id)), ("tag", "emotion:mood")],
    )
    empty_text = client.get(
        f"/worlds/{world_id}/media/assets/search",
        params={"worldline_id": str(primary_id), "contains_text": "   "},
    )
    refs = client.get(f"/worlds/{world_id}/media/assets/{visible_id}/references")
    items = client.get(f"/worlds/{world_id}/media/collections/{collection.json()['id']}/items")

    assert visible_tag.status_code == 201
    assert visible_tag.json()["tag_type"] == "emotion"
    assert visible_tag.json()["tag_value"] == "shy:soft"
    assert hidden_tag.status_code == 201
    assert collection.status_code == 201
    assert collection.json()["collection_kind"] == "sprite_set"
    assert item.status_code == 201
    assert search.status_code == 200
    assert [asset["id"] for asset in search.json()["assets"]] == [str(visible_id)]
    assert hidden_search.status_code == 200
    assert hidden_search.json()["assets"] == []
    assert malformed.status_code == 422
    assert empty_text.status_code == 422
    assert refs.status_code == 200
    assert refs.json()["tag_count"] == 1
    assert refs.json()["collection_count"] == 1
    assert items.status_code == 200
    assert [row["asset_id"] for row in items.json()] == [str(visible_id)]


def test_media_catalog_api_member_cannot_infer_private_collections() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    primary_id = _seed_worldline(engine, world_id)
    asset_id = _seed_asset(engine, world_id, primary_id, visibility="world_member")

    _authenticate(client, owner_token)
    private_collection = client.post(
        f"/worlds/{world_id}/media/collections",
        json={
            "worldline_id": str(primary_id),
            "collection_kind": "secret_set",
            "title": "Secret set",
            "visibility": "private",
        },
    )
    client.post(
        f"/worlds/{world_id}/media/collections/{private_collection.json()['id']}/items",
        json={"worldline_id": str(primary_id), "asset_id": str(asset_id)},
    )

    _authenticate(client, member_token)
    collection_get = client.get(
        f"/worlds/{world_id}/media/collections/{private_collection.json()['id']}"
    )
    items = client.get(
        f"/worlds/{world_id}/media/collections/{private_collection.json()['id']}/items"
    )
    search = client.get(
        f"/worlds/{world_id}/media/assets/search",
        params={"worldline_id": str(primary_id), "collection_id": private_collection.json()["id"]},
    )
    refs = client.get(f"/worlds/{world_id}/media/assets/{asset_id}/references")

    assert collection_get.status_code == 404
    assert items.status_code == 404
    assert search.status_code == 200
    assert search.json()["assets"] == []
    assert refs.status_code == 200
    assert refs.json()["collection_count"] == 0
    assert refs.json()["collections"] == []


def _client_with_database() -> tuple[TestClient, Engine]:
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
    return TestClient(app), engine


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
        cast(Table, MediaAssetContext.__table__),
        cast(Table, MediaAssetInput.__table__),
        cast(Table, MediaAssetTag.__table__),
        cast(Table, MediaAssetCollection.__table__),
        cast(Table, MediaAssetCollectionItem.__table__),
    ):
        table.create(engine)


def _seed_user(engine: Engine, email: str) -> tuple[uuid.UUID, str]:
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
            )
        )
        session.commit()
    return agent_id


def _seed_asset(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    visibility: str,
    title: str | None = None,
    description: str | None = None,
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
                title=title,
                description=description,
                created_by_actor_ref="test",
                metadata_json={"search": "metadata must not match"},
            )
        )
        session.commit()
    return asset_id


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})
