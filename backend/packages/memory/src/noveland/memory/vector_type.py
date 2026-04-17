from __future__ import annotations

from typing import Any

from sqlalchemy import JSON
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator, TypeEngine

VECTOR_DIMENSIONS = 1536


class EmbeddingVector(TypeDecorator[list[float]]):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        return dialect.type_descriptor(JSON())

    def process_bind_param(
        self,
        value: list[float] | None,
        dialect: Dialect,
    ) -> list[float] | None:
        if value is None:
            return None
        return [float(item) for item in value]

    def process_result_value(
        self,
        value: object,
        dialect: Dialect,
    ) -> list[float] | None:
        if value is None:
            return None
        if isinstance(value, list):
            return [float(item) for item in value]
        return None
