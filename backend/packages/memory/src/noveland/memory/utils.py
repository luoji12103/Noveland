from __future__ import annotations

import hashlib

from noveland.memory.vector_type import VECTOR_DIMENSIONS


def deterministic_embedding(text: str) -> list[float]:
    digest = hashlib.sha256(text.strip().encode("utf-8")).digest()
    seed = list(digest)
    values: list[float] = []
    for index in range(VECTOR_DIMENSIONS):
        byte = seed[index % len(seed)]
        values.append((byte / 255.0) * 2.0 - 1.0)
    return values
