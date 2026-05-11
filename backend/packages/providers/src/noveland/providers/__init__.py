from __future__ import annotations

from importlib import import_module
from typing import Any

PACKAGE_NAME = "providers"

_EXPORTS = {
    "ProviderExecutionService": ("noveland.providers.service", "ProviderExecutionService"),
    "ProviderHealthService": ("noveland.providers.health", "ProviderHealthService"),
    "ProviderRegistryService": ("noveland.providers.registry", "ProviderRegistryService"),
    "ProviderExecutionRequest": ("noveland.providers.contracts", "ProviderExecutionRequest"),
    "ProviderExecutionResult": ("noveland.providers.contracts", "ProviderExecutionResult"),
    "ProviderIntegrationCreate": ("noveland.providers.contracts", "ProviderIntegrationCreate"),
    "ProviderIntegrationRead": ("noveland.providers.contracts", "ProviderIntegrationRead"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    return getattr(import_module(module_name), attr_name)


__all__ = sorted((*_EXPORTS, "PACKAGE_NAME"))
