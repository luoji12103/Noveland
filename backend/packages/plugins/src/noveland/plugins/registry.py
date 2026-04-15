from collections.abc import Iterable, Mapping
from typing import Any, cast

from noveland.plugins.categories import PluginCategory
from noveland.plugins.definition import PluginDefinition
from noveland.plugins.errors import (
    DuplicatePluginError,
    PluginConfigValidationError,
    PluginFactoryError,
    PluginNotFoundError,
)
from pydantic import BaseModel, ValidationError


class PluginRegistry:
    def __init__(self, definitions: Iterable[PluginDefinition[Any]] | None = None) -> None:
        self._definitions: dict[str, PluginDefinition[Any]] = {}
        for definition in definitions or ():
            self.register(definition)

    def register(self, definition: PluginDefinition[Any]) -> None:
        identifier = definition.manifest.identifier
        if identifier in self._definitions:
            raise DuplicatePluginError(identifier)
        self._definitions[identifier] = definition

    def get(self, identifier: str) -> PluginDefinition[Any]:
        try:
            return self._definitions[identifier]
        except KeyError as exc:
            raise PluginNotFoundError(identifier) from exc

    def list_by_category(self, category: PluginCategory) -> tuple[PluginDefinition[Any], ...]:
        return tuple(
            definition
            for definition in self._definitions.values()
            if definition.manifest.category == category
        )

    def all(self) -> tuple[PluginDefinition[Any], ...]:
        return tuple(self._definitions.values())

    def resolve_enabled(self, identifiers: Iterable[str]) -> tuple[PluginDefinition[Any], ...]:
        return tuple(self.get(identifier) for identifier in identifiers)

    def validate_config(
        self,
        identifier: str,
        raw_config: Mapping[str, Any] | BaseModel,
    ) -> BaseModel:
        definition = self.get(identifier)
        try:
            return cast(BaseModel, definition.config_model.model_validate(raw_config))
        except ValidationError as exc:
            raise PluginConfigValidationError(identifier, exc) from exc

    def create(
        self,
        identifier: str,
        raw_config: Mapping[str, Any] | BaseModel,
    ) -> object:
        definition = self.get(identifier)
        config = self.validate_config(identifier, raw_config)
        try:
            return definition.implementation_factory(config)
        except Exception as exc:
            raise PluginFactoryError(identifier, exc) from exc
