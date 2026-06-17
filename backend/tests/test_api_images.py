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
from noveland.conversations.models import ConversationSession, ConversationTurn
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
from noveland.services.api.images import _image_storage
from noveland.worlds.models import World, Worldline, WorldMembership
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_images_api_generate_compose_and_acl() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, admin_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    provider_id = _seed_provider(engine, world_id)

    _authenticate(client, member_token)
    member_generate = client.post(
        f"/worlds/{world_id}/images/generate",
        json={
            "worldline_id": str(worldline_id),
            "provider_id": str(provider_id),
            "prompt": "draw",
        },
    )

    _authenticate(client, admin_token)
    generated = client.post(
        f"/worlds/{world_id}/images/generate",
        json={
            "worldline_id": str(worldline_id),
            "provider_id": str(provider_id),
            "prompt": "draw",
            "asset_role": "event_cg",
        },
    )
    job_id = generated.json()["media_job"]["id"]
    job = client.get(f"/worlds/{world_id}/images/jobs/{job_id}")
    asset_id = generated.json()["output_asset"]["id"]
    composed = client.post(
        f"/worlds/{world_id}/images/compose",
        json={
            "worldline_id": str(worldline_id),
            "background_asset_id": asset_id,
            "layers": [{"asset_id": asset_id, "x": 0, "y": 0, "z_index": 1}],
        },
    )

    assert member_generate.status_code == 403
    assert generated.status_code == 201
    assert generated.json()["model_invocation_id"] is not None
    assert generated.json()["output_asset"]["asset_role"] == "event_cg"
    assert generated.json()["output_objects"][0]["mime_type"] == "image/png"
    assert job.status_code == 200
    assert job.json()["status"] == "succeeded"
    assert composed.status_code == 201
    assert composed.json()["model_invocation_id"] is None
    assert composed.json()["output_asset"]["source_kind"] == "composed"

    with Session(engine) as session:
        assert session.scalars(select(ModelInvocation)).one().media_asset_id == uuid.UUID(asset_id)


def test_images_api_rejects_restricted_provider_execution_for_world_admin() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    platform_id, _platform_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    world_id = _seed_world(engine, admin_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, platform_id, AuthRole.WORLD_ADMIN)
    provider_id = _seed_provider(
        engine,
        world_id,
        scope_kind="global",
        visibility="developer_only",
        provider_key="platform-image",
    )

    _authenticate(client, admin_token)
    hidden_detail = client.get(f"/worlds/{world_id}/providers/{provider_id}")
    generated = client.post(
        f"/worlds/{world_id}/images/generate",
        json={
            "worldline_id": str(worldline_id),
            "provider_id": str(provider_id),
            "prompt": "draw restricted provider",
        },
    )

    assert hidden_detail.status_code == 404
    assert generated.status_code == 422
    with Session(engine) as session:
        assert session.scalars(select(MediaJob)).all() == []
        assert session.scalars(select(MediaAsset)).all() == []
        assert session.scalars(select(ModelInvocation)).all() == []
        assert session.scalars(select(PromptSnapshot)).all() == []


def test_images_api_rejects_transparency_without_capability() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    world_id = _seed_world(engine, admin_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    provider_id = _seed_provider(engine, world_id)

    _authenticate(client, admin_token)
    response = client.post(
        f"/worlds/{world_id}/images/generate",
        json={
            "worldline_id": str(worldline_id),
            "provider_id": str(provider_id),
            "prompt": "transparent",
            "transparent_background": "require",
        },
    )

    assert response.status_code == 422
    assert "transparent background" in response.json()["detail"]


class _ImagesApiClient(TestClient):
    image_storage: LocalMediaObjectStorage


def _client_with_database() -> tuple[_ImagesApiClient, Engine]:
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
    app.dependency_overrides[_image_storage] = lambda: storage
    app.state._image_storage_tmp = storage_tmp
    client = _ImagesApiClient(app)
    client.image_storage = storage
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


def _seed_provider(
    engine: Engine,
    world_id: uuid.UUID,
    *,
    scope_kind: str = "world",
    visibility: str = "world_admin",
    provider_key: str = "fake-image",
) -> uuid.UUID:
    provider_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            ProviderIntegration(
                id=provider_id,
                world_id=None if scope_kind == "global" else world_id,
                scope_kind=scope_kind,
                scope_key="global" if scope_kind == "global" else f"world:{world_id}",
                provider_kind="image_generation",
                adapter_kind="fake",
                provider_key=provider_key,
                display_name="Fake Image",
                config_json={},
                default_params_json={},
                status="active",
                visibility=visibility,
            )
        )
        session.add(
            ProviderCapability(
                id=uuid.uuid4(),
                provider_integration_id=provider_id,
                capability_key="supports_image_generation",
                capability_json={"value": True},
            )
        )
        session.commit()
    return provider_id


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})
