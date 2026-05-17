from __future__ import annotations

import uuid
from typing import cast

import pytest
from noveland.agents.models import Agent
from noveland.auth.models import User
from noveland.core.database import Base, import_model_modules
from noveland.events.models import WorldEventModel
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
from noveland.visual_generation.contracts import (
    CharacterVisualGenerationProfileCreate,
    VisualGenerationPlanCreate,
    VisualGenerationPlanReferenceCreate,
    VisualGenerationReferenceKind,
    VisualGenerationReferenceRole,
    VisualGenerationVisibility,
    VisualModelAssetCreate,
    VisualModelInventoryKind,
    VisualWorkflowIntent,
    VisualWorkflowTemplateStatus,
    WorkflowTemplateCreate,
    WorkflowTemplateVersionCreate,
    WorkflowTemplateVersionValidationStatus,
)
from noveland.visual_generation.models import (
    CharacterVisualGenerationProfile,
    VisualGenerationPlan,
    VisualGenerationPlanReference,
    VisualModelAsset,
    VisualWorkflowTemplate,
    VisualWorkflowTemplateVersion,
)
from noveland.visual_generation.service import (
    VisualGenerationService,
    VisualGenerationValidationError,
)
from noveland.worlds.models import Scene, World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_workflow_template_registry_and_slot_validation() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id, scene_id = _seed_world_graph(engine)
    provider_id = _seed_provider(engine, world_id, ProviderAdapterKind.COMFYUI)

    with Session(engine) as session:
        service = VisualGenerationService(session)
        template = service.create_workflow_template(
            WorkflowTemplateCreate(
                world_id=world_id,
                provider_id=provider_id,
                provider_kind=ProviderKind.IMAGE_GENERATION,
                adapter_kind=ProviderAdapterKind.COMFYUI,
                workflow_key="Expression Template",
                display_name="Expression Template",
                intent=VisualWorkflowIntent.EXPRESSION_VARIANT,
                status=VisualWorkflowTemplateStatus.ACTIVE,
            )
        )
        version = service.create_workflow_template_version(
            world_id,
            WorkflowTemplateVersionCreate(
                template_id=template.id,
                version="v1",
                parameter_schema_json={
                    "slots": ["positive_prompt", "checkpoint_id", "lora_ids", "width", "height"],
                    "required": ["positive_prompt", "checkpoint_id"],
                },
                required_capabilities_json={"capabilities": ["supports_image_generation"]},
                template_payload_json={"template": "configured"},
                validation_status=WorkflowTemplateVersionValidationStatus.VALID,
            ),
        )
        checkpoint = service.create_model_asset(
            VisualModelAssetCreate(
                world_id=world_id,
                provider_id=provider_id,
                inventory_kind=VisualModelInventoryKind.CHECKPOINT,
                display_name="Base Checkpoint",
                provider_model_name="base.safetensors",
                compatible_base_models=("sdxl",),
            )
        )
        lora = service.create_model_asset(
            VisualModelAssetCreate(
                world_id=world_id,
                provider_id=provider_id,
                inventory_kind=VisualModelInventoryKind.LORA,
                display_name="Character LoRA",
                provider_model_name="character-lora",
                trigger_words=("heroine",),
                compatible_base_models=("sdxl",),
                recommended_weight=0.8,
            )
        )
        service.create_character_profile(
            CharacterVisualGenerationProfileCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                preferred_checkpoint_id=checkpoint.id,
                allowed_lora_ids=(lora.id,),
                default_lora_ids=(lora.id,),
                prompt_fragments_json={"style": "galgame"},
                default_workflow_template_id=template.id,
            )
        )
        plan = service.create_plan(
            VisualGenerationPlanCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                intent=VisualWorkflowIntent.EXPRESSION_VARIANT,
                provider_id=provider_id,
                workflow_template_id=template.id,
                workflow_template_version_id=version.id,
                character_ids=(agent_id,),
                scene_id=scene_id,
                prompt_plan_json={"positive_prompt": "heroine smiling"},
                model_plan_json={"checkpoint_id": str(checkpoint.id), "lora_ids": [str(lora.id)]},
                output_plan_json={"width": 1024, "height": 1536},
            )
        )
        validation = service.validate_plan(world_id, plan.id)
        dry_run = service.dry_run_plan(world_id, plan.id)
        session.commit()

    assert template.workflow_key == "expression-template"
    assert version.template_payload_configured is True
    assert validation.passed is True
    assert validation.mapping_kind == "comfyui"
    assert validation.provider_call_made is False
    assert dry_run.dry_run_status == "dry_run_succeeded"
    assert dry_run.provider_call_made is False
    assert dry_run.mapped_request_json["adapter"] == "comfyui"
    assert dry_run.mapped_request_json["template_payload_configured"] is True


def test_plan_validation_rejects_non_whitelisted_and_missing_slots() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id, _scene_id = _seed_world_graph(engine)
    provider_id = _seed_provider(engine, world_id, ProviderAdapterKind.COMFYUI)

    with Session(engine) as session:
        service = VisualGenerationService(session)
        template_id, version_id = _seed_active_template(
            service,
            world_id,
            provider_id,
            ProviderAdapterKind.COMFYUI,
            slots=("positive_prompt", "checkpoint_id"),
            required=("positive_prompt", "checkpoint_id"),
        )
        plan = service.create_plan(
            VisualGenerationPlanCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                intent=VisualWorkflowIntent.CHARACTER_SPRITE,
                provider_id=provider_id,
                workflow_template_id=template_id,
                workflow_template_version_id=version_id,
                prompt_plan_json={"positive_prompt": "heroine"},
                output_plan_json={"width": 512},
            )
        )
        validation = service.validate_plan(world_id, plan.id)

    issue_codes = {issue.code for issue in validation.issues}
    assert validation.passed is False
    assert issue_codes == {"slot_not_allowed", "slot_required"}


def test_model_asset_inventory_filters_and_rejects_local_paths() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id, _scene_id = _seed_world_graph(engine)
    provider_id = _seed_provider(engine, world_id, ProviderAdapterKind.COMFYUI)

    with Session(engine) as session:
        service = VisualGenerationService(session)
        world_asset = service.create_model_asset(
            VisualModelAssetCreate(
                world_id=world_id,
                provider_id=provider_id,
                inventory_kind=VisualModelInventoryKind.CHECKPOINT,
                display_name="World Checkpoint",
                provider_model_name="world-checkpoint",
            )
        )
        hidden_asset = service.create_model_asset(
            VisualModelAssetCreate(
                world_id=world_id,
                provider_id=provider_id,
                inventory_kind=VisualModelInventoryKind.LORA,
                display_name="Hidden LoRA",
                provider_model_name="hidden-lora",
                visibility=VisualGenerationVisibility.HIDDEN,
            ),
            include_restricted=True,
        )
        worldline_asset = service.create_model_asset(
            VisualModelAssetCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=provider_id,
                inventory_kind=VisualModelInventoryKind.LORA,
                display_name="Worldline LoRA",
                provider_model_name="worldline-lora",
            )
        )
        listed = service.list_model_assets(world_id, worldline_id=worldline_id)
        with pytest.raises(VisualGenerationValidationError, match="file_name"):
            service.create_model_asset(
                VisualModelAssetCreate(
                    world_id=world_id,
                    provider_id=provider_id,
                    inventory_kind=VisualModelInventoryKind.LORA,
                    display_name="Path LoRA",
                    provider_model_name="path-lora",
                    file_name="/models/lora.safetensors",
                )
            )
        session.commit()

    assert [asset.id for asset in listed] == [world_asset.id, worldline_asset.id]
    assert hidden_asset.id not in {asset.id for asset in listed}


def test_character_profile_requires_worldline_and_valid_lora_sets() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id, _scene_id = _seed_world_graph(engine)
    fork_id = _seed_fork(engine, world_id, worldline_id)
    provider_id = _seed_provider(engine, world_id, ProviderAdapterKind.COMFYUI)

    with Session(engine) as session:
        service = VisualGenerationService(session)
        lora = service.create_model_asset(
            VisualModelAssetCreate(
                world_id=world_id,
                worldline_id=fork_id,
                provider_id=provider_id,
                inventory_kind=VisualModelInventoryKind.LORA,
                display_name="Fork LoRA",
                provider_model_name="fork-lora",
            )
        )
        with pytest.raises(VisualGenerationValidationError, match="worldline mismatch"):
            service.create_character_profile(
                CharacterVisualGenerationProfileCreate(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    agent_id=agent_id,
                    allowed_lora_ids=(lora.id,),
                )
            )
        with pytest.raises(ValueError, match="default LoRAs"):
            CharacterVisualGenerationProfileCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                default_lora_ids=(lora.id,),
            )


def test_plan_validation_rejects_profile_banned_lora_and_cross_worldline_reference() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id, _scene_id = _seed_world_graph(engine)
    fork_id = _seed_fork(engine, world_id, worldline_id)
    provider_id = _seed_provider(engine, world_id, ProviderAdapterKind.FAKE)

    with Session(engine) as session:
        service = VisualGenerationService(session)
        allowed_lora = service.create_model_asset(
            VisualModelAssetCreate(
                world_id=world_id,
                provider_id=provider_id,
                inventory_kind=VisualModelInventoryKind.LORA,
                display_name="Allowed LoRA",
                provider_model_name="allowed-lora",
            )
        )
        banned_lora = service.create_model_asset(
            VisualModelAssetCreate(
                world_id=world_id,
                provider_id=provider_id,
                inventory_kind=VisualModelInventoryKind.LORA,
                display_name="Banned LoRA",
                provider_model_name="banned-lora",
            )
        )
        service.create_character_profile(
            CharacterVisualGenerationProfileCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                allowed_lora_ids=(allowed_lora.id,),
                banned_lora_ids=(banned_lora.id,),
            )
        )
        reference_asset_id = _seed_media_asset(session, world_id, fork_id)
        with pytest.raises(VisualGenerationValidationError, match="forbidden field"):
            service.create_plan(
                VisualGenerationPlanCreate(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    intent=VisualWorkflowIntent.CHARACTER_SPRITE,
                    provider_id=provider_id,
                    character_ids=(agent_id,),
                    prompt_plan_json={"prompt": "heroine"},
                    references=(
                        VisualGenerationPlanReferenceCreate(
                            reference_kind=VisualGenerationReferenceKind.AGENT,
                            reference_id=agent_id,
                            reference_role=VisualGenerationReferenceRole.EVIDENCE,
                            metadata_json={"storage_uri": "media://secret"},
                        ),
                    ),
                )
            )
        with pytest.raises(VisualGenerationValidationError, match="plan worldline"):
            service.create_plan(
                VisualGenerationPlanCreate(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    intent=VisualWorkflowIntent.CHARACTER_SPRITE,
                    provider_id=provider_id,
                    character_ids=(agent_id,),
                    prompt_plan_json={"prompt": "heroine"},
                    model_plan_json={"lora_ids": [str(banned_lora.id)]},
                    references=(
                        VisualGenerationPlanReferenceCreate(
                            reference_kind=VisualGenerationReferenceKind.MEDIA_ASSET,
                            reference_id=reference_asset_id,
                            reference_role=VisualGenerationReferenceRole.CHARACTER_REFERENCE,
                        ),
                    ),
                )
            )
        plan = service.create_plan(
            VisualGenerationPlanCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                intent=VisualWorkflowIntent.CHARACTER_SPRITE,
                provider_id=provider_id,
                character_ids=(agent_id,),
                prompt_plan_json={"prompt": "heroine"},
                model_plan_json={"lora_ids": [str(banned_lora.id)]},
            )
        )
        validation = service.validate_plan(world_id, plan.id)

    issue_codes = {issue.code for issue in validation.issues}
    assert {"lora_not_allowed", "lora_banned"} <= issue_codes


def test_plan_validation_rejects_invalid_model_ids_and_lora_base_model_mismatch() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id, _scene_id = _seed_world_graph(engine)
    provider_id = _seed_provider(engine, world_id, ProviderAdapterKind.FAKE)

    with Session(engine) as session:
        service = VisualGenerationService(session)
        checkpoint = service.create_model_asset(
            VisualModelAssetCreate(
                world_id=world_id,
                provider_id=provider_id,
                inventory_kind=VisualModelInventoryKind.CHECKPOINT,
                display_name="SDXL Checkpoint",
                provider_model_name="sdxl-checkpoint",
                compatible_base_models=("sdxl",),
            )
        )
        mismatched_lora = service.create_model_asset(
            VisualModelAssetCreate(
                world_id=world_id,
                provider_id=provider_id,
                inventory_kind=VisualModelInventoryKind.LORA,
                display_name="SD 1.5 LoRA",
                provider_model_name="sd15-lora",
                compatible_base_models=("sd15",),
            )
        )
        malformed_plan = service.create_plan(
            VisualGenerationPlanCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                intent=VisualWorkflowIntent.CHARACTER_SPRITE,
                provider_id=provider_id,
                prompt_plan_json={"prompt": "heroine"},
                model_plan_json={"checkpoint_id": "not-a-uuid", "lora_ids": ["also-not-a-uuid"]},
            )
        )
        mismatch_plan = service.create_plan(
            VisualGenerationPlanCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                intent=VisualWorkflowIntent.CHARACTER_SPRITE,
                provider_id=provider_id,
                prompt_plan_json={"prompt": "heroine"},
                model_plan_json={
                    "checkpoint_id": str(checkpoint.id),
                    "lora_ids": [str(mismatched_lora.id)],
                },
            )
        )
        malformed_validation = service.validate_plan(world_id, malformed_plan.id)
        mismatch_validation = service.validate_plan(world_id, mismatch_plan.id)

    malformed_codes = {issue.code for issue in malformed_validation.issues}
    mismatch_codes = {issue.code for issue in mismatch_validation.issues}
    assert {"checkpoint_invalid_format", "lora_ids_invalid_format"} <= malformed_codes
    assert "lora_base_model_mismatch" in mismatch_codes


def test_cross_provider_mapping_dry_run_and_no_world_event_pollution() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id, _scene_id = _seed_world_graph(engine)
    z_image_provider_id = _seed_provider(
        engine,
        world_id,
        ProviderAdapterKind.CUSTOM_HTTP,
        provider_key="z-image-gateway",
    )
    openai_provider_id = _seed_provider(
        engine,
        world_id,
        ProviderAdapterKind.OPENAI,
        provider_key="gpt-image",
    )

    with Session(engine) as session:
        service = VisualGenerationService(session)
        z_image_plan = service.create_plan(
            VisualGenerationPlanCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                intent=VisualWorkflowIntent.SCENE_BACKGROUND,
                provider_id=z_image_provider_id,
                prompt_plan_json={"prompt": "quiet classroom"},
                model_plan_json={"provider_family": "z_image"},
                output_plan_json={"size": "1024x1024"},
            )
        )
        openai_plan = service.create_plan(
            VisualGenerationPlanCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                intent=VisualWorkflowIntent.EVENT_CG,
                provider_id=openai_provider_id,
                prompt_plan_json={"prompt": "festival night"},
                output_plan_json={"size": "1024x1024"},
            )
        )
        z_image_dry_run = service.dry_run_plan(world_id, z_image_plan.id)
        openai_dry_run = service.dry_run_plan(world_id, openai_plan.id)
        event_count = session.scalar(select(func.count()).select_from(WorldEventModel))

    assert z_image_dry_run.mapping_kind == "z_image"
    assert z_image_dry_run.provider_call_made is False
    assert openai_dry_run.mapping_kind == "openai"
    assert openai_dry_run.provider_call_made is False
    assert event_count == 0


def test_raw_workflow_and_forbidden_leaks_are_rejected() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id, _scene_id = _seed_world_graph(engine)
    provider_id = _seed_provider(engine, world_id, ProviderAdapterKind.FAKE)

    with Session(engine) as session:
        service = VisualGenerationService(session)
        with pytest.raises(VisualGenerationValidationError, match="raw workflow"):
            service.create_plan(
                VisualGenerationPlanCreate(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    intent=VisualWorkflowIntent.OTHER,
                    provider_id=provider_id,
                    prompt_plan_json={"prompt": "safe", "workflow_json": {"nodes": []}},
                )
            )
        with pytest.raises(VisualGenerationValidationError, match="forbidden field"):
            service.create_plan(
                VisualGenerationPlanCreate(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    intent=VisualWorkflowIntent.OTHER,
                    provider_id=provider_id,
                    source_context_json={"storage_uri": "media://secret"},
                )
            )


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import_model_modules()
    for table in (
        cast(Table, User.__table__),
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, Scene.__table__),
        cast(Table, Agent.__table__),
        cast(Table, ProviderIntegration.__table__),
        cast(Table, ProviderCapability.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, VisualWorkflowTemplate.__table__),
        cast(Table, VisualWorkflowTemplateVersion.__table__),
        cast(Table, VisualModelAsset.__table__),
        cast(Table, CharacterVisualGenerationProfile.__table__),
        cast(Table, VisualGenerationPlan.__table__),
        cast(Table, VisualGenerationPlanReference.__table__),
    ):
        table.create(engine)
    assert ModelInvocation.__table__ in Base.metadata.tables.values()
    return engine


def _seed_world_graph(engine: Engine) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    scene_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(User(id=user_id, email=f"{user_id}@example.test", display_name="Test"))
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug=f"world-{world_id.hex[:8]}",
                name="World",
            )
        )
        session.flush()
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
        return world_id, worldline.id, agent_id, scene_id


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
    *,
    provider_key: str | None = None,
) -> uuid.UUID:
    with Session(engine) as session:
        provider = ProviderRegistryService(session).create_provider(
            ProviderIntegrationCreate(
                world_id=world_id,
                scope_kind=ProviderScopeKind.WORLD,
                provider_kind=ProviderKind.IMAGE_GENERATION,
                adapter_kind=adapter_kind,
                provider_key=provider_key or f"{adapter_kind.value}-{uuid.uuid4().hex[:8]}",
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


def _seed_active_template(
    service: VisualGenerationService,
    world_id: uuid.UUID,
    provider_id: uuid.UUID,
    adapter_kind: ProviderAdapterKind,
    *,
    slots: tuple[str, ...],
    required: tuple[str, ...] = (),
) -> tuple[uuid.UUID, uuid.UUID]:
    template = service.create_workflow_template(
        WorkflowTemplateCreate(
            world_id=world_id,
            provider_id=provider_id,
            provider_kind=ProviderKind.IMAGE_GENERATION,
            adapter_kind=adapter_kind,
            workflow_key=f"{adapter_kind.value}-{uuid.uuid4().hex[:8]}",
            display_name="Template",
            intent=VisualWorkflowIntent.CHARACTER_SPRITE,
            status=VisualWorkflowTemplateStatus.ACTIVE,
        )
    )
    version = service.create_workflow_template_version(
        world_id,
        WorkflowTemplateVersionCreate(
            template_id=template.id,
            version="v1",
            parameter_schema_json={"slots": list(slots), "required": list(required)},
            template_payload_json={"template": "configured"},
            validation_status=WorkflowTemplateVersionValidationStatus.VALID,
        ),
    )
    return template.id, version.id


def _seed_media_asset(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    visibility: MediaVisibility = MediaVisibility.WORLD_ADMIN,
) -> uuid.UUID:
    asset = MediaAsset(
        id=uuid.uuid4(),
        world_id=world_id,
        worldline_id=worldline_id,
        asset_kind=MediaAssetKind.IMAGE.value,
        asset_role=MediaAssetRole.REFERENCE_IMAGE.value,
        source_kind=MediaSourceKind.TEST_FIXTURE.value,
        status=MediaAssetStatus.AVAILABLE.value,
        visibility=visibility.value,
        mime_type="image/png",
        file_ext="png",
        size_bytes=1,
        checksum_sha256="0" * 64,
        created_by_actor_ref="test",
    )
    session.add(asset)
    session.flush()
    return asset.id
