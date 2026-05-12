from __future__ import annotations

from importlib import import_module
from typing import Any

PACKAGE_NAME = "multimodal_eval"

_EXPORTS = {
    "MultimodalEvalService": (
        "noveland.multimodal_eval.service",
        "MultimodalEvalService",
    ),
    "MultimodalEvalRunRequest": (
        "noveland.multimodal_eval.contracts",
        "MultimodalEvalRunRequest",
    ),
    "MultimodalEvalRunRead": (
        "noveland.multimodal_eval.contracts",
        "MultimodalEvalRunRead",
    ),
    "MultimodalDiagnosticsResult": (
        "noveland.multimodal_eval.contracts",
        "MultimodalDiagnosticsResult",
    ),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    return getattr(import_module(module_name), attr_name)


__all__ = sorted((*_EXPORTS, "PACKAGE_NAME"))
