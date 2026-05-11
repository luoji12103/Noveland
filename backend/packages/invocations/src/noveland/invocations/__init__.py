from __future__ import annotations

from typing import Any

PACKAGE_NAME = "invocations"

_EXPORTS: dict[str, tuple[str, str]] = {
    "AgentRuntimeRunInvocationLinkCreate": (
        "noveland.invocations.contracts",
        "AgentRuntimeRunInvocationLinkCreate",
    ),
    "InvocationLedgerService": ("noveland.invocations.service", "InvocationLedgerService"),
    "InvocationRecordCreate": ("noveland.invocations.contracts", "InvocationRecordCreate"),
    "InvocationRecordView": ("noveland.invocations.contracts", "InvocationRecordView"),
    "InvocationSearchFilters": ("noveland.invocations.contracts", "InvocationSearchFilters"),
    "InvocationStatusUpdate": ("noveland.invocations.contracts", "InvocationStatusUpdate"),
    "InvocationTagCreate": ("noveland.invocations.contracts", "InvocationTagCreate"),
    "ModelInvocation": ("noveland.invocations.models", "ModelInvocation"),
    "PromptSnapshotCreate": ("noveland.invocations.contracts", "PromptSnapshotCreate"),
    "PromptSnapshotService": ("noveland.invocations.service", "PromptSnapshotService"),
    "PromptTemplateCreate": ("noveland.invocations.contracts", "PromptTemplateCreate"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    module = __import__(module_name, fromlist=[attr_name])
    return getattr(module, attr_name)


__all__ = [*_EXPORTS, "PACKAGE_NAME"]
