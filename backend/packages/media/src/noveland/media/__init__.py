from __future__ import annotations

from typing import Any

PACKAGE_NAME = "media"

_EXPORTS: dict[str, tuple[str, str]] = {
    "LocalMediaObjectStorage": ("noveland.media.storage", "LocalMediaObjectStorage"),
    "MediaCatalogService": ("noveland.media.catalog", "MediaCatalogService"),
    "MediaCollectionService": ("noveland.media.catalog", "MediaCollectionService"),
    "MediaLineageService": ("noveland.media.catalog", "MediaLineageService"),
    "MediaAssetCreate": ("noveland.media.contracts", "MediaAssetCreate"),
    "MediaAssetCollectionCreate": ("noveland.media.contracts", "MediaAssetCollectionCreate"),
    "MediaAssetCollectionRecord": ("noveland.media.contracts", "MediaAssetCollectionRecord"),
    "MediaAssetInputCreate": ("noveland.media.contracts", "MediaAssetInputCreate"),
    "MediaAssetRecord": ("noveland.media.contracts", "MediaAssetRecord"),
    "MediaAssetUploadResponse": ("noveland.media.contracts", "MediaAssetUploadResponse"),
    "MediaAssetTagCreate": ("noveland.media.contracts", "MediaAssetTagCreate"),
    "MediaAssetTagRecord": ("noveland.media.contracts", "MediaAssetTagRecord"),
    "MediaAssetUpdate": ("noveland.media.contracts", "MediaAssetUpdate"),
    "MediaContextCreate": ("noveland.media.contracts", "MediaContextCreate"),
    "MediaJobCreate": ("noveland.media.contracts", "MediaJobCreate"),
    "MediaJobRecord": ("noveland.media.contracts", "MediaJobRecord"),
    "MediaObjectCreate": ("noveland.media.contracts", "MediaObjectCreate"),
    "MediaObjectRecord": ("noveland.media.contracts", "MediaObjectRecord"),
    "MediaReferenceCreate": ("noveland.media.contracts", "MediaReferenceCreate"),
    "MediaReferenceRecord": ("noveland.media.contracts", "MediaReferenceRecord"),
    "ImageService": ("noveland.media.image_service", "ImageService"),
    "MediaJobService": ("noveland.media.service", "MediaJobService"),
    "MediaReferenceService": ("noveland.media.service", "MediaReferenceService"),
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
