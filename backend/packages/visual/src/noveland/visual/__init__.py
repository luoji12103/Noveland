from __future__ import annotations

from importlib import import_module
from typing import Any

PACKAGE_NAME = "visual"

_EXPORTS = {
    "VisualAssetService": ("noveland.visual.service", "VisualAssetService"),
    "VisualResolver": ("noveland.visual.resolver", "VisualResolver"),
    "VisualCompositionService": ("noveland.visual.composition", "VisualCompositionService"),
    "SpriteSetCreate": ("noveland.visual.contracts", "SpriteSetCreate"),
    "SpriteVariantCreate": ("noveland.visual.contracts", "SpriteVariantCreate"),
    "SceneBackgroundCreate": ("noveland.visual.contracts", "SceneBackgroundCreate"),
    "SpriteResolveRequest": ("noveland.visual.contracts", "SpriteResolveRequest"),
    "BackgroundResolveRequest": ("noveland.visual.contracts", "BackgroundResolveRequest"),
    "SceneComposeRequest": ("noveland.visual.contracts", "SceneComposeRequest"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    return getattr(import_module(module_name), attr_name)


__all__ = sorted((*_EXPORTS, "PACKAGE_NAME"))
