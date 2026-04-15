from typing import Any

import pytest
from noveland.plugins import (
    DuplicatePluginError,
    PluginCategory,
    PluginConfigValidationError,
    PluginDefinition,
    PluginFactoryError,
    PluginManifest,
    PluginNotFoundError,
    PluginRegistry,
)
from pydantic import BaseModel, Field


class FakeConfig(BaseModel):
    endpoint: str
    retries: int = Field(default=1, ge=0)


class FakePlugin:
    def __init__(self, config: FakeConfig) -> None:
        self.config = config


def make_definition(
    *,
    identifier: str = "builtin.fake",
    category: PluginCategory = PluginCategory.MODEL_PROVIDER,
    factory_failure: bool = False,
) -> PluginDefinition[FakeConfig]:
    def create_plugin(config: FakeConfig) -> object:
        if factory_failure:
            raise RuntimeError("factory failed")
        return FakePlugin(config)

    return PluginDefinition.from_config_model(
        manifest=PluginManifest(
            identifier=identifier,
            category=category,
            version="0.1.0",
            config_schema=FakeConfig.model_json_schema(),
            capabilities=("fake.capability",),
        ),
        config_model=FakeConfig,
        implementation_factory=create_plugin,
    )


def test_every_plugin_category_can_register_fake_plugin() -> None:
    registry = PluginRegistry()

    for category in PluginCategory:
        registry.register(
            make_definition(
                identifier=f"builtin.{category.value.replace('_', '-')}",
                category=category,
            )
        )

    assert len(registry.all()) == len(PluginCategory)


def test_manifest_exposes_required_contract_fields() -> None:
    definition = make_definition()

    assert definition.manifest.identifier == "builtin.fake"
    assert definition.manifest.category == PluginCategory.MODEL_PROVIDER
    assert definition.manifest.version == "0.1.0"
    assert "properties" in definition.manifest.config_schema
    assert definition.manifest.capabilities == ("fake.capability",)


def test_manifest_rejects_invalid_identifier() -> None:
    with pytest.raises(ValueError):
        PluginManifest(
            identifier="Builtin Fake",
            category=PluginCategory.MODEL_PROVIDER,
            version="0.1.0",
            config_schema={},
            capabilities=("fake.capability",),
        )


def test_registry_rejects_duplicate_identifier() -> None:
    registry = PluginRegistry([make_definition()])

    with pytest.raises(DuplicatePluginError):
        registry.register(make_definition())


def test_missing_plugin_lookup_raises_typed_error() -> None:
    registry = PluginRegistry()

    with pytest.raises(PluginNotFoundError):
        registry.get("builtin.missing")


def test_config_validation_returns_pydantic_model() -> None:
    registry = PluginRegistry([make_definition()])

    config = registry.validate_config("builtin.fake", {"endpoint": "https://example.test"})

    assert isinstance(config, FakeConfig)
    assert config.endpoint == "https://example.test"
    assert config.retries == 1


def test_invalid_config_raises_typed_error() -> None:
    registry = PluginRegistry([make_definition()])

    with pytest.raises(PluginConfigValidationError):
        registry.validate_config(
            "builtin.fake",
            {"endpoint": "https://example.test", "retries": -1},
        )


def test_factory_failure_is_wrapped() -> None:
    registry = PluginRegistry([make_definition(factory_failure=True)])

    with pytest.raises(PluginFactoryError) as error:
        registry.create("builtin.fake", {"endpoint": "https://example.test"})

    assert isinstance(error.value.original_error, RuntimeError)


def test_create_validates_config_then_returns_plugin_instance() -> None:
    registry = PluginRegistry([make_definition()])

    plugin = registry.create("builtin.fake", {"endpoint": "https://example.test", "retries": 2})

    assert isinstance(plugin, FakePlugin)
    assert plugin.config.retries == 2


def test_category_listing_only_returns_matching_category() -> None:
    registry = PluginRegistry(
        [
            make_definition(identifier="builtin.model", category=PluginCategory.MODEL_PROVIDER),
            make_definition(identifier="builtin.memory", category=PluginCategory.MEMORY_BACKEND),
        ]
    )

    model_plugins = registry.list_by_category(PluginCategory.MODEL_PROVIDER)

    assert [definition.manifest.identifier for definition in model_plugins] == ["builtin.model"]


def test_resolve_enabled_uses_registered_identifiers() -> None:
    registry = PluginRegistry(
        [
            make_definition(identifier="builtin.model", category=PluginCategory.MODEL_PROVIDER),
            make_definition(identifier="builtin.memory", category=PluginCategory.MEMORY_BACKEND),
        ]
    )

    enabled = registry.resolve_enabled(["builtin.memory"])

    assert [definition.manifest.identifier for definition in enabled] == ["builtin.memory"]


def test_definition_accepts_arbitrary_plugin_instance_type() -> None:
    registry = PluginRegistry([make_definition()])

    plugin: Any = registry.create("builtin.fake", {"endpoint": "https://example.test"})

    assert plugin.config.endpoint == "https://example.test"
