from collections.abc import Mapping
from typing import Any

from noveland.plugins import PluginCategory, get_builtin_plugin_registry

EXPECTED_CATEGORY_CAPABILITIES: Mapping[PluginCategory, set[str]] = {
    PluginCategory.MODEL_PROVIDER: {"chat.completions", "messages"},
    PluginCategory.MEMORY_BACKEND: {"memory.record_turn", "memory.search"},
    PluginCategory.WORLD_RULES: {"schedule.resolve_due_rules"},
    PluginCategory.PERSONA_POLICY: {"agent.prompt_context"},
    PluginCategory.NARRATIVE_WRITER: {"conversation.summary", "conversation.chapter"},
}


def test_builtin_plugin_contracts_cover_all_categories() -> None:
    registry = get_builtin_plugin_registry()

    categories = {definition.manifest.category for definition in registry.all()}

    assert categories == set(PluginCategory)


def test_builtin_plugin_manifests_are_complete_and_schema_backed() -> None:
    registry = get_builtin_plugin_registry()

    for definition in registry.all():
        manifest = definition.manifest
        assert manifest.identifier.startswith("builtin.")
        assert manifest.version
        assert manifest.config_schema.get("type") == "object"
        assert manifest.capabilities
        assert definition.config_model.model_json_schema() == manifest.config_schema


def test_builtin_plugin_default_configs_validate_and_create_instances() -> None:
    registry = get_builtin_plugin_registry()

    for definition in registry.all():
        config = registry.validate_config(definition.manifest.identifier, {})
        plugin = registry.create(definition.manifest.identifier, {})

        assert isinstance(config.model_dump(mode="json"), dict)
        assert plugin is not None


def test_builtin_plugin_categories_declare_expected_capabilities() -> None:
    registry = get_builtin_plugin_registry()

    for category, expected_any in EXPECTED_CATEGORY_CAPABILITIES.items():
        category_capabilities: set[str] = set()
        for definition in registry.list_by_category(category):
            category_capabilities.update(definition.manifest.capabilities)
        assert expected_any & category_capabilities


def test_builtin_plugin_config_schemas_reject_unknown_fields() -> None:
    registry = get_builtin_plugin_registry()

    for definition in registry.all():
        if _schema_allows_property(definition.manifest.config_schema, "headers"):
            continue
        invalid = registry.validate_config
        try:
            invalid(definition.manifest.identifier, {"unexpected": True})
        except Exception as exc:  # noqa: BLE001
            assert exc.__class__.__name__ == "PluginConfigValidationError"
        else:
            raise AssertionError(f"{definition.manifest.identifier} accepted unknown config")


def _schema_allows_property(schema: Mapping[str, Any], property_name: str) -> bool:
    properties = schema.get("properties", {})
    return isinstance(properties, dict) and property_name in properties
