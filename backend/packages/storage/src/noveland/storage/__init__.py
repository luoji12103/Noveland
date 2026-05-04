from noveland.storage.local import (
    LocalObjectStorage,
    ObjectStorageError,
    ObjectStorageNotFoundError,
    ObjectStorageRecord,
)

__all__ = [
    "BackupVerificationResult",
    "LocalObjectStorage",
    "ObjectStorageError",
    "ObjectStorageNotFoundError",
    "ObjectStorageRecord",
    "verify_backup_readiness",
]


def __getattr__(name: str) -> object:
    if name in {"BackupVerificationResult", "verify_backup_readiness"}:
        from noveland.storage import backup as _backup

        return getattr(_backup, name)
    raise AttributeError(name)
