from __future__ import annotations

from typing import Any

PACKAGE_NAME = "media"

_EXPORTS: dict[str, tuple[str, str]] = {
    "LocalMediaObjectStorage": ("noveland.media.storage", "LocalMediaObjectStorage"),
    "MediaAssetCreate": ("noveland.media.contracts", "MediaAssetCreate"),
    "MediaAssetInputCreate": ("noveland.media.contracts", "MediaAssetInputCreate"),
    "MediaAssetRecord": ("noveland.media.contracts", "MediaAssetRecord"),
    "MediaAssetUpdate": ("noveland.media.contracts", "MediaAssetUpdate"),
    "MediaContextCreate": ("noveland.media.contracts", "MediaContextCreate"),
    "MediaJobCreate": ("noveland.media.contracts", "MediaJobCreate"),
    "MediaJobRecord": ("noveland.media.contracts", "MediaJobRecord"),
    "MediaJobService": ("noveland.media.service", "MediaJobService"),
    "MediaService": ("noveland.media.service", "MediaService"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    module = __import__(module_name, fromlist=[attr_name])
    return getattr(module, attr_name)


__all__ = [*_EXPORTS, "PACKAGE_NAME"]
