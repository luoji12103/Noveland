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
    "StorageAuditFinding",
    "StorageAuditResult",
    "StorageIntegrityAuditService",
    "verify_backup_readiness",
]


def __getattr__(name: str) -> object:
    if name in {"BackupVerificationResult", "verify_backup_readiness"}:
        from noveland.storage import backup as _backup

        return getattr(_backup, name)
    if name in {"StorageAuditFinding", "StorageAuditResult", "StorageIntegrityAuditService"}:
        from noveland.storage import integrity as _integrity

        return getattr(_integrity, name)
    raise AttributeError(name)
