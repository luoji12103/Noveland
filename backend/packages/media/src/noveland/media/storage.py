from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

from noveland.media.errors import MediaStorageError

_SAFE_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


@dataclass(frozen=True, slots=True)
class MediaObjectRecord:
    uri: str
    size_bytes: int
    checksum_sha256: str
    content_type: str


class MediaObjectStorage(Protocol):
    def write_bytes(self, key: str, data: bytes, *, content_type: str) -> MediaObjectRecord: ...

    def read_bytes(self, uri: str) -> bytes: ...

    def exists(self, uri: str) -> bool: ...

    def delete(self, uri: str) -> None: ...

    def uri_for_key(self, key: str) -> str: ...


class LocalMediaObjectStorage:
    scheme = "media"

    def __init__(self, root: Path) -> None:
        self._root = root

    def write_bytes(self, key: str, data: bytes, *, content_type: str) -> MediaObjectRecord:
        object_path = self._path_for_key(key)
        object_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = object_path.with_name(f".{object_path.name}.{os.getpid()}.tmp")
        temp_path.write_bytes(data)
        temp_path.replace(object_path)
        return MediaObjectRecord(
            uri=self.uri_for_key(key),
            size_bytes=len(data),
            checksum_sha256=hashlib.sha256(data).hexdigest(),
            content_type=content_type,
        )

    def read_bytes(self, uri: str) -> bytes:
        object_path = self._path_for_uri(uri)
        if not object_path.is_file():
            raise MediaStorageError(f"media object not found: {uri}")
        try:
            return object_path.read_bytes()
        except OSError as exc:
            raise MediaStorageError(f"media object is not readable: {uri}") from exc

    def exists(self, uri: str) -> bool:
        return self._path_for_uri(uri).is_file()

    def delete(self, uri: str) -> None:
        object_path = self._path_for_uri(uri)
        try:
            object_path.unlink(missing_ok=True)
        except OSError as exc:
            raise MediaStorageError(f"media object could not be deleted: {uri}") from exc

    def uri_for_key(self, key: str) -> str:
        return f"{self.scheme}://{self._safe_key(key)}"

    def _path_for_uri(self, uri: str) -> Path:
        prefix = f"{self.scheme}://"
        if not uri.startswith(prefix):
            raise MediaStorageError(f"unsupported media URI: {uri}")
        return self._path_for_key(uri[len(prefix) :])

    def _path_for_key(self, key: str) -> Path:
        safe_key = self._safe_key(key)
        return self._root.joinpath(*PurePosixPath(safe_key).parts)

    def _safe_key(self, key: str) -> str:
        normalized = PurePosixPath(key)
        normalized_string = str(normalized)
        if (
            normalized.is_absolute()
            or ".." in normalized.parts
            or normalized_string in {"", "."}
            or not _SAFE_KEY_RE.fullmatch(normalized_string)
        ):
            raise MediaStorageError("media key must be a safe relative path without traversal")
        return normalized_string
