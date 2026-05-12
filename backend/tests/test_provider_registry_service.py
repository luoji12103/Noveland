from __future__ import annotations

import uuid
from typing import cast

import pytest
from noveland.auth.models import User
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderCapabilityCreate,
    ProviderHealthStatus,
    ProviderIntegrationCreate,
    ProviderIntegrationListFilters,
    ProviderIntegrationUpdate,
    ProviderKind,
    ProviderScopeKind,
    ProviderVisibility,
)
from noveland.providers.health import ProviderHealthService
from noveland.providers.models import ProviderCapability, ProviderHealthCheck, ProviderIntegration
from noveland.providers.registry import ProviderRegistryService, ProviderValidationError
from noveland.providers.secrets import (
    ProviderSecretMissingError,
    ProviderSecretResolver,
    sanitize_for_persistence,
)
from noveland.worlds.models import World
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_provider_registry_create_list_update_resolve_and_health() -> None:
    engine = _engine()
    world_id = _seed_world(engine)

    with Session(engine) as session:
        service = ProviderRegistryService(session)
        global_provider = service.create_provider(
            ProviderIntegrationCreate(
                scope_kind=ProviderScopeKind.GLOBAL,
                provider_kind=ProviderKind.TEXT_GENERATION,
                adapter_kind=ProviderAdapterKind.FAKE,
                provider_key="fake-text",
                display_name="Fake Text",
                auth_ref="secret:fake",
                visibility=ProviderVisibility.DEVELOPER_ONLY,
                capabilities=(
                    ProviderCapabilityCreate(
                        capability_key="supports_text_generation",
                        capability_json={"value": True},
                    ),
                ),
            )
        )
        world_provider = service.create_provider(
            ProviderIntegrationCreate(
                world_id=world_id,
                scope_kind=ProviderScopeKind.WORLD,
                provider_kind=ProviderKind.TEXT_GENERATION,
                adapter_kind=ProviderAdapterKind.FAKE,
                provider_key="fake-text",
                display_name="World Fake Text",
                capabilities=(
                    ProviderCapabilityCreate(
                        capability_key="supports_text_generation",
                        capability_json={"value": True, "world": True},
                    ),
                ),
            )
        )
        resolved = service.resolve_provider_for_capability(
            world_id,
            provider_kind=ProviderKind.TEXT_GENERATION,
            capability_key="supports_text_generation",
        )
        listed = service.list_providers(
            world_id,
            ProviderIntegrationListFilters(adapter_kind=ProviderAdapterKind.FAKE),
            platform_admin=True,
        )
        capabilities = service.list_capabilities(world_id, world_provider.id)
        updated = service.update_provider(
            world_id,
            world_provider.id,
            update=ProviderIntegrationUpdate(
                display_name="Updated Fake Text",
                capabilities=(
                    ProviderCapabilityCreate(
                        capability_key="supports_text_generation",
                        capability_json={"value": True, "updated": True},
                    ),
                ),
            ),
        )
        health = ProviderHealthService(session).record_health_check(
            world_provider.id,
            status=ProviderHealthStatus.HEALTHY,
            latency_ms=1,
            metadata_json={"adapter_kind": "fake"},
        )
        session.commit()

    assert global_provider.auth_ref_configured is True
    assert resolved.id == world_provider.id
    assert {record.id for record in listed} == {global_provider.id, world_provider.id}
    assert capabilities[0].capability_key == "supports_text_generation"
    assert updated.display_name == "Updated Fake Text"
    assert health.provider_integration_id == world_provider.id


def test_registry_rejects_incompatible_adapter_kind() -> None:
    engine = _engine()
    world_id = _seed_world(engine)

    with Session(engine) as session:
        with pytest.raises(ProviderValidationError, match="does not support"):
            ProviderRegistryService(session).create_provider(
                ProviderIntegrationCreate(
                    world_id=world_id,
                    scope_kind=ProviderScopeKind.WORLD,
                    provider_kind=ProviderKind.IMAGE_GENERATION,
                    adapter_kind=ProviderAdapterKind.MIMO_TTS,
                    provider_key="bad",
                    display_name="Bad",
                )
            )


def test_registry_rejects_sensitive_provider_config_recursively() -> None:
    engine = _engine()
    world_id = _seed_world(engine)

    with Session(engine) as session:
        with pytest.raises(ProviderValidationError, match="sensitive key"):
            ProviderRegistryService(session).create_provider(
                ProviderIntegrationCreate(
                    world_id=world_id,
                    scope_kind=ProviderScopeKind.WORLD,
                    provider_kind=ProviderKind.IMAGE_GENERATION,
                    adapter_kind=ProviderAdapterKind.FAKE,
                    provider_key="bad-config",
                    display_name="Bad Config",
                    config_json={"nested": {"api_key": "sk-secret"}},
                )
            )
        provider = ProviderRegistryService(session).create_provider(
            ProviderIntegrationCreate(
                world_id=world_id,
                scope_kind=ProviderScopeKind.WORLD,
                provider_kind=ProviderKind.TEXT_GENERATION,
                adapter_kind=ProviderAdapterKind.FAKE,
                provider_key="safe-config",
                display_name="Safe Config",
            )
        )
        with pytest.raises(ProviderValidationError, match="sensitive key"):
            ProviderRegistryService(session).update_provider(
                world_id,
                provider.id,
                ProviderIntegrationUpdate(default_params_json={"headers": {"authorization": "x"}}),
            )


def test_provider_secret_resolver_uses_env_refs_and_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-live")
    resolver = ProviderSecretResolver()

    resolved = resolver.resolve_auth_ref("openai:default")

    assert resolved is not None
    assert resolved.source == "env:OPENAI_API_KEY"
    assert resolved.value == "sk-live"
    with pytest.raises(ProviderSecretMissingError):
        resolver.resolve_auth_ref("env:DOES_NOT_EXIST")


def test_sanitizer_redacts_nested_sensitive_keys() -> None:
    assert sanitize_for_persistence({"headers": {"Authorization": "Bearer secret"}}) == {
        "headers": {"Authorization": "[REDACTED]"}
    }


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        cast(Table, User.__table__),
        cast(Table, World.__table__),
        cast(Table, ProviderIntegration.__table__),
        cast(Table, ProviderCapability.__table__),
        cast(Table, ProviderHealthCheck.__table__),
    ):
        table.create(engine)
    return engine


def _seed_world(engine: Engine) -> uuid.UUID:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
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
        session.commit()
    return world_id
