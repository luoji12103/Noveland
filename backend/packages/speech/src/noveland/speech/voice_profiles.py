from __future__ import annotations

import uuid

from noveland.agents.models import Agent
from noveland.media.contracts import MediaAssetKind
from noveland.media.models import MediaAsset
from noveland.providers.models import ProviderIntegration
from noveland.speech.contracts import (
    AgentVoiceProfileBindingCreate,
    AgentVoiceProfileBindingRead,
    VoiceBindingRole,
    VoiceConsentStatus,
    VoiceKind,
    VoiceProfileCreate,
    VoiceProfileOwnerKind,
    VoiceProfileRead,
    VoiceProfileStatus,
    VoiceProfileUpdate,
    VoiceProfileVisibility,
)
from noveland.speech.models import AgentVoiceProfileBinding, VoiceProfile
from noveland.worlds.models import World
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class SpeechValidationError(ValueError):
    pass


class SpeechNotFoundError(LookupError):
    pass


class VoiceProfileService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_profile(self, create: VoiceProfileCreate) -> VoiceProfileRead:
        self._validate_world(create.world_id)
        worldline_id = self._worldline_id_nullable(create.world_id, create.worldline_id)
        self._validate_agent(create.world_id, create.owner_agent_id)
        self._validate_provider(create.world_id, create.provider_integration_id)
        self._validate_reference_asset(create.world_id, worldline_id, create.reference_asset_id)
        model = VoiceProfile(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=worldline_id,
            profile_key=create.profile_key,
            display_name=create.display_name,
            description=create.description,
            status=create.status.value,
            visibility=create.visibility.value,
            owner_kind=create.owner_kind.value,
            owner_agent_id=create.owner_agent_id,
            provider_integration_id=create.provider_integration_id,
            provider_voice_id=create.provider_voice_id,
            default_language=create.default_language,
            supported_languages_json=create.supported_languages,
            voice_kind=create.voice_kind.value,
            reference_asset_id=create.reference_asset_id,
            consent_status=create.consent_status.value,
            usage_policy_json=create.usage_policy_json,
            metadata_json=create.metadata_json,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise SpeechValidationError("voice profile already exists") from exc
        self._session.refresh(model)
        return _profile_record(model)

    def update_profile(
        self,
        world_id: uuid.UUID,
        profile_id: uuid.UUID,
        update: VoiceProfileUpdate,
    ) -> VoiceProfileRead:
        model = self._profile_required(world_id, profile_id)
        if update.display_name is not None:
            model.display_name = update.display_name
        if "description" in update.model_fields_set:
            model.description = update.description
        if update.status is not None:
            model.status = update.status.value
        if update.visibility is not None:
            model.visibility = update.visibility.value
        if "provider_integration_id" in update.model_fields_set:
            self._validate_provider(world_id, update.provider_integration_id)
            model.provider_integration_id = update.provider_integration_id
        if "provider_voice_id" in update.model_fields_set:
            model.provider_voice_id = update.provider_voice_id
        if "default_language" in update.model_fields_set:
            model.default_language = update.default_language
        if update.supported_languages is not None:
            model.supported_languages_json = update.supported_languages
        if "reference_asset_id" in update.model_fields_set:
            self._validate_reference_asset(world_id, model.worldline_id, update.reference_asset_id)
            model.reference_asset_id = update.reference_asset_id
        if update.consent_status is not None:
            model.consent_status = update.consent_status.value
        if update.usage_policy_json is not None:
            model.usage_policy_json = update.usage_policy_json
        if update.metadata_json is not None:
            model.metadata_json = update.metadata_json
        self._session.flush()
        self._session.refresh(model)
        return _profile_record(model)

    def delete_profile(self, world_id: uuid.UUID, profile_id: uuid.UUID) -> None:
        model = self._profile_required(world_id, profile_id)
        model.status = VoiceProfileStatus.DELETED.value
        self._session.flush()

    def get_profile(
        self,
        world_id: uuid.UUID,
        profile_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> VoiceProfileRead | None:
        model = self._session.get(VoiceProfile, profile_id)
        if model is None or model.world_id != world_id:
            return None
        if not include_deleted and model.status == VoiceProfileStatus.DELETED.value:
            return None
        return _profile_record(model)

    def list_profiles(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
        include_world_level: bool = True,
    ) -> list[VoiceProfileRead]:
        resolved = self._worldline_id_nullable(world_id, worldline_id)
        statement = select(VoiceProfile).where(
            VoiceProfile.world_id == world_id,
            VoiceProfile.status != VoiceProfileStatus.DELETED.value,
        )
        if resolved is not None:
            if include_world_level:
                statement = statement.where(
                    (VoiceProfile.worldline_id == resolved) | (VoiceProfile.worldline_id.is_(None))
                )
            else:
                statement = statement.where(VoiceProfile.worldline_id == resolved)
        statement = statement.order_by(VoiceProfile.profile_key)
        return [_profile_record(model) for model in self._session.scalars(statement).all()]

    def bind_agent_voice(
        self,
        create: AgentVoiceProfileBindingCreate,
    ) -> AgentVoiceProfileBindingRead:
        worldline_id = self._worldline_id_nullable(create.world_id, create.worldline_id)
        self._validate_agent(create.world_id, create.agent_id)
        profile = self._profile_required(create.world_id, create.voice_profile_id)
        if profile.worldline_id is not None and profile.worldline_id != worldline_id:
            raise SpeechValidationError("voice profile worldline must match binding worldline")
        if create.is_default:
            self._clear_existing_default(create.world_id, worldline_id, create.agent_id)
        model = AgentVoiceProfileBinding(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=worldline_id,
            agent_id=create.agent_id,
            voice_profile_id=create.voice_profile_id,
            binding_role=create.binding_role.value,
            priority=create.priority,
            is_default=create.is_default,
            style_overrides_json=create.style_overrides_json,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise SpeechValidationError("agent voice binding already exists") from exc
        self._session.refresh(model)
        return _binding_record(model)

    def list_agent_bindings(
        self,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
    ) -> list[AgentVoiceProfileBindingRead]:
        resolved = self._worldline_id_nullable(world_id, worldline_id)
        self._validate_agent(world_id, agent_id)
        statement = (
            select(AgentVoiceProfileBinding)
            .where(
                AgentVoiceProfileBinding.world_id == world_id,
                AgentVoiceProfileBinding.agent_id == agent_id,
            )
            .order_by(
                AgentVoiceProfileBinding.is_default.desc(),
                AgentVoiceProfileBinding.priority,
                AgentVoiceProfileBinding.created_at,
            )
        )
        if resolved is not None:
            statement = statement.where(
                (AgentVoiceProfileBinding.worldline_id == resolved)
                | (AgentVoiceProfileBinding.worldline_id.is_(None))
            )
        return [_binding_record(model) for model in self._session.scalars(statement).all()]

    def delete_agent_binding(
        self,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
        binding_id: uuid.UUID,
    ) -> None:
        model = self._session.get(AgentVoiceProfileBinding, binding_id)
        if model is None or model.world_id != world_id or model.agent_id != agent_id:
            raise SpeechNotFoundError("agent voice binding not found")
        self._session.delete(model)
        self._session.flush()

    def resolve_agent_default(
        self,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
    ) -> tuple[VoiceProfileRead, AgentVoiceProfileBindingRead | None]:
        bindings = self.list_agent_bindings(world_id, agent_id, worldline_id=worldline_id)
        if not bindings:
            raise SpeechValidationError("agent has no voice profile binding")
        default = next((binding for binding in bindings if binding.is_default), bindings[0])
        profile = self.get_profile(world_id, default.voice_profile_id)
        if profile is None:
            raise SpeechValidationError("default voice profile is unavailable")
        return profile, default

    def _clear_existing_default(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        agent_id: uuid.UUID,
    ) -> None:
        for model in self._session.scalars(
            select(AgentVoiceProfileBinding).where(
                AgentVoiceProfileBinding.world_id == world_id,
                AgentVoiceProfileBinding.worldline_id == worldline_id,
                AgentVoiceProfileBinding.agent_id == agent_id,
                AgentVoiceProfileBinding.is_default.is_(True),
            )
        ):
            model.is_default = False

    def _profile_required(self, world_id: uuid.UUID, profile_id: uuid.UUID) -> VoiceProfile:
        model = self._session.get(VoiceProfile, profile_id)
        if model is None or model.world_id != world_id or model.status == "deleted":
            raise SpeechNotFoundError("voice profile not found")
        return model

    def _validate_world(self, world_id: uuid.UUID) -> None:
        if self._session.get(World, world_id) is None:
            raise SpeechValidationError("world not found")

    def _worldline_id_nullable(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
    ) -> uuid.UUID | None:
        if worldline_id is None:
            return None
        try:
            return worldline_or_404(self._session, world_id, worldline_id).id
        except ValueError as exc:
            raise SpeechValidationError("worldline not found") from exc

    def _validate_agent(self, world_id: uuid.UUID, agent_id: uuid.UUID | None) -> None:
        if agent_id is None:
            return
        agent = self._session.get(Agent, agent_id)
        if agent is None or agent.world_id != world_id:
            raise SpeechValidationError("agent must belong to voice profile world")

    def _validate_provider(self, world_id: uuid.UUID, provider_id: uuid.UUID | None) -> None:
        if provider_id is None:
            return
        provider = self._session.get(ProviderIntegration, provider_id)
        if provider is None or (provider.world_id is not None and provider.world_id != world_id):
            raise SpeechValidationError("provider integration must belong to voice profile world")

    def _validate_reference_asset(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        asset_id: uuid.UUID | None,
    ) -> None:
        if asset_id is None:
            return
        asset = self._session.get(MediaAsset, asset_id)
        if asset is None or asset.world_id != world_id or asset.asset_kind != MediaAssetKind.AUDIO:
            raise SpeechValidationError("voice reference asset must be an audio asset")
        if worldline_id is not None and asset.worldline_id != worldline_id:
            raise SpeechValidationError("voice reference asset must match profile worldline")


def _profile_record(model: VoiceProfile) -> VoiceProfileRead:
    return VoiceProfileRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        profile_key=model.profile_key,
        display_name=model.display_name,
        description=model.description,
        status=VoiceProfileStatus(model.status),
        visibility=VoiceProfileVisibility(model.visibility),
        owner_kind=VoiceProfileOwnerKind(model.owner_kind),
        owner_agent_id=model.owner_agent_id,
        provider_integration_id=model.provider_integration_id,
        provider_voice_id=model.provider_voice_id,
        default_language=model.default_language,
        supported_languages=list(model.supported_languages_json),
        voice_kind=VoiceKind(model.voice_kind),
        reference_asset_id=model.reference_asset_id,
        consent_status=VoiceConsentStatus(model.consent_status),
        usage_policy_json=dict(model.usage_policy_json),
        metadata_json=dict(model.metadata_json),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _binding_record(model: AgentVoiceProfileBinding) -> AgentVoiceProfileBindingRead:
    return AgentVoiceProfileBindingRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        agent_id=model.agent_id,
        voice_profile_id=model.voice_profile_id,
        binding_role=VoiceBindingRole(model.binding_role),
        priority=model.priority,
        is_default=model.is_default,
        style_overrides_json=dict(model.style_overrides_json),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
