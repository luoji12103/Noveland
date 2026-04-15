from pydantic import ValidationError


class PluginRegistryError(Exception):
    """Base class for plugin registry failures."""


class DuplicatePluginError(PluginRegistryError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Plugin is already registered: {identifier}")
        self.identifier = identifier


class PluginNotFoundError(PluginRegistryError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Plugin is not registered: {identifier}")
        self.identifier = identifier


class PluginConfigValidationError(PluginRegistryError):
    def __init__(self, identifier: str, validation_error: ValidationError) -> None:
        super().__init__(f"Plugin config is invalid for: {identifier}")
        self.identifier = identifier
        self.validation_error = validation_error


class PluginFactoryError(PluginRegistryError):
    def __init__(self, identifier: str, original_error: Exception) -> None:
        super().__init__(f"Plugin factory failed for: {identifier}")
        self.identifier = identifier
        self.original_error = original_error
