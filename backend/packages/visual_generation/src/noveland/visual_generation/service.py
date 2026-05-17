from __future__ import annotations

import uuid
from typing import Any

from noveland.agents.models import Agent
from noveland.media.contracts import MediaAssetStatus, MediaVisibility
from noveland.media.models import MediaAsset
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderIntegrationStatus,
    ProviderKind,
)
from noveland.providers.models import ProviderCapability, ProviderIntegration
from noveland.providers.registry import ProviderNotFoundError, ProviderRegistryService
from noveland.visual_generation.contracts import (
    CharacterVisualGenerationProfileCreate,
    CharacterVisualGenerationProfileRead,
    CharacterVisualGenerationProfileUpdate,
    CharacterVisualProfileReviewStatus,
    ValidationIssue,
    ValidationSeverity,
    VisualGenerationDryRunResult,
    VisualGenerationPlanCreate,
    VisualGenerationPlanRead,
    VisualGenerationPlanReferenceRead,
    VisualGenerationPlanStatus,
    VisualGenerationPlanValidationResult,
    VisualGenerationReferenceKind,
    VisualGenerationReferenceRole,
    VisualGenerationVisibility,
    VisualModelAssetCreate,
    VisualModelAssetRead,
    VisualModelAssetUpdate,
    VisualModelInventoryKind,
    VisualWorkflowIntent,
    VisualWorkflowTemplateStatus,
    WorkflowTemplateCreate,
    WorkflowTemplateRead,
    WorkflowTemplateUpdate,
    WorkflowTemplateVersionCreate,
    WorkflowTemplateVersionRead,
    WorkflowTemplateVersionValidationStatus,
)
from noveland.visual_generation.mapping import map_provider_request
from noveland.visual_generation.models import (
    CharacterVisualGenerationProfile,
    VisualGenerationPlan,
    VisualGenerationPlanReference,
    VisualModelAsset,
    VisualWorkflowTemplate,
    VisualWorkflowTemplateVersion,
)
from noveland.visual_generation.planning import slot_values_from_plan
from noveland.visual_generation.validators import (
    leak_issues,
    reject_raw_workflow_payload,
    safe_json_or_raise,
    sanitize_validation_metadata,
    validate_provider_adapter,
    validate_slots,
)
from noveland.worlds.models import Scene, World
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class VisualGenerationValidationError(ValueError):
    pass


class VisualGenerationNotFoundError(LookupError):
    pass


RESTRICTED_VISIBILITIES = {
    VisualGenerationVisibility.DEVELOPER_ONLY.value,
    VisualGenerationVisibility.HIDDEN.value,
}
RESTRICTED_MEDIA_VISIBILITIES = {
    MediaVisibility.DEVELOPER_ONLY.value,
    MediaVisibility.HIDDEN.value,
}


class VisualGenerationService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_workflow_template(
        self,
        create: WorkflowTemplateCreate,
    ) -> WorkflowTemplateRead:
        self._validate_world(create.world_id)
        if create.provider_id is not None:
            self._provider_read(create.world_id, create.provider_id, platform_admin=True)
        self._provider_adapter_issues_or_raise(create.provider_kind, create.adapter_kind)
        model = VisualWorkflowTemplate(
            id=uuid.uuid4(),
            world_id=create.world_id,
            provider_id=create.provider_id,
            provider_kind=create.provider_kind.value,
            adapter_kind=create.adapter_kind.value,
            workflow_key=create.workflow_key,
            display_name=create.display_name,
            intent=create.intent.value,
            status=create.status.value,
            visibility=create.visibility.value,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise VisualGenerationValidationError("workflow template already exists") from exc
        self._session.refresh(model)
        return _workflow_template_record(model)

    def list_workflow_templates(
        self,
        world_id: uuid.UUID,
        *,
        include_restricted: bool = False,
    ) -> list[WorkflowTemplateRead]:
        statement = select(VisualWorkflowTemplate).where(
            VisualWorkflowTemplate.world_id == world_id,
            VisualWorkflowTemplate.status != VisualWorkflowTemplateStatus.DELETED.value,
        )
        if not include_restricted:
            statement = statement.where(
                VisualWorkflowTemplate.visibility.not_in(RESTRICTED_VISIBILITIES)
            )
        statement = statement.order_by(
            VisualWorkflowTemplate.intent,
            VisualWorkflowTemplate.workflow_key,
        )
        return [_workflow_template_record(model) for model in self._session.scalars(statement)]

    def get_workflow_template(
        self,
        world_id: uuid.UUID,
        template_id: uuid.UUID,
        *,
        include_restricted: bool = False,
    ) -> WorkflowTemplateRead:
        model = self._workflow_template_required(world_id, template_id)
        if not include_restricted and model.visibility in RESTRICTED_VISIBILITIES:
            raise VisualGenerationNotFoundError("workflow template not found")
        return _workflow_template_record(model)

    def update_workflow_template(
        self,
        world_id: uuid.UUID,
        template_id: uuid.UUID,
        update: WorkflowTemplateUpdate,
    ) -> WorkflowTemplateRead:
        model = self._workflow_template_required(world_id, template_id)
        provider_kind = (
            update.provider_kind.value if update.provider_kind is not None else model.provider_kind
        )
        adapter_kind = (
            update.adapter_kind.value if update.adapter_kind is not None else model.adapter_kind
        )
        self._provider_adapter_issues_or_raise(
            ProviderKind(provider_kind),
            ProviderAdapterKind(adapter_kind),
        )
        if "provider_id" in update.model_fields_set:
            if update.provider_id is not None:
                self._provider_read(world_id, update.provider_id, platform_admin=True)
            model.provider_id = update.provider_id
        if update.provider_kind is not None:
            model.provider_kind = update.provider_kind.value
        if update.adapter_kind is not None:
            model.adapter_kind = update.adapter_kind.value
        if update.display_name is not None:
            model.display_name = update.display_name
        if update.intent is not None:
            model.intent = update.intent.value
        if update.status is not None:
            model.status = update.status.value
        if update.visibility is not None:
            model.visibility = update.visibility.value
        self._session.flush()
        self._session.refresh(model)
        return _workflow_template_record(model)

    def delete_workflow_template(self, world_id: uuid.UUID, template_id: uuid.UUID) -> None:
        model = self._workflow_template_required(world_id, template_id)
        model.status = VisualWorkflowTemplateStatus.DELETED.value
        self._session.flush()

    def create_workflow_template_version(
        self,
        world_id: uuid.UUID,
        create: WorkflowTemplateVersionCreate,
    ) -> WorkflowTemplateVersionRead:
        self._workflow_template_required(world_id, create.template_id)
        self._validate_version_json(create)
        model = VisualWorkflowTemplateVersion(
            id=uuid.uuid4(),
            template_id=create.template_id,
            version=create.version,
            parameter_schema_json=create.parameter_schema_json,
            required_capabilities_json=create.required_capabilities_json,
            allowed_asset_roles_json=create.allowed_asset_roles_json,
            safety_constraints_json=create.safety_constraints_json,
            template_payload_json=create.template_payload_json,
            validation_status=create.validation_status.value,
            validation_error_json=sanitize_validation_metadata(create.validation_error_json),
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise VisualGenerationValidationError(
                "workflow template version already exists"
            ) from exc
        self._session.refresh(model)
        return _workflow_template_version_record(model)

    def list_workflow_template_versions(
        self,
        world_id: uuid.UUID,
        template_id: uuid.UUID,
    ) -> list[WorkflowTemplateVersionRead]:
        self._workflow_template_required(world_id, template_id)
        statement = (
            select(VisualWorkflowTemplateVersion)
            .where(VisualWorkflowTemplateVersion.template_id == template_id)
            .order_by(VisualWorkflowTemplateVersion.created_at)
        )
        return [
            _workflow_template_version_record(model) for model in self._session.scalars(statement)
        ]

    def create_model_asset(
        self,
        create: VisualModelAssetCreate,
        *,
        include_restricted: bool = False,
    ) -> VisualModelAssetRead:
        self._validate_world(create.world_id)
        if create.worldline_id is not None:
            self._worldline_id(create.world_id, create.worldline_id)
        self._provider_read(create.world_id, create.provider_id, platform_admin=True)
        self._validate_model_asset_payload(create)
        model = VisualModelAsset(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=create.worldline_id,
            provider_id=create.provider_id,
            inventory_kind=create.inventory_kind.value,
            display_name=create.display_name,
            provider_model_name=create.provider_model_name,
            file_name=create.file_name,
            trigger_words_json=list(create.trigger_words),
            compatible_base_models_json=list(create.compatible_base_models),
            recommended_weight=create.recommended_weight,
            style_tags_json=list(create.style_tags),
            character_tags_json=list(create.character_tags),
            visibility=create.visibility.value,
            source_note=create.source_note,
            metadata_json=create.metadata_json,
        )
        if not include_restricted and model.visibility in RESTRICTED_VISIBILITIES:
            raise VisualGenerationValidationError("restricted visibility requires platform admin")
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _model_asset_record(model)

    def list_model_assets(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
        provider_id: uuid.UUID | None = None,
        inventory_kind: VisualModelInventoryKind | None = None,
        include_restricted: bool = False,
    ) -> list[VisualModelAssetRead]:
        statement = select(VisualModelAsset).where(VisualModelAsset.world_id == world_id)
        if worldline_id is not None:
            self._worldline_id(world_id, worldline_id)
            statement = statement.where(
                (VisualModelAsset.worldline_id.is_(None))
                | (VisualModelAsset.worldline_id == worldline_id)
            )
        if provider_id is not None:
            statement = statement.where(VisualModelAsset.provider_id == provider_id)
        if inventory_kind is not None:
            statement = statement.where(VisualModelAsset.inventory_kind == inventory_kind.value)
        if not include_restricted:
            statement = statement.where(VisualModelAsset.visibility.not_in(RESTRICTED_VISIBILITIES))
        statement = statement.order_by(
            VisualModelAsset.inventory_kind,
            VisualModelAsset.display_name,
        )
        return [_model_asset_record(model) for model in self._session.scalars(statement)]

    def get_model_asset(
        self,
        world_id: uuid.UUID,
        model_asset_id: uuid.UUID,
        *,
        include_restricted: bool = False,
    ) -> VisualModelAssetRead:
        return _model_asset_record(
            self._model_asset_required(
                world_id,
                model_asset_id,
                include_restricted=include_restricted,
            )
        )

    def update_model_asset(
        self,
        world_id: uuid.UUID,
        model_asset_id: uuid.UUID,
        update: VisualModelAssetUpdate,
        *,
        include_restricted: bool = False,
    ) -> VisualModelAssetRead:
        model = self._model_asset_required(
            world_id,
            model_asset_id,
            include_restricted=include_restricted,
        )
        if "worldline_id" in update.model_fields_set:
            if update.worldline_id is not None:
                self._worldline_id(world_id, update.worldline_id)
            model.worldline_id = update.worldline_id
        if update.provider_id is not None:
            self._provider_read(world_id, update.provider_id, platform_admin=True)
            model.provider_id = update.provider_id
        if update.inventory_kind is not None:
            model.inventory_kind = update.inventory_kind.value
        if update.display_name is not None:
            model.display_name = update.display_name
        if update.provider_model_name is not None:
            model.provider_model_name = update.provider_model_name
        if "file_name" in update.model_fields_set:
            self._validate_file_name(update.file_name)
            model.file_name = update.file_name
        if update.trigger_words is not None:
            model.trigger_words_json = list(update.trigger_words)
        if update.compatible_base_models is not None:
            model.compatible_base_models_json = list(update.compatible_base_models)
        if "recommended_weight" in update.model_fields_set:
            model.recommended_weight = update.recommended_weight
        if update.style_tags is not None:
            model.style_tags_json = list(update.style_tags)
        if update.character_tags is not None:
            model.character_tags_json = list(update.character_tags)
        if update.visibility is not None:
            if not include_restricted and update.visibility.value in RESTRICTED_VISIBILITIES:
                raise VisualGenerationValidationError(
                    "restricted visibility requires platform admin"
                )
            model.visibility = update.visibility.value
        if "source_note" in update.model_fields_set:
            model.source_note = update.source_note
        if update.metadata_json is not None:
            safe_json_or_raise(update.metadata_json, field_name="metadata_json")
            model.metadata_json = update.metadata_json
        self._session.flush()
        self._session.refresh(model)
        return _model_asset_record(model)

    def delete_model_asset(self, world_id: uuid.UUID, model_asset_id: uuid.UUID) -> None:
        model = self._model_asset_required(world_id, model_asset_id, include_restricted=True)
        model.visibility = VisualGenerationVisibility.HIDDEN.value
        self._session.flush()

    def create_character_profile(
        self,
        create: CharacterVisualGenerationProfileCreate,
        *,
        include_restricted: bool = False,
    ) -> CharacterVisualGenerationProfileRead:
        worldline_id = self._worldline_id(create.world_id, create.worldline_id)
        self._validate_agent(create.world_id, create.agent_id)
        self._validate_profile_assets(create, include_restricted=include_restricted)
        if not include_restricted and create.visibility.value in RESTRICTED_VISIBILITIES:
            raise VisualGenerationValidationError("restricted visibility requires platform admin")
        model = CharacterVisualGenerationProfile(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=worldline_id,
            agent_id=create.agent_id,
            preferred_checkpoint_id=create.preferred_checkpoint_id,
            allowed_lora_ids_json=_uuid_strings(create.allowed_lora_ids),
            default_lora_ids_json=_uuid_strings(create.default_lora_ids),
            banned_lora_ids_json=_uuid_strings(create.banned_lora_ids),
            prompt_fragments_json=create.prompt_fragments_json,
            negative_prompt_fragments_json=create.negative_prompt_fragments_json,
            reference_asset_ids_json=_uuid_strings(create.reference_asset_ids),
            default_workflow_template_id=create.default_workflow_template_id,
            expression_workflow_template_id=create.expression_workflow_template_id,
            cg_workflow_template_id=create.cg_workflow_template_id,
            outfit_policy_json=create.outfit_policy_json,
            pose_policy_json=create.pose_policy_json,
            review_status=create.review_status.value,
            visibility=create.visibility.value,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise VisualGenerationValidationError(
                "character visual generation profile already exists"
            ) from exc
        self._session.refresh(model)
        return _character_profile_record(model)

    def list_character_profiles(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID | None = None,
        include_restricted: bool = False,
    ) -> list[CharacterVisualGenerationProfileRead]:
        resolved = self._worldline_id(world_id, worldline_id)
        statement = select(CharacterVisualGenerationProfile).where(
            CharacterVisualGenerationProfile.world_id == world_id,
            CharacterVisualGenerationProfile.worldline_id == resolved,
            CharacterVisualGenerationProfile.review_status
            != CharacterVisualProfileReviewStatus.DELETED.value,
        )
        if agent_id is not None:
            statement = statement.where(CharacterVisualGenerationProfile.agent_id == agent_id)
        if not include_restricted:
            statement = statement.where(
                CharacterVisualGenerationProfile.visibility.not_in(RESTRICTED_VISIBILITIES)
            )
        statement = statement.order_by(CharacterVisualGenerationProfile.agent_id)
        return [_character_profile_record(model) for model in self._session.scalars(statement)]

    def get_character_profile(
        self,
        world_id: uuid.UUID,
        profile_id: uuid.UUID,
        *,
        include_restricted: bool = False,
    ) -> CharacterVisualGenerationProfileRead:
        return _character_profile_record(
            self._character_profile_required(
                world_id,
                profile_id,
                include_restricted=include_restricted,
            )
        )

    def update_character_profile(
        self,
        world_id: uuid.UUID,
        profile_id: uuid.UUID,
        update: CharacterVisualGenerationProfileUpdate,
        *,
        include_restricted: bool = False,
    ) -> CharacterVisualGenerationProfileRead:
        model = self._character_profile_required(
            world_id,
            profile_id,
            include_restricted=include_restricted,
        )
        merged = CharacterVisualGenerationProfileCreate(
            world_id=model.world_id,
            worldline_id=model.worldline_id,
            agent_id=model.agent_id,
            preferred_checkpoint_id=(
                update.preferred_checkpoint_id
                if "preferred_checkpoint_id" in update.model_fields_set
                else model.preferred_checkpoint_id
            ),
            allowed_lora_ids=(
                update.allowed_lora_ids
                if update.allowed_lora_ids is not None
                else _uuids(model.allowed_lora_ids_json)
            ),
            default_lora_ids=(
                update.default_lora_ids
                if update.default_lora_ids is not None
                else _uuids(model.default_lora_ids_json)
            ),
            banned_lora_ids=(
                update.banned_lora_ids
                if update.banned_lora_ids is not None
                else _uuids(model.banned_lora_ids_json)
            ),
            prompt_fragments_json=(
                update.prompt_fragments_json
                if update.prompt_fragments_json is not None
                else model.prompt_fragments_json
            ),
            negative_prompt_fragments_json=(
                update.negative_prompt_fragments_json
                if update.negative_prompt_fragments_json is not None
                else model.negative_prompt_fragments_json
            ),
            reference_asset_ids=(
                update.reference_asset_ids
                if update.reference_asset_ids is not None
                else _uuids(model.reference_asset_ids_json)
            ),
            default_workflow_template_id=(
                update.default_workflow_template_id
                if "default_workflow_template_id" in update.model_fields_set
                else model.default_workflow_template_id
            ),
            expression_workflow_template_id=(
                update.expression_workflow_template_id
                if "expression_workflow_template_id" in update.model_fields_set
                else model.expression_workflow_template_id
            ),
            cg_workflow_template_id=(
                update.cg_workflow_template_id
                if "cg_workflow_template_id" in update.model_fields_set
                else model.cg_workflow_template_id
            ),
            outfit_policy_json=(
                update.outfit_policy_json
                if update.outfit_policy_json is not None
                else model.outfit_policy_json
            ),
            pose_policy_json=(
                update.pose_policy_json
                if update.pose_policy_json is not None
                else model.pose_policy_json
            ),
            review_status=(
                update.review_status
                if update.review_status is not None
                else CharacterVisualProfileReviewStatus(model.review_status)
            ),
            visibility=(
                update.visibility
                if update.visibility is not None
                else VisualGenerationVisibility(model.visibility)
            ),
        )
        self._validate_profile_assets(merged, include_restricted=include_restricted)
        if not include_restricted and merged.visibility.value in RESTRICTED_VISIBILITIES:
            raise VisualGenerationValidationError("restricted visibility requires platform admin")
        model.preferred_checkpoint_id = merged.preferred_checkpoint_id
        model.allowed_lora_ids_json = _uuid_strings(merged.allowed_lora_ids)
        model.default_lora_ids_json = _uuid_strings(merged.default_lora_ids)
        model.banned_lora_ids_json = _uuid_strings(merged.banned_lora_ids)
        model.prompt_fragments_json = merged.prompt_fragments_json
        model.negative_prompt_fragments_json = merged.negative_prompt_fragments_json
        model.reference_asset_ids_json = _uuid_strings(merged.reference_asset_ids)
        model.default_workflow_template_id = merged.default_workflow_template_id
        model.expression_workflow_template_id = merged.expression_workflow_template_id
        model.cg_workflow_template_id = merged.cg_workflow_template_id
        model.outfit_policy_json = merged.outfit_policy_json
        model.pose_policy_json = merged.pose_policy_json
        model.review_status = merged.review_status.value
        model.visibility = merged.visibility.value
        self._session.flush()
        self._session.refresh(model)
        return _character_profile_record(model)

    def delete_character_profile(self, world_id: uuid.UUID, profile_id: uuid.UUID) -> None:
        model = self._character_profile_required(
            world_id,
            profile_id,
            include_restricted=True,
        )
        model.review_status = CharacterVisualProfileReviewStatus.DELETED.value
        self._session.flush()

    def create_plan(
        self,
        create: VisualGenerationPlanCreate,
        *,
        include_restricted: bool = False,
    ) -> VisualGenerationPlanRead:
        worldline_id = self._worldline_id(create.world_id, create.worldline_id)
        self._provider_read(create.world_id, create.provider_id, platform_admin=True)
        self._validate_plan_payload(create)
        for character_id in create.character_ids:
            self._validate_agent(create.world_id, character_id)
        self._validate_scene(create.world_id, create.scene_id)
        self._validate_template_pair(
            create.world_id,
            create.workflow_template_id,
            create.workflow_template_version_id,
        )
        model = VisualGenerationPlan(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=worldline_id,
            intent=create.intent.value,
            provider_id=create.provider_id,
            workflow_template_id=create.workflow_template_id,
            workflow_template_version_id=create.workflow_template_version_id,
            status=VisualGenerationPlanStatus.DRAFT.value,
            character_ids_json=_uuid_strings(create.character_ids),
            scene_id=create.scene_id,
            prompt_plan_json=create.prompt_plan_json,
            model_plan_json=create.model_plan_json,
            output_plan_json=create.output_plan_json,
            validation_results_json={},
            source_context_json=create.source_context_json,
        )
        self._session.add(model)
        self._session.flush()
        for reference in create.references:
            try:
                safe_json_or_raise(reference.metadata_json, field_name="reference.metadata_json")
            except ValueError as exc:
                raise VisualGenerationValidationError(str(exc)) from exc
            self._validate_reference(
                create.world_id,
                worldline_id,
                reference.reference_kind,
                reference.reference_id,
                include_restricted=include_restricted,
            )
            self._session.add(
                VisualGenerationPlanReference(
                    id=uuid.uuid4(),
                    world_id=create.world_id,
                    worldline_id=worldline_id,
                    plan_id=model.id,
                    reference_kind=reference.reference_kind.value,
                    reference_id=reference.reference_id,
                    reference_role=reference.reference_role.value,
                    display_order=reference.display_order,
                    metadata_json=reference.metadata_json,
                )
            )
        self._session.flush()
        self._session.refresh(model)
        return self._plan_record(model)

    def list_plans(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
        status: VisualGenerationPlanStatus | None = None,
    ) -> list[VisualGenerationPlanRead]:
        statement = select(VisualGenerationPlan).where(
            VisualGenerationPlan.world_id == world_id,
            VisualGenerationPlan.status != VisualGenerationPlanStatus.DELETED.value,
        )
        if worldline_id is not None:
            resolved = self._worldline_id(world_id, worldline_id)
            statement = statement.where(VisualGenerationPlan.worldline_id == resolved)
        if status is not None:
            statement = statement.where(VisualGenerationPlan.status == status.value)
        statement = statement.order_by(VisualGenerationPlan.created_at.desc()).limit(200)
        return [self._plan_record(model) for model in self._session.scalars(statement)]

    def get_plan(self, world_id: uuid.UUID, plan_id: uuid.UUID) -> VisualGenerationPlanRead:
        return self._plan_record(self._plan_required(world_id, plan_id))

    def validate_plan(
        self,
        world_id: uuid.UUID,
        plan_id: uuid.UUID,
        *,
        include_restricted: bool = False,
    ) -> VisualGenerationPlanValidationResult:
        model = self._plan_required(world_id, plan_id)
        validation = self._validate_plan_model(model, include_restricted=include_restricted)
        model.validation_results_json = validation.model_dump(mode="json")
        model.status = (
            VisualGenerationPlanStatus.VALIDATED.value
            if validation.passed
            else VisualGenerationPlanStatus.VALIDATION_FAILED.value
        )
        self._session.flush()
        return validation

    def dry_run_plan(
        self,
        world_id: uuid.UUID,
        plan_id: uuid.UUID,
        *,
        include_restricted: bool = False,
    ) -> VisualGenerationDryRunResult:
        model = self._plan_required(world_id, plan_id)
        validation = self._validate_plan_model(model, include_restricted=include_restricted)
        mapped_request_json: dict[str, Any] = {}
        mapping_kind = validation.mapping_kind
        if validation.passed:
            provider = self._provider_model(model.provider_id)
            version = (
                self._session.get(VisualWorkflowTemplateVersion, model.workflow_template_version_id)
                if model.workflow_template_version_id is not None
                else None
            )
            mapping = map_provider_request(
                adapter_kind=ProviderAdapterKind(provider.adapter_kind),
                provider_key=provider.provider_key,
                template_payload_json={} if version is None else version.template_payload_json,
                slot_values=validation.normalized_slot_values_json,
                prompt_plan_json=model.prompt_plan_json,
                model_plan_json=model.model_plan_json,
                output_plan_json=model.output_plan_json,
            )
            validation = _merge_validation(validation, mapping.validation)
            mapped_request_json = mapping.request_json if mapping.validation.passed else {}
            mapping_kind = mapping.mapping_kind
        model.validation_results_json = validation.model_dump(mode="json")
        model.status = (
            VisualGenerationPlanStatus.DRY_RUN_SUCCEEDED.value
            if validation.passed
            else VisualGenerationPlanStatus.DRY_RUN_FAILED.value
        )
        self._session.flush()
        return VisualGenerationDryRunResult(
            plan_id=model.id,
            validation=validation,
            dry_run_status=model.status,
            mapping_kind=mapping_kind,
            mapped_request_json=mapped_request_json,
            provider_call_made=False,
        )

    def _validate_plan_model(
        self,
        model: VisualGenerationPlan,
        *,
        include_restricted: bool,
    ) -> VisualGenerationPlanValidationResult:
        issues: list[ValidationIssue] = []
        provider = self._provider_model(model.provider_id)
        issues.extend(
            validate_provider_adapter(
                ProviderKind(provider.provider_kind),
                ProviderAdapterKind(provider.adapter_kind),
            )
        )
        if provider.world_id is not None and provider.world_id != model.world_id:
            issues.append(_issue("provider_cross_world", "provider belongs to a different world"))
        if provider.status != ProviderIntegrationStatus.ACTIVE.value:
            issues.append(_issue("provider_not_active", "provider is not active"))
        template: VisualWorkflowTemplate | None = None
        version: VisualWorkflowTemplateVersion | None = None
        if model.workflow_template_id is not None:
            template = self._workflow_template_required(model.world_id, model.workflow_template_id)
            if template.status != VisualWorkflowTemplateStatus.ACTIVE.value:
                issues.append(_issue("template_not_active", "workflow template is not active"))
            if not include_restricted and template.visibility in RESTRICTED_VISIBILITIES:
                issues.append(_issue("template_not_visible", "workflow template is restricted"))
            if template.provider_id is not None and template.provider_id != model.provider_id:
                issues.append(
                    _issue("template_provider_mismatch", "workflow template provider mismatch")
                )
            if template.provider_kind != provider.provider_kind:
                issues.append(
                    _issue("template_kind_mismatch", "workflow template provider kind mismatch")
                )
            if template.adapter_kind != provider.adapter_kind:
                issues.append(
                    _issue("template_adapter_mismatch", "workflow template adapter mismatch")
                )
        if model.workflow_template_version_id is not None:
            version = self._session.get(
                VisualWorkflowTemplateVersion,
                model.workflow_template_version_id,
            )
            if version is None:
                issues.append(_issue("version_missing", "workflow template version not found"))
            elif (
                model.workflow_template_id is not None
                and version.template_id != model.workflow_template_id
            ):
                issues.append(
                    _issue(
                        "version_template_mismatch",
                        "workflow version does not belong to template",
                    )
                )
            elif version.validation_status != WorkflowTemplateVersionValidationStatus.VALID.value:
                issues.append(_issue("version_not_valid", "workflow template version is not valid"))
        if (
            ProviderAdapterKind(provider.adapter_kind) == ProviderAdapterKind.COMFYUI
            and version is None
        ):
            issues.append(
                _issue(
                    "comfyui_template_required",
                    "ComfyUI plans require a workflow template version",
                )
            )

        slot_values = slot_values_from_plan(
            prompt_plan_json=model.prompt_plan_json,
            model_plan_json=model.model_plan_json,
            output_plan_json=model.output_plan_json,
        )
        if version is not None:
            slot_validation = validate_slots(version.parameter_schema_json, slot_values)
            issues.extend(slot_validation.issues)
        for issue in self._validate_required_capabilities(provider.id, version):
            issues.append(issue)
        for issue in self._validate_plan_model_assets(model):
            issues.append(issue)
        for issue in self._validate_plan_profile_constraints(model):
            issues.append(issue)
        for reference in self._plan_reference_models(model.id):
            try:
                self._validate_reference(
                    model.world_id,
                    model.worldline_id,
                    VisualGenerationReferenceKind(reference.reference_kind),
                    reference.reference_id,
                    include_restricted=include_restricted,
                )
            except VisualGenerationValidationError as exc:
                issues.append(_issue("reference_invalid", str(exc), field="references"))
        for field_name, value in (
            ("prompt_plan_json", model.prompt_plan_json),
            ("model_plan_json", model.model_plan_json),
            ("output_plan_json", model.output_plan_json),
            ("source_context_json", model.source_context_json),
        ):
            issues.extend(leak_issues(value, field_name=field_name))
            issues.extend(reject_raw_workflow_payload(value, field_name=field_name))
        if not issues:
            mapping = map_provider_request(
                adapter_kind=ProviderAdapterKind(provider.adapter_kind),
                provider_key=provider.provider_key,
                template_payload_json={} if version is None else version.template_payload_json,
                slot_values=slot_values,
                prompt_plan_json=model.prompt_plan_json,
                model_plan_json=model.model_plan_json,
                output_plan_json=model.output_plan_json,
            )
            issues.extend(mapping.validation.issues)
            mapping_kind = mapping.mapping_kind
        else:
            mapping_kind = None
        return VisualGenerationPlanValidationResult(
            plan_id=model.id,
            passed=not any(issue.severity == ValidationSeverity.ERROR for issue in issues),
            issues=tuple(issues),
            normalized_slot_values_json=slot_values,
            mapping_kind=mapping_kind,
            provider_call_made=False,
        )

    def _validate_required_capabilities(
        self,
        provider_id: uuid.UUID,
        version: VisualWorkflowTemplateVersion | None,
    ) -> list[ValidationIssue]:
        if version is None:
            return []
        required = _required_capability_keys(version.required_capabilities_json)
        if not required:
            return []
        capabilities = {
            capability
            for capability in self._session.scalars(
                select(ProviderCapability.capability_key).where(
                    ProviderCapability.provider_integration_id == provider_id
                )
            )
        }
        missing = sorted(required.difference(capabilities))
        if not missing:
            return []
        return [
            _issue(
                "provider_capability_missing",
                f"provider is missing required capabilities: {', '.join(missing)}",
            )
        ]

    def _validate_plan_model_assets(self, plan: VisualGenerationPlan) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        checkpoint_raw = plan.model_plan_json.get("checkpoint_id")
        checkpoint_id = _uuid_from_plan(checkpoint_raw)
        checkpoint_asset: VisualModelAsset | None = None
        if checkpoint_raw is not None and checkpoint_id is None:
            issues.append(
                _issue("checkpoint_invalid_format", "checkpoint_id must be a valid UUID")
            )
        if checkpoint_id is not None:
            asset = self._model_asset_optional(plan.world_id, checkpoint_id)
            if asset is None or asset.inventory_kind != VisualModelInventoryKind.CHECKPOINT.value:
                issues.append(
                    _issue("checkpoint_invalid", "checkpoint_id is not a checkpoint asset")
                )
            elif asset.worldline_id is not None and asset.worldline_id != plan.worldline_id:
                issues.append(
                    _issue(
                        "checkpoint_worldline_mismatch",
                        "checkpoint asset is not valid for worldline",
                    )
                )
            else:
                checkpoint_asset = asset
        lora_ids, lora_format_issues = _uuid_list_from_plan_checked(
            plan.model_plan_json.get("lora_ids"),
            field_name="lora_ids",
        )
        issues.extend(lora_format_issues)
        for lora_id in lora_ids:
            asset = self._model_asset_optional(plan.world_id, lora_id)
            if asset is None or asset.inventory_kind != VisualModelInventoryKind.LORA.value:
                issues.append(
                    _issue("lora_invalid", "lora_ids must reference LoRA inventory assets")
                )
            elif asset.worldline_id is not None and asset.worldline_id != plan.worldline_id:
                issues.append(
                    _issue("lora_worldline_mismatch", "LoRA asset is not valid for worldline")
                )
            elif _base_models_conflict(checkpoint_asset, asset):
                issues.append(
                    _issue(
                        "lora_base_model_mismatch",
                        "LoRA compatible base models do not match selected checkpoint",
                    )
                )
        return issues

    def _validate_plan_profile_constraints(
        self,
        plan: VisualGenerationPlan,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        selected_lora_ids = set(_uuid_list_from_plan(plan.model_plan_json.get("lora_ids")))
        if not selected_lora_ids:
            return issues
        for character_id in _uuids(plan.character_ids_json):
            profile = self._profile_for_agent(plan.world_id, plan.worldline_id, character_id)
            if profile is None:
                continue
            allowed = set(_uuids(profile.allowed_lora_ids_json))
            banned = set(_uuids(profile.banned_lora_ids_json))
            if allowed and not selected_lora_ids.issubset(allowed):
                issues.append(
                    _issue("lora_not_allowed", "plan selected LoRA outside profile allowed set")
                )
            if selected_lora_ids.intersection(banned):
                issues.append(_issue("lora_banned", "plan selected a profile-banned LoRA"))
        return issues

    def _validate_template_pair(
        self,
        world_id: uuid.UUID,
        template_id: uuid.UUID | None,
        version_id: uuid.UUID | None,
    ) -> None:
        if template_id is None and version_id is not None:
            raise VisualGenerationValidationError("workflow_template_id is required with version")
        if template_id is None:
            return
        self._workflow_template_required(world_id, template_id)
        if version_id is not None:
            version = self._session.get(VisualWorkflowTemplateVersion, version_id)
            if version is None or version.template_id != template_id:
                raise VisualGenerationValidationError("workflow template version not found")

    def _validate_plan_payload(self, create: VisualGenerationPlanCreate) -> None:
        for field_name, value in (
            ("prompt_plan_json", create.prompt_plan_json),
            ("model_plan_json", create.model_plan_json),
            ("output_plan_json", create.output_plan_json),
            ("source_context_json", create.source_context_json),
        ):
            try:
                safe_json_or_raise(value, field_name=field_name)
            except ValueError as exc:
                raise VisualGenerationValidationError(str(exc)) from exc
            raw_issues = reject_raw_workflow_payload(value, field_name=field_name)
            if raw_issues:
                raise VisualGenerationValidationError(raw_issues[0].message)

    def _validate_model_asset_payload(self, create: VisualModelAssetCreate) -> None:
        self._validate_file_name(create.file_name)
        safe_json_or_raise(create.metadata_json, field_name="metadata_json")

    def _validate_version_json(self, create: WorkflowTemplateVersionCreate) -> None:
        for field_name, value in (
            ("parameter_schema_json", create.parameter_schema_json),
            ("required_capabilities_json", create.required_capabilities_json),
            ("allowed_asset_roles_json", create.allowed_asset_roles_json),
            ("safety_constraints_json", create.safety_constraints_json),
            ("template_payload_json", create.template_payload_json),
            ("validation_error_json", create.validation_error_json),
        ):
            safe_json_or_raise(value, field_name=field_name)

    def _validate_profile_assets(
        self,
        create: CharacterVisualGenerationProfileCreate,
        *,
        include_restricted: bool,
    ) -> None:
        for field_name, value in (
            ("prompt_fragments_json", create.prompt_fragments_json),
            ("negative_prompt_fragments_json", create.negative_prompt_fragments_json),
            ("outfit_policy_json", create.outfit_policy_json),
            ("pose_policy_json", create.pose_policy_json),
        ):
            safe_json_or_raise(value, field_name=field_name)
        if create.preferred_checkpoint_id is not None:
            checkpoint = self._model_asset_required(
                create.world_id,
                create.preferred_checkpoint_id,
                include_restricted=include_restricted,
            )
            if checkpoint.inventory_kind != VisualModelInventoryKind.CHECKPOINT.value:
                raise VisualGenerationValidationError("preferred checkpoint must be a checkpoint")
            if (
                checkpoint.worldline_id is not None
                and checkpoint.worldline_id != create.worldline_id
            ):
                raise VisualGenerationValidationError("checkpoint inventory worldline mismatch")
        for lora_id in set(
            create.allowed_lora_ids + create.default_lora_ids + create.banned_lora_ids
        ):
            lora = self._model_asset_required(
                create.world_id,
                lora_id,
                include_restricted=include_restricted,
            )
            if lora.inventory_kind != VisualModelInventoryKind.LORA.value:
                raise VisualGenerationValidationError("LoRA id must reference LoRA inventory")
            if lora.worldline_id is not None and lora.worldline_id != create.worldline_id:
                raise VisualGenerationValidationError("LoRA inventory worldline mismatch")
        for asset_id in create.reference_asset_ids:
            self._validate_media_asset_reference(
                create.world_id,
                create.worldline_id,
                asset_id,
                include_restricted=include_restricted,
            )
        for template_id in (
            create.default_workflow_template_id,
            create.expression_workflow_template_id,
            create.cg_workflow_template_id,
        ):
            if template_id is not None:
                template = self._workflow_template_required(create.world_id, template_id)
                if not include_restricted and template.visibility in RESTRICTED_VISIBILITIES:
                    raise VisualGenerationValidationError("workflow template is restricted")

    def _validate_reference(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        reference_kind: VisualGenerationReferenceKind,
        reference_id: uuid.UUID,
        *,
        include_restricted: bool,
    ) -> None:
        if reference_kind == VisualGenerationReferenceKind.MEDIA_ASSET:
            self._validate_media_asset_reference(
                world_id,
                worldline_id,
                reference_id,
                include_restricted=include_restricted,
            )
            return
        if reference_kind == VisualGenerationReferenceKind.MODEL_ASSET:
            asset = self._model_asset_required(
                world_id,
                reference_id,
                include_restricted=include_restricted,
            )
            if asset.worldline_id is not None and asset.worldline_id != worldline_id:
                raise VisualGenerationValidationError("model asset reference worldline mismatch")
            return
        if reference_kind == VisualGenerationReferenceKind.WORKFLOW_TEMPLATE:
            template = self._workflow_template_required(world_id, reference_id)
            if not include_restricted and template.visibility in RESTRICTED_VISIBILITIES:
                raise VisualGenerationValidationError("workflow template reference is restricted")
            return
        if reference_kind == VisualGenerationReferenceKind.CHARACTER_PROFILE:
            profile = self._character_profile_required(
                world_id,
                reference_id,
                include_restricted=include_restricted,
            )
            if profile.worldline_id != worldline_id:
                raise VisualGenerationValidationError(
                    "character profile reference worldline mismatch"
                )
            return
        if reference_kind == VisualGenerationReferenceKind.SCENE:
            self._validate_scene(world_id, reference_id)
            return
        if reference_kind == VisualGenerationReferenceKind.AGENT:
            self._validate_agent(world_id, reference_id)

    def _validate_media_asset_reference(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        include_restricted: bool,
    ) -> MediaAsset:
        asset = self._session.get(MediaAsset, asset_id)
        if (
            asset is None
            or asset.world_id != world_id
            or asset.worldline_id != worldline_id
            or asset.status == MediaAssetStatus.DELETED.value
        ):
            raise VisualGenerationValidationError("reference asset must belong to plan worldline")
        if not include_restricted and asset.visibility in RESTRICTED_MEDIA_VISIBILITIES:
            raise VisualGenerationValidationError("reference asset is restricted")
        return asset

    def _workflow_template_required(
        self,
        world_id: uuid.UUID,
        template_id: uuid.UUID,
    ) -> VisualWorkflowTemplate:
        model = self._session.get(VisualWorkflowTemplate, template_id)
        if (
            model is None
            or model.world_id != world_id
            or model.status == VisualWorkflowTemplateStatus.DELETED.value
        ):
            raise VisualGenerationNotFoundError("workflow template not found")
        return model

    def _model_asset_required(
        self,
        world_id: uuid.UUID,
        model_asset_id: uuid.UUID,
        *,
        include_restricted: bool,
    ) -> VisualModelAsset:
        model = self._model_asset_optional(world_id, model_asset_id)
        if model is None:
            raise VisualGenerationNotFoundError("visual model asset not found")
        if not include_restricted and model.visibility in RESTRICTED_VISIBILITIES:
            raise VisualGenerationNotFoundError("visual model asset not found")
        return model

    def _model_asset_optional(
        self,
        world_id: uuid.UUID,
        model_asset_id: uuid.UUID,
    ) -> VisualModelAsset | None:
        model = self._session.get(VisualModelAsset, model_asset_id)
        if model is None or model.world_id != world_id:
            return None
        return model

    def _character_profile_required(
        self,
        world_id: uuid.UUID,
        profile_id: uuid.UUID,
        *,
        include_restricted: bool,
    ) -> CharacterVisualGenerationProfile:
        model = self._session.get(CharacterVisualGenerationProfile, profile_id)
        if (
            model is None
            or model.world_id != world_id
            or model.review_status == CharacterVisualProfileReviewStatus.DELETED.value
        ):
            raise VisualGenerationNotFoundError("character visual generation profile not found")
        if not include_restricted and model.visibility in RESTRICTED_VISIBILITIES:
            raise VisualGenerationNotFoundError("character visual generation profile not found")
        return model

    def _plan_required(self, world_id: uuid.UUID, plan_id: uuid.UUID) -> VisualGenerationPlan:
        model = self._session.get(VisualGenerationPlan, plan_id)
        if (
            model is None
            or model.world_id != world_id
            or model.status == VisualGenerationPlanStatus.DELETED.value
        ):
            raise VisualGenerationNotFoundError("visual generation plan not found")
        return model

    def _provider_read(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
        *,
        platform_admin: bool,
    ) -> object:
        provider = ProviderRegistryService(self._session).get_provider(
            world_id,
            provider_id,
            include_hidden=platform_admin,
            platform_admin=platform_admin,
        )
        if provider is None:
            raise VisualGenerationValidationError("provider integration not found")
        return provider

    def _provider_model(self, provider_id: uuid.UUID) -> ProviderIntegration:
        try:
            return ProviderRegistryService(self._session).internal_model(provider_id)
        except ProviderNotFoundError as exc:
            raise VisualGenerationValidationError("provider integration not found") from exc

    def _provider_adapter_issues_or_raise(
        self,
        provider_kind: ProviderKind,
        adapter_kind: ProviderAdapterKind,
    ) -> None:
        issues = validate_provider_adapter(provider_kind, adapter_kind)
        if issues:
            raise VisualGenerationValidationError(issues[0].message)

    def _worldline_id(self, world_id: uuid.UUID, worldline_id: uuid.UUID) -> uuid.UUID:
        try:
            return worldline_or_404(self._session, world_id, worldline_id).id
        except ValueError as exc:
            raise VisualGenerationValidationError("worldline not found") from exc

    def _validate_world(self, world_id: uuid.UUID) -> None:
        if self._session.get(World, world_id) is None:
            raise VisualGenerationValidationError("world not found")

    def _validate_agent(self, world_id: uuid.UUID, agent_id: uuid.UUID) -> None:
        agent = self._session.get(Agent, agent_id)
        if agent is None or agent.world_id != world_id:
            raise VisualGenerationValidationError("agent not found")

    def _validate_scene(self, world_id: uuid.UUID, scene_id: uuid.UUID | None) -> None:
        if scene_id is None:
            return
        scene = self._session.get(Scene, scene_id)
        if scene is None or scene.world_id != world_id:
            raise VisualGenerationValidationError("scene not found")

    def _validate_file_name(self, file_name: str | None) -> None:
        if file_name is None:
            return
        if "/" in file_name or "\\" in file_name or ":" in file_name:
            raise VisualGenerationValidationError("file_name must not contain local path details")

    def _plan_reference_models(self, plan_id: uuid.UUID) -> list[VisualGenerationPlanReference]:
        statement = (
            select(VisualGenerationPlanReference)
            .where(VisualGenerationPlanReference.plan_id == plan_id)
            .order_by(VisualGenerationPlanReference.display_order)
        )
        return list(self._session.scalars(statement))

    def _profile_for_agent(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
    ) -> CharacterVisualGenerationProfile | None:
        return self._session.scalars(
            select(CharacterVisualGenerationProfile).where(
                CharacterVisualGenerationProfile.world_id == world_id,
                CharacterVisualGenerationProfile.worldline_id == worldline_id,
                CharacterVisualGenerationProfile.agent_id == agent_id,
                CharacterVisualGenerationProfile.review_status
                != CharacterVisualProfileReviewStatus.DELETED.value,
            )
        ).first()

    def _plan_record(self, model: VisualGenerationPlan) -> VisualGenerationPlanRead:
        return _plan_record(model, references=self._plan_reference_records(model.id))

    def _plan_reference_records(
        self,
        plan_id: uuid.UUID,
    ) -> tuple[VisualGenerationPlanReferenceRead, ...]:
        return tuple(
            _plan_reference_record(model) for model in self._plan_reference_models(plan_id)
        )


def _workflow_template_record(model: VisualWorkflowTemplate) -> WorkflowTemplateRead:
    return WorkflowTemplateRead(
        id=model.id,
        world_id=model.world_id,
        provider_id=model.provider_id,
        provider_kind=ProviderKind(model.provider_kind),
        adapter_kind=ProviderAdapterKind(model.adapter_kind),
        workflow_key=model.workflow_key,
        display_name=model.display_name,
        intent=VisualWorkflowIntent(model.intent),
        status=VisualWorkflowTemplateStatus(model.status),
        visibility=VisualGenerationVisibility(model.visibility),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _workflow_template_version_record(
    model: VisualWorkflowTemplateVersion,
) -> WorkflowTemplateVersionRead:
    return WorkflowTemplateVersionRead(
        id=model.id,
        template_id=model.template_id,
        version=model.version,
        parameter_schema_json=model.parameter_schema_json,
        required_capabilities_json=model.required_capabilities_json,
        allowed_asset_roles_json=model.allowed_asset_roles_json,
        safety_constraints_json=model.safety_constraints_json,
        template_payload_configured=bool(model.template_payload_json),
        validation_status=WorkflowTemplateVersionValidationStatus(model.validation_status),
        validation_error_json=model.validation_error_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _model_asset_record(model: VisualModelAsset) -> VisualModelAssetRead:
    return VisualModelAssetRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        provider_id=model.provider_id,
        inventory_kind=VisualModelInventoryKind(model.inventory_kind),
        display_name=model.display_name,
        provider_model_name=model.provider_model_name,
        file_name=model.file_name,
        trigger_words=tuple(model.trigger_words_json),
        compatible_base_models=tuple(model.compatible_base_models_json),
        recommended_weight=model.recommended_weight,
        style_tags=tuple(model.style_tags_json),
        character_tags=tuple(model.character_tags_json),
        visibility=VisualGenerationVisibility(model.visibility),
        source_note=model.source_note,
        metadata_json=model.metadata_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _character_profile_record(
    model: CharacterVisualGenerationProfile,
) -> CharacterVisualGenerationProfileRead:
    return CharacterVisualGenerationProfileRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        agent_id=model.agent_id,
        preferred_checkpoint_id=model.preferred_checkpoint_id,
        allowed_lora_ids=_uuids(model.allowed_lora_ids_json),
        default_lora_ids=_uuids(model.default_lora_ids_json),
        banned_lora_ids=_uuids(model.banned_lora_ids_json),
        prompt_fragments_json=model.prompt_fragments_json,
        negative_prompt_fragments_json=model.negative_prompt_fragments_json,
        reference_asset_ids=_uuids(model.reference_asset_ids_json),
        default_workflow_template_id=model.default_workflow_template_id,
        expression_workflow_template_id=model.expression_workflow_template_id,
        cg_workflow_template_id=model.cg_workflow_template_id,
        outfit_policy_json=model.outfit_policy_json,
        pose_policy_json=model.pose_policy_json,
        review_status=CharacterVisualProfileReviewStatus(model.review_status),
        visibility=VisualGenerationVisibility(model.visibility),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _plan_record(
    model: VisualGenerationPlan,
    *,
    references: tuple[VisualGenerationPlanReferenceRead, ...],
) -> VisualGenerationPlanRead:
    return VisualGenerationPlanRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        intent=VisualWorkflowIntent(model.intent),
        provider_id=model.provider_id,
        workflow_template_id=model.workflow_template_id,
        workflow_template_version_id=model.workflow_template_version_id,
        status=VisualGenerationPlanStatus(model.status),
        character_ids=_uuids(model.character_ids_json),
        scene_id=model.scene_id,
        prompt_plan_json=model.prompt_plan_json,
        model_plan_json=model.model_plan_json,
        output_plan_json=model.output_plan_json,
        validation_results_json=model.validation_results_json,
        source_context_json=model.source_context_json,
        model_invocation_id=model.model_invocation_id,
        media_job_id=model.media_job_id,
        output_media_asset_id=model.output_media_asset_id,
        references=references,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _plan_reference_record(
    model: VisualGenerationPlanReference,
) -> VisualGenerationPlanReferenceRead:
    return VisualGenerationPlanReferenceRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        plan_id=model.plan_id,
        reference_kind=VisualGenerationReferenceKind(model.reference_kind),
        reference_id=model.reference_id,
        reference_role=VisualGenerationReferenceRole(model.reference_role),
        display_order=model.display_order,
        metadata_json=model.metadata_json,
        created_at=model.created_at,
    )


def _required_capability_keys(value: dict[str, Any]) -> set[str]:
    raw = value.get("capabilities") or value.get("required") or value.get("capability_keys")
    if isinstance(raw, list | tuple):
        return {str(item).strip() for item in raw if str(item).strip()}
    return set()


def _uuid_strings(values: tuple[uuid.UUID, ...]) -> list[str]:
    return [str(value) for value in values]


def _uuids(values: list[str]) -> tuple[uuid.UUID, ...]:
    return tuple(uuid.UUID(value) for value in values)


def _uuid_from_plan(value: object) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _uuid_list_from_plan(value: object) -> tuple[uuid.UUID, ...]:
    if not isinstance(value, list | tuple):
        return ()
    result: list[uuid.UUID] = []
    for item in value:
        parsed = _uuid_from_plan(item)
        if parsed is not None:
            result.append(parsed)
    return tuple(result)


def _uuid_list_from_plan_checked(
    value: object,
    *,
    field_name: str,
) -> tuple[tuple[uuid.UUID, ...], list[ValidationIssue]]:
    if value is None:
        return (), []
    if not isinstance(value, list | tuple):
        return (), [_issue(f"{field_name}_invalid_format", f"{field_name} must be a list")]
    result: list[uuid.UUID] = []
    issues: list[ValidationIssue] = []
    for index, item in enumerate(value):
        parsed = _uuid_from_plan(item)
        if parsed is None:
            issues.append(
                _issue(
                    f"{field_name}_invalid_format",
                    f"{field_name}[{index}] must be a valid UUID",
                )
            )
        else:
            result.append(parsed)
    return tuple(result), issues


def _base_models_conflict(
    checkpoint: VisualModelAsset | None,
    lora: VisualModelAsset,
) -> bool:
    if checkpoint is None:
        return False
    checkpoint_models = {
        str(value).strip().lower()
        for value in checkpoint.compatible_base_models_json
        if str(value).strip()
    }
    lora_models = {
        str(value).strip().lower()
        for value in lora.compatible_base_models_json
        if str(value).strip()
    }
    return bool(checkpoint_models and lora_models and checkpoint_models.isdisjoint(lora_models))


def _merge_validation(
    first: VisualGenerationPlanValidationResult,
    second: VisualGenerationPlanValidationResult,
) -> VisualGenerationPlanValidationResult:
    issues = first.issues + second.issues
    return VisualGenerationPlanValidationResult(
        plan_id=first.plan_id,
        passed=first.passed and second.passed,
        issues=issues,
        normalized_slot_values_json=first.normalized_slot_values_json,
        mapping_kind=second.mapping_kind or first.mapping_kind,
        provider_call_made=False,
    )


def _issue(
    code: str,
    message: str,
    *,
    field: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message=message,
        field=field,
        severity=ValidationSeverity.ERROR,
    )
