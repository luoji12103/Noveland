from noveland.memory.contracts import (
    MemoryBackend,
    MemoryItemCreate,
    MemoryItemRecord,
    MemorySearchQuery,
)
from noveland.memory.local_pgvector import LocalPgvectorMemoryBackend
from noveland.memory.vector_type import VECTOR_DIMENSIONS

PACKAGE_NAME = "memory"

__all__ = [
    "PACKAGE_NAME",
    "LocalPgvectorMemoryBackend",
    "MemoryBackend",
    "MemoryItemCreate",
    "MemoryItemRecord",
    "MemorySearchQuery",
    "VECTOR_DIMENSIONS",
]
