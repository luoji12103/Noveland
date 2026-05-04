from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


class ObjectStorageError(Exception):
    """Base object storage error."""


class ObjectStorageNotFoundError(ObjectStorageError):
    """Raised when an object URI cannot be resolved."""


@dataclass(frozen=True, slots=True)
class ObjectStorageRecord:
    uri: str
    size_bytes: int


class LocalObjectStorage:
    scheme = "object"

    def __init__(self, root: Path) -> None:
        self._root = root

    def write_json(self, key: str, payload: dict[str, Any]) -> ObjectStorageRecord:
        object_path = self._path_for_key(key)
        object_path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        object_path.write_bytes(encoded)
        return ObjectStorageRecord(uri=self.uri_for_key(key), size_bytes=len(encoded))

    def read_json(self, uri: str) -> dict[str, Any]:
        object_path = self._path_for_uri(uri)
        if not object_path.is_file():
            raise ObjectStorageNotFoundError(f"object not found: {uri}")
        try:
            payload = json.loads(object_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ObjectStorageError(f"object is not readable JSON: {uri}") from exc
        if not isinstance(payload, dict):
            raise ObjectStorageError(f"object payload is not a JSON object: {uri}")
        return payload

    def exists(self, uri: str) -> bool:
        return self._path_for_uri(uri).is_file()

    def uri_for_key(self, key: str) -> str:
        safe_key = self._safe_key(key)
        return f"{self.scheme}://{safe_key}"

    def _path_for_uri(self, uri: str) -> Path:
        prefix = f"{self.scheme}://"
        if not uri.startswith(prefix):
            raise ObjectStorageError(f"unsupported object URI: {uri}")
        return self._path_for_key(uri[len(prefix) :])

    def _path_for_key(self, key: str) -> Path:
        safe_key = self._safe_key(key)
        return self._root.joinpath(*PurePosixPath(safe_key).parts)

    def _safe_key(self, key: str) -> str:
        normalized = PurePosixPath(key)
        if normalized.is_absolute() or ".." in normalized.parts or str(normalized) in {"", "."}:
            raise ObjectStorageError("object key must be a relative path without traversal")
        return str(normalized)
