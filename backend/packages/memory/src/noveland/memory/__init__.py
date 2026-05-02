from __future__ import annotations

from typing import Any

PACKAGE_NAME = "memory"

_EXPORTS: dict[str, tuple[str, str]] = {
    "AgentProfileSnapshot": ("noveland.memory.contracts", "AgentProfileSnapshot"),
    "FakeMemoryBackend": ("noveland.memory.backends", "FakeMemoryBackend"),
    "LocalPgvectorMemoryBackend": (
        "noveland.memory.local_pgvector",
        "LocalPgvectorMemoryBackend",
    ),
    "Mem0OssMemoryBackend": ("noveland.memory.backends", "Mem0OssMemoryBackend"),
    "MemoryBackend": ("noveland.memory.contracts", "MemoryBackend"),
    "MemoryBackendHealth": ("noveland.memory.contracts", "MemoryBackendHealth"),
    "MemoryBackendHealthStatus": ("noveland.memory.contracts", "MemoryBackendHealthStatus"),
    "MemoryBackendKind": ("noveland.memory.contracts", "MemoryBackendKind"),
    "MemoryBackendProfileCreate": (
        "noveland.memory.contracts",
        "MemoryBackendProfileCreate",
    ),
    "MemoryBackendProfileRecord": (
        "noveland.memory.contracts",
        "MemoryBackendProfileRecord",
    ),
    "MemoryBackendProfileService": (
        "noveland.memory.service",
        "MemoryBackendProfileService",
    ),
    "MemoryBackendProfileUpdate": (
        "noveland.memory.contracts",
        "MemoryBackendProfileUpdate",
    ),
    "MemoryBackfillDryRunResult": (
        "noveland.memory.contracts",
        "MemoryBackfillDryRunResult",
    ),
    "MemoryBackfillSourceSummary": (
        "noveland.memory.contracts",
        "MemoryBackfillSourceSummary",
    ),
    "MemoryBackfillWorldSummary": (
        "noveland.memory.contracts",
        "MemoryBackfillWorldSummary",
    ),
    "MemoryContext": ("noveland.memory.contracts", "MemoryContext"),
    "MemoryDeleteResult": ("noveland.memory.contracts", "MemoryDeleteResult"),
    "MemoryDeleteScope": ("noveland.memory.contracts", "MemoryDeleteScope"),
    "MemoryEvalCase": ("noveland.memory.contracts", "MemoryEvalCase"),
    "MemoryEvalCaseResult": ("noveland.memory.contracts", "MemoryEvalCaseResult"),
    "MemoryEvalResult": ("noveland.memory.contracts", "MemoryEvalResult"),
    "MemoryEvent": ("noveland.memory.contracts", "MemoryEvent"),
    "MemoryItemRecord": ("noveland.memory.contracts", "MemoryItemRecord"),
    "MemoryMessage": ("noveland.memory.contracts", "MemoryMessage"),
    "MemoryProfileSnapshotRecord": (
        "noveland.memory.contracts",
        "MemoryProfileSnapshotRecord",
    ),
    "MemoryRetrievalLogRecord": ("noveland.memory.contracts", "MemoryRetrievalLogRecord"),
    "MemorySearchRequest": ("noveland.memory.contracts", "MemorySearchRequest"),
    "MemorySearchResult": ("noveland.memory.contracts", "MemorySearchResult"),
    "MemoryService": ("noveland.memory.service", "MemoryService"),
    "MemoryTurn": ("noveland.memory.contracts", "MemoryTurn"),
    "MemoryWriteLogRecord": ("noveland.memory.contracts", "MemoryWriteLogRecord"),
    "MemoryWriteJobRecord": ("noveland.memory.contracts", "MemoryWriteJobRecord"),
    "MemoryWriteJobStatus": ("noveland.memory.contracts", "MemoryWriteJobStatus"),
    "MemoryWriteJobStatusSummary": (
        "noveland.memory.contracts",
        "MemoryWriteJobStatusSummary",
    ),
    "MemoryWriteSourceKind": ("noveland.memory.contracts", "MemoryWriteSourceKind"),
    "VECTOR_DIMENSIONS": ("noveland.memory.vector_type", "VECTOR_DIMENSIONS"),
    "deterministic_embedding": ("noveland.memory.utils", "deterministic_embedding"),
    "run_memory_eval_cases": ("noveland.memory.evals", "run_memory_eval_cases"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    module = __import__(module_name, fromlist=[attr_name])
    return getattr(module, attr_name)


__all__ = [*_EXPORTS, "PACKAGE_NAME"]
