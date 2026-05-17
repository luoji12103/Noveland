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
from noveland.events.models import WorldEventModel, WorldSnapshotModel
from noveland.invocations.models import ModelInvocation
from noveland.media.contracts import (
    MediaAssetKind,
    MediaAssetRole,
    MediaAssetStatus,
    MediaSourceKind,
    MediaVisibility,
)
from noveland.media.models import MediaAsset
from noveland.memory.models import MemoryBackendProfile
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderCapabilityCreate,
    ProviderIntegrationCreate,
    ProviderKind,
    ProviderScopeKind,
)
from noveland.providers.models import ProviderCapability, ProviderIntegration
from noveland.providers.registry import ProviderRegistryService
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.visual_generation.models import (
    CharacterVisualGenerationProfile,
    VisualGenerationPlan,
    VisualGenerationPlanReference,
    VisualModelAsset,
    VisualWorkflowTemplate,
    VisualWorkflowTemplateVersion,
)
from noveland.worlds.models import Scene, World, Worldline, WorldMembership
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_visual_generation_api_template_inventory_profile_and_plan_flow() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    world_id = _seed_world(engine, admin_id)
    worldline_id, agent_id, scene_id = _seed_world_graph(engine, world_id)
    provider_id = _seed_provider(engine, world_id, ProviderAdapterKind.COMFYUI)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, admin_token)

    template = client.post(
        f"/worlds/{world_id}/visual-generation/workflow-templates",
        json={
            "world_id": str(world_id),
            "provider_id": str(provider_id),
            "provider_kind": "image_generation",
            "adapter_kind": "comfyui",
            "workflow_key": "Expression Template",
            "display_name": "Expression Template",
            "intent": "expression_variant",
            "status": "active",
        },
    )
    template_id = template.json()["id"]
    version = client.post(
        f"/worlds/{world_id}/visual-generation/workflow-templates/{template_id}/versions",
        json={
            "template_id": template_id,
            "version": "v1",
            "parameter_schema_json": {
                "slots": ["positive_prompt", "checkpoint_id", "lora_ids", "width", "height"],
                "required": ["positive_prompt", "checkpoint_id"],
            },
            "required_capabilities_json": {"capabilities": ["supports_image_generation"]},
            "template_payload_json": {"template": "configured"},
            "validation_status": "valid",
        },
    )
    version_id = version.json()["id"]
    checkpoint = client.post(
        f"/worlds/{world_id}/visual-generation/model-assets",
        json={
            "world_id": str(world_id),
            "provider_id": str(provider_id),
            "inventory_kind": "checkpoint",
            "display_name": "Base Checkpoint",
            "provider_model_name": "base-model",
        },
    )
    checkpoint_id = checkpoint.json()["id"]
    lora = client.post(
        f"/worlds/{world_id}/visual-generation/model-assets",
        json={
            "world_id": str(world_id),
            "provider_id": str(provider_id),
            "inventory_kind": "lora",
            "display_name": "Character LoRA",
            "provider_model_name": "character-lora",
            "trigger_words": ["heroine"],
            "recommended_weight": 0.8,
        },
    )
    lora_id = lora.json()["id"]
    profile = client.post(
        f"/worlds/{world_id}/visual-generation/character-profiles",
        json={
            "world_id": str(world_id),
            "worldline_id": str(worldline_id),
            "agent_id": str(agent_id),
            "preferred_checkpoint_id": checkpoint_id,
            "allowed_lora_ids": [lora_id],
            "default_lora_ids": [lora_id],
            "prompt_fragments_json": {"style": "galgame"},
            "default_workflow_template_id": template_id,
        },
    )
    plan = client.post(
        f"/worlds/{world_id}/visual-generation/plans",
        json={
            "world_id": str(world_id),
            "worldline_id": str(worldline_id),
            "intent": "expression_variant",
            "provider_id": str(provider_id),
            "workflow_template_id": template_id,
            "workflow_template_version_id": version_id,
            "character_ids": [str(agent_id)],
            "scene_id": str(scene_id),
            "prompt_plan_json": {"positive_prompt": "heroine smiling"},
            "model_plan_json": {"checkpoint_id": checkpoint_id, "lora_ids": [lora_id]},
            "output_plan_json": {"width": 1024, "height": 1536},
        },
    )
    plan_id = plan.json()["id"]
    validation = client.post(f"/worlds/{world_id}/visual-generation/plans/{plan_id}/validate")
    dry_run = client.post(f"/worlds/{world_id}/visual-generation/plans/{plan_id}/dry-run")

    assert template.status_code == 201
    assert template.json()["workflow_key"] == "expression-template"
    assert version.status_code == 201
    assert version.json()["template_payload_configured"] is True
    assert "template_payload_json" not in version.text
    assert checkpoint.status_code == 201
    assert lora.status_code == 201
    assert profile.status_code == 201
    assert plan.status_code == 201
    assert validation.status_code == 200
    assert validation.json()["passed"] is True
    assert validation.json()["provider_call_made"] is False
    assert dry_run.status_code == 200
    assert dry_run.json()["provider_call_made"] is False
    assert dry_run.json()["mapped_request_json"]["adapter"] == "comfyui"
    assert "storage_uri" not in dry_run.text
    assert "base64" not in dry_run.text
    assert "raw_prompt" not in dry_run.text


def test_visual_generation_api_acl_csrf_and_restricted_visibility() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    platform_id, platform_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    world_id = _seed_world(engine, admin_id)
    _seed_world_graph(engine, world_id)
    provider_id = _seed_provider(engine, world_id, ProviderAdapterKind.FAKE)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    _add_membership(engine, world_id, platform_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, member_token)
    member_rejected = client.post(
        f"/worlds/{world_id}/visual-generation/model-assets",
        json={
            "world_id": str(world_id),
            "provider_id": str(provider_id),
            "inventory_kind": "lora",
            "display_name": "Member LoRA",
            "provider_model_name": "member-lora",
        },
    )

    _authenticate(client, admin_token)
    client.headers.pop(CSRF_HEADER_NAME, None)
    csrf_rejected = client.post(
        f"/worlds/{world_id}/visual-generation/model-assets",
        json={
            "world_id": str(world_id),
            "provider_id": str(provider_id),
            "inventory_kind": "lora",
            "display_name": "No CSRF LoRA",
            "provider_model_name": "no-csrf-lora",
        },
    )
    _authenticate(client, admin_token)
    hidden_rejected = client.post(
        f"/worlds/{world_id}/visual-generation/model-assets",
        json={
            "world_id": str(world_id),
            "provider_id": str(provider_id),
            "inventory_kind": "lora",
            "display_name": "Hidden LoRA",
            "provider_model_name": "hidden-lora",
            "visibility": "hidden",
        },
    )

    _authenticate(client, platform_token)
    hidden_created = client.post(
        f"/worlds/{world_id}/visual-generation/model-assets",
        json={
            "world_id": str(world_id),
            "provider_id": str(provider_id),
            "inventory_kind": "lora",
            "display_name": "Hidden LoRA",
            "provider_model_name": "hidden-lora",
            "visibility": "hidden",
        },
    )
    listed_for_platform = client.get(f"/worlds/{world_id}/visual-generation/model-assets")

    _authenticate(client, admin_token)
    listed_for_admin = client.get(f"/worlds/{world_id}/visual-generation/model-assets")

    assert member_rejected.status_code == 403
    assert csrf_rejected.status_code == 403
    assert hidden_rejected.status_code == 403
    assert hidden_created.status_code == 201
    assert hidden_created.json()["visibility"] == "hidden"
    assert [item["id"] for item in listed_for_platform.json()] == [hidden_created.json()["id"]]
    assert listed_for_admin.json() == []


def test_visual_generation_api_rejects_raw_workflow_and_leaky_payloads() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    world_id = _seed_world(engine, admin_id)
    worldline_id, _agent_id, _scene_id = _seed_world_graph(engine, world_id)
    provider_id = _seed_provider(engine, world_id, ProviderAdapterKind.FAKE)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, admin_token)

    raw_workflow = client.post(
        f"/worlds/{world_id}/visual-generation/plans",
        json={
            "world_id": str(world_id),
            "worldline_id": str(worldline_id),
            "intent": "other",
            "provider_id": str(provider_id),
            "prompt_plan_json": {"prompt": "safe", "workflow_json": {"nodes": []}},
        },
    )
    leaky_payload = client.post(
        f"/worlds/{world_id}/visual-generation/plans",
        json={
            "world_id": str(world_id),
            "worldline_id": str(worldline_id),
            "intent": "other",
            "provider_id": str(provider_id),
            "source_context_json": {"storage_uri": "media://secret"},
        },
    )

    assert raw_workflow.status_code == 422
    assert "raw workflow" in raw_workflow.text
    assert leaky_payload.status_code == 422
    assert "forbidden field" in leaky_payload.text


def test_visual_generation_api_rejects_cross_worldline_reference_and_makes_no_calls() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    world_id = _seed_world(engine, admin_id)
    worldline_id, _agent_id, _scene_id = _seed_world_graph(engine, world_id)
    fork_id = _seed_fork(engine, world_id, worldline_id)
    provider_id = _seed_provider(engine, world_id, ProviderAdapterKind.FAKE)
    reference_asset_id = _seed_media_asset(engine, world_id, fork_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, admin_token)

    rejected = client.post(
        f"/worlds/{world_id}/visual-generation/plans",
        json={
            "world_id": str(world_id),
            "worldline_id": str(worldline_id),
            "intent": "character_sprite",
            "provider_id": str(provider_id),
            "prompt_plan_json": {"prompt": "heroine"},
            "references": [
                {
                    "reference_kind": "media_asset",
                    "reference_id": str(reference_asset_id),
                    "reference_role": "character_reference",
                }
            ],
        },
    )
    valid_plan = client.post(
        f"/worlds/{world_id}/visual-generation/plans",
        json={
            "world_id": str(world_id),
            "worldline_id": str(worldline_id),
            "intent": "character_sprite",
            "provider_id": str(provider_id),
            "prompt_plan_json": {"prompt": "heroine"},
        },
    )
    dry_run = client.post(
        f"/worlds/{world_id}/visual-generation/plans/{valid_plan.json()['id']}/dry-run"
    )

    with Session(engine) as session:
        event_count = session.scalar(select(func.count()).select_from(WorldEventModel))
        invocation_count = session.scalar(select(func.count()).select_from(ModelInvocation))

    assert rejected.status_code == 422
    assert "plan worldline" in rejected.text
    assert valid_plan.status_code == 201
    assert dry_run.status_code == 200
    assert dry_run.json()["provider_call_made"] is False
    assert event_count == 0
    assert invocation_count == 0


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
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, WorldSnapshotModel.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, Scene.__table__),
        cast(Table, Agent.__table__),
        cast(Table, ProviderIntegration.__table__),
        cast(Table, ProviderCapability.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, ModelInvocation.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, VisualWorkflowTemplate.__table__),
        cast(Table, VisualWorkflowTemplateVersion.__table__),
        cast(Table, VisualModelAsset.__table__),
        cast(Table, CharacterVisualGenerationProfile.__table__),
        cast(Table, VisualGenerationPlan.__table__),
        cast(Table, VisualGenerationPlanReference.__table__),
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


def _seed_world_graph(
    engine: Engine, world_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    agent_id = uuid.uuid4()
    scene_id = uuid.uuid4()
    with Session(engine) as session:
        worldline = ensure_primary_worldline(session, world_id)
        session.add(
            Scene(
                id=scene_id,
                world_id=world_id,
                scene_key=f"scene-{scene_id.hex[:8]}",
                name="Scene",
            )
        )
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key=f"agent-{agent_id.hex[:8]}",
                display_name="Agent",
                kind="role_agent",
            )
        )
        session.commit()
        return worldline.id, agent_id, scene_id


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


def _seed_provider(
    engine: Engine,
    world_id: uuid.UUID,
    adapter_kind: ProviderAdapterKind,
) -> uuid.UUID:
    with Session(engine) as session:
        provider = ProviderRegistryService(session).create_provider(
            ProviderIntegrationCreate(
                world_id=world_id,
                scope_kind=ProviderScopeKind.WORLD,
                provider_kind=ProviderKind.IMAGE_GENERATION,
                adapter_kind=adapter_kind,
                provider_key=f"{adapter_kind.value}-{uuid.uuid4().hex[:8]}",
                display_name=f"{adapter_kind.value} Image",
                capabilities=(
                    ProviderCapabilityCreate(
                        capability_key="supports_image_generation",
                        capability_json={"value": True},
                    ),
                ),
            )
        )
        session.commit()
        return provider.id


def _seed_media_asset(engine: Engine, world_id: uuid.UUID, worldline_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        asset = MediaAsset(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline_id,
            asset_kind=MediaAssetKind.IMAGE.value,
            asset_role=MediaAssetRole.REFERENCE_IMAGE.value,
            source_kind=MediaSourceKind.TEST_FIXTURE.value,
            status=MediaAssetStatus.AVAILABLE.value,
            visibility=MediaVisibility.WORLD_ADMIN.value,
            mime_type="image/png",
            file_ext="png",
            size_bytes=1,
            checksum_sha256="0" * 64,
            created_by_actor_ref="test",
        )
        session.add(asset)
        session.commit()
        return asset.id


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
