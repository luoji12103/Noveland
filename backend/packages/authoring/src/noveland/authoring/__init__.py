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
    "BetaContentRepairCandidate": (
        "noveland.authoring.contracts",
        "BetaContentRepairCandidate",
    ),
    "BetaContentRepairImpact": (
        "noveland.authoring.contracts",
        "BetaContentRepairImpact",
    ),
    "BetaContentRepairKind": (
        "noveland.authoring.contracts",
        "BetaContentRepairKind",
    ),
    "BetaContentRepairRequest": (
        "noveland.authoring.contracts",
        "BetaContentRepairRequest",
    ),
    "BetaContentRepairResult": (
        "noveland.authoring.contracts",
        "BetaContentRepairResult",
    ),
    "AuthoringPreviewRequest": (
        "noveland.authoring.contracts",
        "AuthoringPreviewRequest",
    ),
    "AuthoringApplyRequest": (
        "noveland.authoring.contracts",
        "AuthoringApplyRequest",
    ),
    "AuthoringAssetMatchRequest": (
        "noveland.authoring.contracts",
        "AuthoringAssetMatchRequest",
    ),
    "AuthoringAssetMatchResult": (
        "noveland.authoring.contracts",
        "AuthoringAssetMatchResult",
    ),
    "AuthoringAssetMatchingMode": (
        "noveland.authoring.contracts",
        "AuthoringAssetMatchingMode",
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
    "AuthoringConflictReviewRequest": (
        "noveland.authoring.contracts",
        "AuthoringConflictReviewRequest",
    ),
    "AuthoringConflictReviewResult": (
        "noveland.authoring.contracts",
        "AuthoringConflictReviewResult",
    ),
    "AuthoringConflictReviewMode": (
        "noveland.authoring.contracts",
        "AuthoringConflictReviewMode",
    ),
    "AuthoringLoreExtractRequest": (
        "noveland.authoring.contracts",
        "AuthoringLoreExtractRequest",
    ),
    "AuthoringLoreExtractResult": (
        "noveland.authoring.contracts",
        "AuthoringLoreExtractResult",
    ),
    "AuthoringLoreExtractorMode": (
        "noveland.authoring.contracts",
        "AuthoringLoreExtractorMode",
    ),
    "AuthoringMemoryMigrateRequest": (
        "noveland.authoring.contracts",
        "AuthoringMemoryMigrateRequest",
    ),
    "AuthoringMemoryMigrateResult": (
        "noveland.authoring.contracts",
        "AuthoringMemoryMigrateResult",
    ),
    "AuthoringMemoryMigrationMode": (
        "noveland.authoring.contracts",
        "AuthoringMemoryMigrationMode",
    ),
    "AuthoringCharacterMemoryDistillRequest": (
        "noveland.authoring.contracts",
        "AuthoringCharacterMemoryDistillRequest",
    ),
    "AuthoringCharacterMemoryDistillResult": (
        "noveland.authoring.contracts",
        "AuthoringCharacterMemoryDistillResult",
    ),
    "AuthoringCharacterMemoryDistillationMode": (
        "noveland.authoring.contracts",
        "AuthoringCharacterMemoryDistillationMode",
    ),
    "DemoWorldAssemblyRequest": (
        "noveland.authoring.contracts",
        "DemoWorldAssemblyRequest",
    ),
    "DemoWorldAssemblyResult": (
        "noveland.authoring.contracts",
        "DemoWorldAssemblyResult",
    ),
    "DemoWorldAssemblyMode": (
        "noveland.authoring.contracts",
        "DemoWorldAssemblyMode",
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
