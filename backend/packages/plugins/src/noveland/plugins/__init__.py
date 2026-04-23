from noveland.plugins.categories import PluginCategory
from noveland.plugins.constants import (
    BUILTIN_ANTHROPIC_COMPATIBLE,
    BUILTIN_DEFAULT_NARRATIVE_WRITER,
    BUILTIN_DEFAULT_PERSONA_POLICY,
    BUILTIN_DEFAULT_WORLD_RULES,
    BUILTIN_LOCAL_PGVECTOR_MEMORY,
    BUILTIN_OPENAI_COMPATIBLE,
)
from noveland.plugins.definition import PluginDefinition
from noveland.plugins.errors import (
    DuplicatePluginError,
    PluginConfigValidationError,
    PluginFactoryError,
    PluginNotFoundError,
    PluginRegistryError,
)
from noveland.plugins.manifest import PluginManifest
from noveland.plugins.registry import PluginRegistry

__all__ = [
    "BUILTIN_ANTHROPIC_COMPATIBLE",
    "BUILTIN_DEFAULT_NARRATIVE_WRITER",
    "BUILTIN_DEFAULT_PERSONA_POLICY",
    "BUILTIN_DEFAULT_WORLD_RULES",
    "BUILTIN_LOCAL_PGVECTOR_MEMORY",
    "BUILTIN_OPENAI_COMPATIBLE",
    "DuplicatePluginError",
    "PluginCategory",
    "PluginConfigValidationError",
    "PluginDefinition",
    "PluginFactoryError",
    "PluginManifest",
    "PluginNotFoundError",
    "PluginRegistry",
    "PluginRegistryError",
    "MemoryBackendPlugin",
    "ModelProviderPlugin",
    "NarrativeWriterPlugin",
    "PersonaPolicyPlugin",
    "WorldRulesPlugin",
    "get_builtin_plugin_registry",
]


def __getattr__(name: str) -> object:
    if name in {
        "MemoryBackendPlugin",
        "ModelProviderPlugin",
        "NarrativeWriterPlugin",
        "PersonaPolicyPlugin",
        "WorldRulesPlugin",
        "get_builtin_plugin_registry",
    }:
        from noveland.plugins import builtins as _builtins

        return getattr(_builtins, name)
    raise AttributeError(name)
