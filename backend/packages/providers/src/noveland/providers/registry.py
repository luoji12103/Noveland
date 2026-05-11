from __future__ import annotations

import uuid

from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderCapabilityCreate,
    ProviderCapabilityRead,
    ProviderIntegrationCreate,
    ProviderIntegrationListFilters,
    ProviderIntegrationRead,
    ProviderIntegrationStatus,
    ProviderIntegrationUpdate,
    ProviderKind,
    ProviderScopeKind,
    ProviderVisibility,
)
from noveland.providers.models import ProviderCapability, ProviderIntegration
from noveland.providers.routing import (
    ProviderRoutingError,
    validate_provider_adapter_compatibility,
)
from noveland.worlds.models import World
from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

ADMIN_VISIBLE = {ProviderVisibility.PRIVATE.value, ProviderVisibility.WORLD_ADMIN.value}
PLATFORM_VISIBLE = {
    ProviderVisibility.PRIVATE.value,
    ProviderVisibility.WORLD_ADMIN.value,
    ProviderVisibility.DEVELOPER_ONLY.value,
    ProviderVisibility.HIDDEN.value,
}


class ProviderValidationError(ValueError):
    pass


class ProviderNotFoundError(LookupError):
    pass


class ProviderRegistryService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_provider(self, create: ProviderIntegrationCreate) -> ProviderIntegrationRead:
        self._validate_world(create.world_id)
        self._validate_compatibility(create.provider_kind, create.adapter_kind)
        model = ProviderIntegration(
            id=uuid.uuid4(),
            world_id=create.world_id,
            scope_kind=create.scope_kind.value,
            scope_key=_scope_key(create.scope_kind, create.world_id),
            provider_kind=create.provider_kind.value,
            adapter_kind=create.adapter_kind.value,
            provider_key=create.provider_key,
            display_name=create.display_name,
            base_url=create.base_url,
            auth_ref=create.auth_ref,
            config_json=create.config_json,
            default_params_json=create.default_params_json,
            status=create.status.value,
            visibility=create.visibility.value,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise ProviderValidationError("provider integration already exists") from exc
        self.update_capabilities(model.id, create.capabilities)
        self._session.refresh(model)
        return _integration_record(model)

    def update_provider(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
        update: ProviderIntegrationUpdate,
        *,
        platform_admin: bool = False,
    ) -> ProviderIntegrationRead:
        model = self._required(world_id, provider_id, platform_admin=platform_admin)
        if update.display_name is not None:
            model.display_name = update.display_name
        if "base_url" in update.model_fields_set:
            model.base_url = update.base_url
        if "auth_ref" in update.model_fields_set:
            model.auth_ref = update.auth_ref
        if update.config_json is not None:
            model.config_json = update.config_json
        if update.default_params_json is not None:
            model.default_params_json = update.default_params_json
        if update.status is not None:
            model.status = update.status.value
        if update.visibility is not None:
            model.visibility = update.visibility.value
        if update.capabilities is not None:
            self.update_capabilities(model.id, update.capabilities)
        self._session.flush()
        self._session.refresh(model)
        return _integration_record(model)

    def delete_provider(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
        *,
        platform_admin: bool = False,
    ) -> None:
        model = self._required(world_id, provider_id, platform_admin=platform_admin)
        model.status = ProviderIntegrationStatus.DELETED.value
        self._session.flush()

    def get_provider(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
        *,
        include_hidden: bool = False,
        platform_admin: bool = False,
    ) -> ProviderIntegrationRead | None:
        model = self._visible_provider_or_none(
            world_id,
            provider_id,
            include_hidden=include_hidden,
            platform_admin=platform_admin,
        )
        return None if model is None else _integration_record(model)

    def list_providers(
        self,
        world_id: uuid.UUID,
        filters: ProviderIntegrationListFilters,
        *,
        platform_admin: bool = False,
    ) -> list[ProviderIntegrationRead]:
        statement = select(ProviderIntegration)
        if filters.scope_kind is not None:
            if filters.scope_kind == ProviderScopeKind.GLOBAL:
                statement = statement.where(
                    ProviderIntegration.scope_kind == ProviderScopeKind.GLOBAL.value
                )
            else:
                statement = statement.where(ProviderIntegration.world_id == world_id)
        else:
            statement = statement.where(ProviderIntegration.scope_key.in_(_scope_keys(world_id)))
            if not filters.include_global:
                statement = statement.where(ProviderIntegration.world_id == world_id)
        statement = _apply_visibility(statement, filters.include_hidden, platform_admin)
        if filters.provider_kind is not None:
            statement = statement.where(
                ProviderIntegration.provider_kind == filters.provider_kind.value
            )
        if filters.adapter_kind is not None:
            statement = statement.where(
                ProviderIntegration.adapter_kind == filters.adapter_kind.value
            )
        if filters.status is not None:
            statement = statement.where(ProviderIntegration.status == filters.status.value)
        if filters.visibility is not None:
            statement = statement.where(ProviderIntegration.visibility == filters.visibility.value)
        if filters.capability_key is not None:
            statement = statement.where(
                select(ProviderCapability.id)
                .where(
                    ProviderCapability.provider_integration_id == ProviderIntegration.id,
                    ProviderCapability.capability_key == filters.capability_key,
                )
                .exists()
            )
        statement = statement.order_by(
            ProviderIntegration.scope_kind.desc(),
            ProviderIntegration.provider_key,
        ).limit(filters.limit)
        return [_integration_record(model) for model in self._session.scalars(statement).all()]

    def resolve_provider_for_capability(
        self,
        world_id: uuid.UUID,
        *,
        provider_kind: ProviderKind | None = None,
        capability_key: str | None = None,
        provider_id: uuid.UUID | None = None,
    ) -> ProviderIntegrationRead:
        if provider_id is not None:
            provider = self.get_provider(world_id, provider_id, platform_admin=True)
            if provider is None or provider.status != ProviderIntegrationStatus.ACTIVE:
                raise ProviderNotFoundError("provider integration not found")
            return provider
        statement = select(ProviderIntegration).where(
            ProviderIntegration.scope_key.in_(_scope_keys(world_id)),
            ProviderIntegration.status == ProviderIntegrationStatus.ACTIVE.value,
        )
        if provider_kind is not None:
            statement = statement.where(ProviderIntegration.provider_kind == provider_kind.value)
        if capability_key is not None:
            statement = statement.where(
                select(ProviderCapability.id)
                .where(
                    ProviderCapability.provider_integration_id == ProviderIntegration.id,
                    ProviderCapability.capability_key == capability_key,
                )
                .exists()
            )
        statement = statement.order_by(
            (ProviderIntegration.scope_kind == ProviderScopeKind.WORLD.value).desc(),
            ProviderIntegration.provider_key,
        ).limit(1)
        model = self._session.scalars(statement).first()
        if model is None:
            raise ProviderNotFoundError("provider integration not found")
        return _integration_record(model)

    def list_capabilities(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
        *,
        platform_admin: bool = False,
    ) -> list[ProviderCapabilityRead]:
        self._required(world_id, provider_id, platform_admin=platform_admin)
        return [
            _capability_record(model)
            for model in self._session.scalars(
                select(ProviderCapability)
                .where(ProviderCapability.provider_integration_id == provider_id)
                .order_by(ProviderCapability.capability_key)
            ).all()
        ]

    def update_capabilities(
        self,
        provider_id: uuid.UUID,
        capabilities: tuple[ProviderCapabilityCreate, ...],
    ) -> list[ProviderCapabilityRead]:
        self._session.query(ProviderCapability).filter(
            ProviderCapability.provider_integration_id == provider_id
        ).delete(synchronize_session=False)
        records: list[ProviderCapabilityRead] = []
        for capability in capabilities:
            model = ProviderCapability(
                id=uuid.uuid4(),
                provider_integration_id=provider_id,
                capability_key=capability.capability_key,
                capability_json=capability.capability_json,
            )
            self._session.add(model)
            self._session.flush()
            self._session.refresh(model)
            records.append(_capability_record(model))
        return records

    def internal_model(self, provider_id: uuid.UUID) -> ProviderIntegration:
        model = self._session.get(ProviderIntegration, provider_id)
        if model is None:
            raise ProviderNotFoundError("provider integration not found")
        return model

    def _required(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
        *,
        platform_admin: bool,
    ) -> ProviderIntegration:
        model = self._session.get(ProviderIntegration, provider_id)
        if model is None:
            raise ProviderNotFoundError("provider integration not found")
        if model.scope_kind == ProviderScopeKind.GLOBAL.value and not platform_admin:
            raise ProviderNotFoundError("provider integration not found")
        if model.world_id is not None and model.world_id != world_id:
            raise ProviderNotFoundError("provider integration not found")
        return model

    def _visible_provider_or_none(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
        *,
        include_hidden: bool,
        platform_admin: bool,
    ) -> ProviderIntegration | None:
        model = self._session.get(ProviderIntegration, provider_id)
        if model is None:
            return None
        if model.scope_kind == ProviderScopeKind.GLOBAL.value and not platform_admin:
            return None
        if model.world_id is not None and model.world_id != world_id:
            return None
        allowed = PLATFORM_VISIBLE if platform_admin else ADMIN_VISIBLE
        if model.visibility not in allowed:
            return None
        if model.visibility == ProviderVisibility.HIDDEN.value and not (
            platform_admin and include_hidden
        ):
            return None
        return model

    def _validate_world(self, world_id: uuid.UUID | None) -> None:
        if world_id is not None and self._session.get(World, world_id) is None:
            raise ProviderValidationError("provider world not found")

    def _validate_compatibility(
        self,
        provider_kind: ProviderKind,
        adapter_kind: ProviderAdapterKind,
    ) -> None:
        try:
            validate_provider_adapter_compatibility(provider_kind, adapter_kind)
        except ProviderRoutingError as exc:
            raise ProviderValidationError(str(exc)) from exc


def _scope_key(scope_kind: ProviderScopeKind, world_id: uuid.UUID | None) -> str:
    if scope_kind == ProviderScopeKind.GLOBAL:
        return "global"
    if world_id is None:
        raise ProviderValidationError("world providers require world_id")
    return f"world:{world_id}"


def _scope_keys(world_id: uuid.UUID) -> tuple[str, str]:
    return ("global", f"world:{world_id}")


def _apply_visibility(
    statement: Select[tuple[ProviderIntegration]],
    include_hidden: bool,
    platform_admin: bool,
) -> Select[tuple[ProviderIntegration]]:
    allowed = PLATFORM_VISIBLE if platform_admin else ADMIN_VISIBLE
    statement = statement.where(ProviderIntegration.visibility.in_(allowed))
    if not (platform_admin and include_hidden):
        statement = statement.where(
            ProviderIntegration.visibility != ProviderVisibility.HIDDEN.value
        )
    return statement


def _integration_record(model: ProviderIntegration) -> ProviderIntegrationRead:
    return ProviderIntegrationRead(
        id=model.id,
        world_id=model.world_id,
        scope_kind=ProviderScopeKind(model.scope_kind),
        scope_key=model.scope_key,
        provider_kind=ProviderKind(model.provider_kind),
        adapter_kind=ProviderAdapterKind(model.adapter_kind),
        provider_key=model.provider_key,
        display_name=model.display_name,
        base_url=model.base_url,
        auth_ref_configured=model.auth_ref is not None,
        config_json=model.config_json,
        default_params_json=model.default_params_json,
        status=ProviderIntegrationStatus(model.status),
        visibility=ProviderVisibility(model.visibility),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _capability_record(model: ProviderCapability) -> ProviderCapabilityRead:
    return ProviderCapabilityRead(
        id=model.id,
        provider_integration_id=model.provider_integration_id,
        capability_key=model.capability_key,
        capability_json=model.capability_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
