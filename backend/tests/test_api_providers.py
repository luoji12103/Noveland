from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from fastapi.testclient import TestClient
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
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
from noveland.providers.models import (
    ProviderCapability,
    ProviderHealthCheck,
    ProviderIntegration,
)
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.services.api.providers import _media_storage
from noveland.worlds.models import World, Worldline, WorldMembership
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_providers_api_crud_health_and_fake_invocation() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    world_id = _seed_world(engine, admin_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, admin_token)

    created = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "image_generation",
            "adapter_kind": "fake",
            "provider_key": "fake-image",
            "display_name": "Fake Image",
            "auth_ref": "secret:fake",
            "capabilities": [
                {
                    "capability_key": "supports_image_generation",
                    "capability_json": {"value": True},
                }
            ],
        },
    )
    provider_id = created.json()["id"]
    listed = client.get(f"/worlds/{world_id}/providers", params={"adapter_kind": "fake"})
    capabilities = client.get(f"/worlds/{world_id}/providers/{provider_id}/capabilities")
    health = client.post(f"/worlds/{world_id}/providers/{provider_id}/health-check")
    invocation = client.post(
        f"/worlds/{world_id}/providers/test-invocation",
        json={
            "worldline_id": str(worldline_id),
            "provider_id": provider_id,
            "input_text": "draw this",
        },
    )

    assert created.status_code == 201
    assert created.json()["auth_ref_configured"] is True
    assert "auth_ref" not in created.json()
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [provider_id]
    assert capabilities.status_code == 200
    assert capabilities.json()[0]["capability_key"] == "supports_image_generation"
    assert health.status_code == 201
    assert health.json()["status"] == "healthy"
    assert invocation.status_code == 201
    assert invocation.json()["invocation"]["media_asset_id"] is not None
    assert invocation.json()["output_objects"][0]["mime_type"] == "image/png"

    with Session(engine) as session:
        assert session.scalars(select(ModelInvocation)).one().media_asset_id is not None
        assert session.scalars(select(MediaObject)).one().storage_uri.startswith("media://")


def test_providers_api_acl_and_global_platform_admin() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    platform_id, platform_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    world_id = _seed_world(engine, admin_id)
    _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    member_create = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "text_generation",
            "adapter_kind": "fake",
            "provider_key": "member-fake",
            "display_name": "Member Fake",
        },
    )

    _authenticate(client, admin_token)
    admin_global = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "global",
            "provider_kind": "text_generation",
            "adapter_kind": "fake",
            "provider_key": "global-fake",
            "display_name": "Global Fake",
        },
    )

    _authenticate(client, platform_token)
    platform_global = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "global",
            "provider_kind": "text_generation",
            "adapter_kind": "fake",
            "provider_key": "global-fake",
            "display_name": "Global Fake",
            "visibility": "developer_only",
        },
    )

    assert platform_id
    assert member_create.status_code == 403
    assert admin_global.status_code == 403
    assert platform_global.status_code == 201


class _ProviderApiClient(TestClient):
    media_storage: LocalMediaObjectStorage


def _client_with_database() -> tuple[_ProviderApiClient, Engine]:
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
    app.state._provider_media_storage_tmp = storage_tmp
    client = _ProviderApiClient(app)
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


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})
