from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi.testclient import TestClient
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.core.database import import_model_modules
from noveland.events.models import WorldEventModel
from noveland.media.models import MediaAsset, MediaObject, MediaReference
from noveland.services.api.app import create_app
from noveland.services.api.csrf import SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import Scene, World, Worldline, WorldMembership
from sqlalchemy import Table, create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

FORBIDDEN_MARKERS = (
    "storage_uri",
    "media://",
    "file://",
    "s3://",
    "gs://",
    "base64",
    "raw_prompt",
    "raw_output",
    "prompt_snapshot",
    "api_key",
    "bearer_token",
    "authorization",
    "secret",
    "/tmp/",
    "/root/",
)


def test_world_package_export_preview_is_manifest_safe() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id, worldline_id = _seed_world_graph(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    _seed_media(engine, world_id, worldline_id)

    _authenticate(client, member_token)
    forbidden = client.post(
        f"/worlds/{world_id}/packages/export-preview",
        json={"worldline_id": str(worldline_id)},
    )

    _authenticate(client, owner_token)
    response = client.post(
        f"/worlds/{world_id}/packages/export-preview",
        json={"worldline_id": str(worldline_id), "package_key": "safe-package"},
    )

    assert forbidden.status_code == 403
    assert response.status_code == 200
    body = response.json()
    assert body["blocker_count"] == 0
    assert body["provider_execution"] is False
    assert body["world_event_writes"] is False
    assert body["manifest"]["metadata"]["package_key"] == "safe-package"
    assert body["manifest"]["worldlines"][0]["worldline_key"] == "primary"
    assert body["manifest"]["scenes"][0]["scene_key"] == "harbor"
    assert len(body["manifest"]["media"]) == 1
    assert body["manifest"]["media"][0]["objects"][0]["checksum_sha256"] == "a" * 64
    assert body["manifest"]["media"][0]["metadata"]["leaky_note"] == "[redacted]"
    _assert_no_forbidden_markers(body)


def test_world_package_import_preview_reports_blockers_without_mutation() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id, _worldline_id = _seed_world_graph(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    before_worlds = _count_rows(engine, World)
    before_media = _count_rows(engine, MediaAsset)
    before_events = _count_rows(engine, WorldEventModel)

    manifest = _valid_manifest()
    manifest["metadata"]["manifest_version"] = "v9"
    manifest["media"][0]["worldline_key"] = "missing"
    response = _authenticated_post(
        client,
        owner_token,
        f"/worlds/{world_id}/packages/import-preview",
        {"manifest": manifest},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["blocker_count"] == 2
    assert {issue["code"] for issue in body["issues"]} == {
        "unsupported_manifest_version",
        "unknown_worldline",
    }
    assert _count_rows(engine, World) == before_worlds
    assert _count_rows(engine, MediaAsset) == before_media
    assert _count_rows(engine, WorldEventModel) == before_events
    _assert_no_forbidden_markers(body)


def test_world_package_import_apply_creates_safe_records_only() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id, _worldline_id = _seed_world_graph(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    before_events = _count_rows(engine, WorldEventModel)
    manifest = _valid_manifest()

    preview = _authenticated_post(
        client,
        owner_token,
        f"/worlds/{world_id}/packages/import-preview",
        {"manifest": manifest},
    )
    apply = _authenticated_post(
        client,
        owner_token,
        f"/worlds/{world_id}/packages/import-apply",
        {"manifest": manifest, "slug": "imported-package", "name": "Imported Package"},
    )
    blocked_apply = _authenticated_post(
        client,
        owner_token,
        f"/worlds/{world_id}/packages/import-apply",
        {"manifest": {**manifest, "metadata": {**manifest["metadata"], "manifest_version": "bad"}}},
    )

    assert preview.status_code == 200
    assert preview.json()["blocker_count"] == 0
    assert apply.status_code == 200
    body = apply.json()
    assert body["applied"] is True
    assert body["provider_execution"] is False
    assert body["world_event_writes"] is False
    assert len(body["created_worldline_ids"]) == 1
    assert len(body["created_scene_ids"]) == 1
    assert len(body["created_media_asset_ids"]) == 1
    assert blocked_apply.status_code == 400
    assert _count_rows(engine, WorldEventModel) == before_events
    _assert_no_forbidden_markers(body)

    with Session(engine) as session:
        imported_world = session.get(World, uuid.UUID(body["created_world_id"]))
        assert imported_world is not None
        assert imported_world.slug == "imported-package"
        imported_asset = session.get(MediaAsset, uuid.UUID(body["created_media_asset_ids"][0]))
        assert imported_asset is not None
        assert imported_asset.storage_uri is None
        assert imported_asset.metadata_json["package_import_placeholder"] is True


def test_world_package_import_rejects_forbidden_manifest_values() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id, _worldline_id = _seed_world_graph(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    manifest = _valid_manifest()
    manifest["world"]["rules_config"] = {"storage_uri": "media://private-object"}

    response = _authenticated_post(
        client,
        owner_token,
        f"/worlds/{world_id}/packages/import-preview",
        {"manifest": manifest},
    )

    assert response.status_code == 422
    assert _count_rows(engine, World) == 1


def test_world_package_routes_do_not_replace_existing_worlds_router() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id, _worldline_id = _seed_world_graph(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, owner_token)
    response = client.get(f"/worlds/{world_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(world_id)
    assert "package" not in response.json()


def _client_with_database() -> tuple[TestClient, Engine]:
    import_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _create_required_tables(engine)

    def override_session() -> Iterator[Session]:
        session = Session(engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    return TestClient(app), engine


def _create_required_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, Scene.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, MediaObject.__table__),
        cast(Table, MediaReference.__table__),
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
        session.add(User(id=user_id, email=email, display_name=email.split("@")[0], is_active=True))
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


def _seed_world_graph(
    engine: Engine,
    owner_id: uuid.UUID,
    *,
    slug: str = "package-source",
) -> tuple[uuid.UUID, uuid.UUID]:
    world_id = uuid.uuid4()
    worldline_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=owner_id,
                slug=slug,
                name="Package Source",
                description="World for package tests",
                rules_config={"tone": "safe"},
                is_active=True,
            )
        )
        session.add(
            Worldline(
                id=worldline_id,
                world_id=world_id,
                worldline_key="primary",
                name="Primary",
                status="active",
                created_by_actor_ref="system:test",
                metadata_json={"branch": "main"},
            )
        )
        session.add(
            Scene(
                id=uuid.uuid4(),
                world_id=world_id,
                scene_key="harbor",
                name="Harbor",
                description="Safe harbor scene.",
                region_key="coast",
                location_tags=["outside"],
                opening_rules={"weather": "clear"},
                is_active=True,
            )
        )
        session.commit()
    return world_id, worldline_id


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


def _seed_media(engine: Engine, world_id: uuid.UUID, worldline_id: uuid.UUID) -> None:
    asset_id = uuid.uuid4()
    hidden_id = uuid.uuid4()
    object_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            MediaAsset(
                id=asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind="image",
                asset_role="scene_background",
                source_kind="manual_upload",
                status="available",
                visibility="reader_visible",
                storage_uri="media://internal-background",
                preview_uri="media://internal-preview",
                mime_type="image/png",
                size_bytes=12,
                checksum_sha256="a" * 64,
                created_by_actor_ref="test",
                title="Safe background",
                metadata_json={
                    "caption": "Safe",
                    "leaky_note": "storage_uri media://private",
                    "secret": "must not leak",
                },
            )
        )
        session.add(
            MediaObject(
                id=object_id,
                asset_id=asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                object_role="original",
                storage_uri="media://internal-background",
                filename="background.png",
                mime_type="image/png",
                size_bytes=12,
                checksum_sha256="a" * 64,
                width=100,
                height=100,
                metadata_json={"path": "/tmp/private"},
            )
        )
        session.add(
            MediaReference(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                asset_id=asset_id,
                ref_kind="scene",
                ref_id=uuid.uuid4(),
                ref_role="background",
                display_order=0,
                metadata_json={"storage_uri": "media://private"},
            )
        )
        session.add(
            MediaAsset(
                id=hidden_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind="image",
                asset_role="character_sprite",
                source_kind="manual_upload",
                status="available",
                visibility="developer_only",
                storage_uri="media://developer-only",
                mime_type="image/png",
                size_bytes=12,
                checksum_sha256="b" * 64,
                created_by_actor_ref="test",
                metadata_json={},
            )
        )
        session.commit()


def _valid_manifest() -> dict[str, Any]:
    return {
        "metadata": {
            "manifest_version": "v0.8.7",
            "package_key": "sample-package",
            "generated_at": "2026-05-16T00:00:00Z",
            "capabilities": ["world", "worldline", "scene", "media-manifest"],
        },
        "world": {
            "slug": "sample-package",
            "name": "Sample Package",
            "description": "Safe package.",
            "memory_plugin_identifier": "builtin.local_pgvector_memory",
            "memory_plugin_config": {},
            "world_rules_plugin_identifier": "builtin.default_world_rules",
            "world_rules_plugin_config": {},
            "rules_config": {"tone": "safe"},
            "is_active": True,
        },
        "worldlines": [
            {
                "worldline_key": "primary",
                "name": "Primary",
                "description": None,
                "status": "active",
                "metadata": {},
            }
        ],
        "scenes": [
            {
                "scene_key": "harbor",
                "name": "Harbor",
                "description": "Safe scene.",
                "region_key": "coast",
                "location_tags": ["outside"],
                "opening_rules": {},
                "is_active": True,
            }
        ],
        "media": [
            {
                "package_asset_key": "background",
                "worldline_key": "primary",
                "asset_kind": "image",
                "asset_role": "scene_background",
                "source_kind": "imported_original",
                "status": "registered",
                "visibility": "world_admin",
                "mime_type": "image/png",
                "size_bytes": 12,
                "checksum_sha256": "a" * 64,
                "title": "Background",
                "description": "Safe media placeholder.",
                "objects": [],
                "references": [
                    {
                        "ref_kind": "scene",
                        "ref_key": "harbor",
                        "ref_role": "background",
                        "display_order": 0,
                    }
                ],
                "metadata": {"rights": "test-fixture"},
            }
        ],
    }


def _authenticated_post(
    client: TestClient,
    token: str,
    path: str,
    payload: dict[str, Any],
) -> Any:
    _authenticate(client, token)
    return client.post(path, json=payload)


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)


def _count_rows(engine: Engine, model: type[Any]) -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count(model.id))) or 0


def _assert_no_forbidden_markers(value: object) -> None:
    serialized = json.dumps(value, sort_keys=True).lower()
    for marker in FORBIDDEN_MARKERS:
        assert marker not in serialized
