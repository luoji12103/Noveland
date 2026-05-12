from __future__ import annotations

from importlib import import_module
from typing import Any

PACKAGE_NAME = "asset_generation"

_EXPORTS = {
    "AssetGenerationService": ("noveland.asset_generation.service", "AssetGenerationService"),
    "AssetGenerationPolicyCreate": (
        "noveland.asset_generation.contracts",
        "AssetGenerationPolicyCreate",
    ),
    "AssetGenerationPolicyRead": (
        "noveland.asset_generation.contracts",
        "AssetGenerationPolicyRead",
    ),
    "AssetGenerationPreviewRequest": (
        "noveland.asset_generation.contracts",
        "AssetGenerationPreviewRequest",
    ),
    "AssetGenerationApplyRequest": (
        "noveland.asset_generation.contracts",
        "AssetGenerationApplyRequest",
    ),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    return getattr(import_module(module_name), attr_name)


__all__ = sorted((*_EXPORTS, "PACKAGE_NAME"))
