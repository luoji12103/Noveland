from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi.testclient import TestClient
from noveland.agents.models import Agent, AgentPersona
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.authoring.models import (
    AuthoringSourceAsset,
    AuthoringSourceBatch,
    AuthoringSourceFragment,
    AuthoringSourceTraceability,
)
from noveland.core.database import import_model_modules
from noveland.events.models import WorldEventModel
from noveland.media.models import MediaAsset, MediaObject, MediaReference
from noveland.memory.models import AgentMemoryItem
from noveland.providers.models import ProviderCapability, ProviderIntegration
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.speech.models import AgentVoiceProfileBinding, VoiceProfile
from noveland.visual.models import (
    CharacterSpriteSet,
    CharacterSpriteVariant,
    SceneBackgroundProfile,
)
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


def test_world_package_export_preview_includes_extended_safe_manifests() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id, worldline_id = _seed_world_graph(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    refs = _seed_extended_package_records(engine, world_id, worldline_id)

    response = _authenticated_post(
        client,
        owner_token,
        f"/worlds/{world_id}/packages/export-preview",
        {
            "worldline_id": str(worldline_id),
            "package_key": "normal-use-export",
            "public_sample": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["blocker_count"] == 0
    assert body["provider_manifest_count"] == 1
    assert body["persona_manifest_count"] == 1
    assert body["memory_manifest_count"] == 1
    assert body["visual_mapping_count"] == 2
    assert body["voice_mapping_count"] == 1
    assert body["source_traceability_count"] == 1
    assert "proprietary_source_excluded" in {issue["code"] for issue in body["issues"]}
    manifest = body["manifest"]
    assert manifest["providers"][0]["provider_key"] == "package-provider"
    assert manifest["providers"][0]["auth_ref_configured"] is True
    assert "auth_ref" not in manifest["providers"][0]
    assert manifest["providers"][0]["config"] == {"safe": True}
    assert manifest["personas"][0]["agent_key"] == "alice"
    assert manifest["memories"][0]["agent_key"] == "alice"
    assert {mapping["mapping_kind"] for mapping in manifest["visual_mappings"]} == {
        "character_sprite",
        "scene_background",
    }
    assert manifest["voice_mappings"][0]["provider_key"] == "package-provider"
    assert manifest["source_traceability"][0]["excluded_from_public_sample"] is True
    media_by_title = {asset["title"]: asset for asset in manifest["media"]}
    assert media_by_title["Galgame Sprite"]["objects"] == []
    assert media_by_title["Galgame Sprite"]["metadata"]["public_sample_policy"] == (
        "excluded_placeholder"
    )
    assert refs["hidden_asset_id"] not in json.dumps(manifest)
    assert body["provider_execution"] is False
    assert body["world_event_writes"] is False
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


def test_world_package_import_preview_reports_repeatable_duplicate_package_safely() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id, _worldline_id = _seed_world_graph(engine, owner_id, slug="source-world")
    _seed_world_graph(engine, owner_id, slug="imported-sample-package")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    before_worlds = _count_rows(engine, World)
    manifest = _valid_manifest()

    response = _authenticated_post(
        client,
        owner_token,
        f"/worlds/{world_id}/packages/import-preview",
        {"manifest": manifest},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["blocker_count"] == 0
    codes = {issue["code"] for issue in body["issues"]}
    assert "duplicate_import_target" in codes
    assert _count_rows(engine, World) == before_worlds
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
    _authenticate_without_csrf(client, owner_token)
    missing_csrf_apply = client.post(
        f"/worlds/{world_id}/packages/import-apply",
        json={"manifest": manifest, "slug": "missing-csrf", "name": "Missing CSRF"},
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
    assert missing_csrf_apply.status_code == 403
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


def test_world_package_import_apply_preserves_extended_manifests_as_safe_metadata() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id, _worldline_id = _seed_world_graph(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    manifest = _valid_manifest()
    manifest.update(_extended_manifest_sections())

    apply = _authenticated_post(
        client,
        owner_token,
        f"/worlds/{world_id}/packages/import-apply",
        {"manifest": manifest, "slug": "extended-import", "name": "Extended Import"},
    )

    assert apply.status_code == 200
    body = apply.json()
    assert body["applied"] is True
    assert body["provider_execution"] is False
    assert body["world_event_writes"] is False
    _assert_no_forbidden_markers(body)

    with Session(engine) as session:
        imported_world = session.get(World, uuid.UUID(body["created_world_id"]))
        assert imported_world is not None
        preserved = imported_world.rules_config["package_import_extended_manifests"]
        assert preserved["review_apply_required_for_specialized_records"] is True
        assert preserved["providers"][0]["provider_key"] == "safe-provider"
        assert preserved["personas"][0]["agent_key"] == "alice"
        assert preserved["memories"][0]["memory_key"] == "memory-alice"
        assert preserved["visual_mappings"][0]["package_asset_key"] == "background"
        assert preserved["voice_mappings"][0]["voice_profile_key"] == "alice-voice"
        assert preserved["source_traceability"][0]["excluded_from_public_sample"] is True
        assert _count_rows(engine, ProviderIntegration) == 0
        assert _count_rows(engine, AgentPersona) == 0
        assert _count_rows(engine, AgentMemoryItem) == 0


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
        cast(Table, Agent.__table__),
        cast(Table, AgentPersona.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, ProviderIntegration.__table__),
        cast(Table, ProviderCapability.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, MediaObject.__table__),
        cast(Table, MediaReference.__table__),
        cast(Table, AgentMemoryItem.__table__),
        cast(Table, CharacterSpriteSet.__table__),
        cast(Table, CharacterSpriteVariant.__table__),
        cast(Table, SceneBackgroundProfile.__table__),
        cast(Table, VoiceProfile.__table__),
        cast(Table, AgentVoiceProfileBinding.__table__),
        cast(Table, AuthoringSourceBatch.__table__),
        cast(Table, AuthoringSourceAsset.__table__),
        cast(Table, AuthoringSourceFragment.__table__),
        cast(Table, AuthoringSourceTraceability.__table__),
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


def _get_scene_id(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        scene_id = session.scalar(select(Scene.id).where(Scene.world_id == world_id))
        assert scene_id is not None
        return scene_id


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


def _seed_extended_package_records(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> dict[str, str]:
    scene_id = _get_scene_id(engine, world_id)
    provider_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    sprite_asset_id = uuid.uuid4()
    background_asset_id = uuid.uuid4()
    hidden_asset_id = uuid.uuid4()
    sprite_set_id = uuid.uuid4()
    voice_profile_id = uuid.uuid4()
    source_batch_id = uuid.uuid4()
    source_asset_id = uuid.uuid4()
    source_fragment_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            ProviderIntegration(
                id=provider_id,
                world_id=world_id,
                scope_kind="world",
                scope_key=f"world:{world_id}",
                provider_kind="text_generation",
                adapter_kind="fake",
                provider_key="package-provider",
                display_name="Package Provider",
                auth_ref="env:PACKAGE_PROVIDER_KEY",
                config_json={"safe": True, "api_key": "secret-value"},
                default_params_json={"temperature": 0.2},
                status="active",
                visibility="world_admin",
            )
        )
        session.add(
            ProviderCapability(
                id=uuid.uuid4(),
                provider_integration_id=provider_id,
                capability_key="supports_text_generation",
                capability_json={"mode": "chat"},
            )
        )
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key="alice",
                display_name="Alice",
                kind="role_agent",
                character_profile={"role": "lead", "raw_prompt": "hidden"},
                config={},
                is_enabled=True,
            )
        )
        session.add(
            AgentPersona(
                id=uuid.uuid4(),
                world_id=world_id,
                agent_id=agent_id,
                persona_text="Alice is a careful guide with a long persona text.",
                behavior_policy={"tone": "safe"},
                policy_plugin_identifier="builtin.default_persona_policy",
                policy_plugin_config={},
                is_enabled=True,
            )
        )
        session.add(
            AgentMemoryItem(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                content="Alice remembers the harbor meeting.",
                metadata_json={"source_kind": "authoring_distillation"},
                embedding=[0.1] * 1536,
                visibility="private",
                is_active=True,
            )
        )
        for asset_id, title, metadata in (
            (
                sprite_asset_id,
                "Galgame Sprite",
                {"source_type": "already_unpacked_galgame", "source_ref": "sprites/alice.png"},
            ),
            (background_asset_id, "Safe Background", {"safe": True}),
            (hidden_asset_id, "Hidden Sprite", {}),
        ):
            asset_role = (
                "character_sprite"
                if asset_id != background_asset_id
                else "scene_background"
            )
            visibility = (
                "developer_only" if asset_id == hidden_asset_id else "reader_visible"
            )
            session.add(
                MediaAsset(
                    id=asset_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    asset_kind="image",
                    asset_role=asset_role,
                    source_kind="imported_original",
                    status="available",
                    visibility=visibility,
                    storage_uri=f"media://{title.lower().replace(' ', '-')}",
                    mime_type="image/png",
                    size_bytes=12,
                    checksum_sha256="c" * 64 if asset_id == sprite_asset_id else "d" * 64,
                    title=title,
                    created_by_actor_ref="test",
                    metadata_json=metadata,
                )
            )
            session.add(
                MediaObject(
                    id=uuid.uuid4(),
                    asset_id=asset_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    object_role="original",
                    storage_uri=f"media://{title.lower().replace(' ', '-')}",
                    filename=f"{title.lower().replace(' ', '-')}.png",
                    mime_type="image/png",
                    size_bytes=12,
                    checksum_sha256="c" * 64 if asset_id == sprite_asset_id else "d" * 64,
                    width=100,
                    height=100,
                    metadata_json={},
                )
            )
        session.add(
            CharacterSpriteSet(
                id=sprite_set_id,
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                style_key="default",
                display_name="Alice Sprites",
                status="active",
                visibility="world_admin",
                metadata_json={},
            )
        )
        session.add(
            CharacterSpriteVariant(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                sprite_set_id=sprite_set_id,
                asset_id=sprite_asset_id,
                expression_key="neutral",
                mood_tags_json=["calm"],
                priority=100,
                is_default=True,
                status="active",
                visibility="world_admin",
                metadata_json={},
            )
        )
        session.add(
            SceneBackgroundProfile(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                scene_id=scene_id,
                location_key="harbor",
                asset_id=background_asset_id,
                priority=100,
                is_default=True,
                status="active",
                visibility="world_admin",
                metadata_json={},
            )
        )
        session.add(
            VoiceProfile(
                id=voice_profile_id,
                world_id=world_id,
                worldline_id=worldline_id,
                profile_key="alice-voice",
                display_name="Alice Voice",
                status="active",
                visibility="world_admin",
                owner_kind="agent",
                owner_agent_id=agent_id,
                provider_integration_id=provider_id,
                provider_voice_id="voice-safe-1",
                supported_languages_json=["en"],
                voice_kind="preset",
                consent_status="not_required",
                usage_policy_json={},
                metadata_json={"style": "bright"},
            )
        )
        session.add(
            AgentVoiceProfileBinding(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                voice_profile_id=voice_profile_id,
                binding_role="default",
                priority=100,
                is_default=True,
                style_overrides_json={"emotion": "warm"},
            )
        )
        session.add(
            AuthoringSourceBatch(
                id=source_batch_id,
                world_id=world_id,
                worldline_id=worldline_id,
                batch_key="galgame",
                display_name="Galgame",
                source_kind="other",
                status="active",
                visibility="private",
                metadata_json={"source_type": "already_unpacked_galgame"},
                created_by_actor_ref="test",
            )
        )
        session.add(
            AuthoringSourceAsset(
                id=source_asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                batch_id=source_batch_id,
                media_asset_id=sprite_asset_id,
                source_asset_kind="image",
                source_label="alice.png",
                source_ref="sprites/alice.png",
                status="active",
                metadata_json={"source_type": "already_unpacked_galgame"},
            )
        )
        session.add(
            AuthoringSourceFragment(
                id=source_fragment_id,
                world_id=world_id,
                worldline_id=worldline_id,
                source_asset_id=source_asset_id,
                fragment_key="alice-sprite",
                fragment_kind="asset",
                sequence=0,
                excerpt_text=None,
                locator_json={"source_ref": "sprites/alice.png"},
                metadata_json={},
            )
        )
        session.add(
            AuthoringSourceTraceability(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                source_fragment_id=source_fragment_id,
                proposal_id=None,
                applied_ref_kind="media_asset",
                applied_ref_id=sprite_asset_id,
                trace_kind="proposal_applied",
                metadata_json={},
            )
        )
        session.commit()
    return {"hidden_asset_id": str(hidden_asset_id)}


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


def _extended_manifest_sections() -> dict[str, Any]:
    return {
        "providers": [
            {
                "provider_key": "safe-provider",
                "provider_kind": "text_generation",
                "adapter_kind": "fake",
                "display_name": "Safe Provider",
                "auth_ref_configured": True,
                "config": {"safe": True},
                "default_params": {"temperature": 0.2},
                "capabilities": ["supports_text_generation"],
                "status": "active",
                "visibility": "world_admin",
            }
        ],
        "personas": [
            {
                "agent_key": "alice",
                "display_name": "Alice",
                "persona_summary": "Alice is safe.",
                "character_profile": {"role": "lead"},
                "behavior_policy": {"tone": "safe"},
                "enabled": True,
            }
        ],
        "memories": [
            {
                "agent_key": "alice",
                "worldline_key": "primary",
                "memory_key": "memory-alice",
                "content_summary": "Alice remembers the harbor.",
                "metadata": {"source_kind": "authoring_distillation"},
                "active": True,
            }
        ],
        "visual_mappings": [
            {
                "mapping_kind": "scene_background",
                "worldline_key": "primary",
                "scene_key": "harbor",
                "package_asset_key": "background",
                "role": "harbor",
                "metadata": {"is_default": True},
            }
        ],
        "voice_mappings": [
            {
                "worldline_key": "primary",
                "agent_key": "alice",
                "voice_profile_key": "alice-voice",
                "display_name": "Alice Voice",
                "provider_key": "safe-provider",
                "provider_voice_id": "voice-safe-1",
                "binding_role": "default",
                "style_overrides": {"emotion": "warm"},
                "metadata": {"style": "bright"},
            }
        ],
        "source_traceability": [
            {
                "worldline_key": "primary",
                "source_kind": "image",
                "source_label": "alice.png",
                "source_ref": "sprites/alice.png",
                "trace_kind": "proposal_applied",
                "applied_ref_kind": "media_asset",
                "metadata": {"public_sample_policy": "excluded_placeholder"},
                "excluded_from_public_sample": True,
                "exclusion_reason": "user-provided galgame source assets are excluded",
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
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _authenticate_without_csrf(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)


def _count_rows(engine: Engine, model: type[Any]) -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count(model.id))) or 0


def _assert_no_forbidden_markers(value: object) -> None:
    serialized = json.dumps(value, sort_keys=True).lower()
    for marker in FORBIDDEN_MARKERS:
        assert marker not in serialized
