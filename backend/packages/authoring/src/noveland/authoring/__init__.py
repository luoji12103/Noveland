from __future__ import annotations

from importlib import import_module
from typing import Any

PACKAGE_NAME = "authoring"

_EXPORTS = {
    "AuthoringService": ("noveland.authoring.service", "AuthoringService"),
    "AuthoringSourceBatchCreate": (
        "noveland.authoring.contracts",
        "AuthoringSourceBatchCreate",
    ),
    "AuthoringSourceBatchRead": (
        "noveland.authoring.contracts",
        "AuthoringSourceBatchRead",
    ),
    "AuthoringImportRunCreate": (
        "noveland.authoring.contracts",
        "AuthoringImportRunCreate",
    ),
    "AuthoringImportRunRead": (
        "noveland.authoring.contracts",
        "AuthoringImportRunRead",
    ),
    "AuthoringPreviewRequest": (
        "noveland.authoring.contracts",
        "AuthoringPreviewRequest",
    ),
    "AuthoringApplyRequest": (
        "noveland.authoring.contracts",
        "AuthoringApplyRequest",
    ),
    "AuthoringCharacterExtractRequest": (
        "noveland.authoring.contracts",
        "AuthoringCharacterExtractRequest",
    ),
    "AuthoringCharacterExtractResult": (
        "noveland.authoring.contracts",
        "AuthoringCharacterExtractResult",
    ),
    "AuthoringCharacterExtractorMode": (
        "noveland.authoring.contracts",
        "AuthoringCharacterExtractorMode",
    ),
    "AuthoringScriptParseRequest": (
        "noveland.authoring.contracts",
        "AuthoringScriptParseRequest",
    ),
    "AuthoringScriptParseResult": (
        "noveland.authoring.contracts",
        "AuthoringScriptParseResult",
    ),
    "AuthoringScriptParserMode": (
        "noveland.authoring.contracts",
        "AuthoringScriptParserMode",
    ),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    return getattr(import_module(module_name), attr_name)


__all__ = sorted((*_EXPORTS, "PACKAGE_NAME"))
