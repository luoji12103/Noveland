import hashlib
from pathlib import Path

import pytest
from noveland.media.errors import MediaStorageError
from noveland.media.storage import LocalMediaObjectStorage


def test_local_media_storage_writes_reads_and_deletes_bytes(tmp_path: Path) -> None:
    storage = LocalMediaObjectStorage(tmp_path)

    record = storage.write_bytes(
        "worlds/world-1/worldlines/line-1/assets/example.png",
        b"media-bytes",
        content_type="image/png",
    )

    assert record.uri == "media://worlds/world-1/worldlines/line-1/assets/example.png"
    assert record.size_bytes == len(b"media-bytes")
    assert record.checksum_sha256 == hashlib.sha256(b"media-bytes").hexdigest()
    assert str(tmp_path) not in record.uri
    assert storage.exists(record.uri) is True
    assert storage.read_bytes(record.uri) == b"media-bytes"

    storage.delete(record.uri)

    assert storage.exists(record.uri) is False


@pytest.mark.parametrize(
    "key",
    [
        "../escape.png",
        "/absolute.png",
        "",
        ".",
        "worlds/../../escape.png",
        "worlds/world 1/bad.png",
    ],
)
def test_local_media_storage_rejects_unsafe_keys(tmp_path: Path, key: str) -> None:
    storage = LocalMediaObjectStorage(tmp_path)

    with pytest.raises(MediaStorageError):
        storage.uri_for_key(key)


@pytest.mark.parametrize("uri", ["file:///tmp/x.png", "https://example.test/x.png", "object://x"])
def test_local_media_storage_rejects_non_media_uris(tmp_path: Path, uri: str) -> None:
    storage = LocalMediaObjectStorage(tmp_path)

    with pytest.raises(MediaStorageError):
        storage.exists(uri)
