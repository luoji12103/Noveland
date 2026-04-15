from collections.abc import Callable
from dataclasses import dataclass

from noveland.plugins.manifest import PluginManifest
from pydantic import BaseModel


@dataclass(frozen=True)
class PluginDefinition[ConfigModelT: BaseModel]:
    manifest: PluginManifest
    config_model: type[ConfigModelT]
    implementation_factory: Callable[[ConfigModelT], object]

    @classmethod
    def from_config_model(
        cls,
        *,
        manifest: PluginManifest,
        config_model: type[ConfigModelT],
        implementation_factory: Callable[[ConfigModelT], object],
    ) -> "PluginDefinition[ConfigModelT]":
        return cls(
            manifest=manifest,
            config_model=config_model,
            implementation_factory=implementation_factory,
        )
