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
    "BackupRestoreDrillService",
    "RestoreDrillCheck",
    "RestoreDrillReport",
    "verify_backup_readiness",
]


def __getattr__(name: str) -> object:
    if name in {"BackupVerificationResult", "verify_backup_readiness"}:
        from noveland.storage import backup as _backup

        return getattr(_backup, name)
    if name in {"StorageAuditFinding", "StorageAuditResult", "StorageIntegrityAuditService"}:
        from noveland.storage import integrity as _integrity

        return getattr(_integrity, name)
    if name in {"BackupRestoreDrillService", "RestoreDrillCheck", "RestoreDrillReport"}:
        from noveland.storage import restore_drill as _restore_drill

        return getattr(_restore_drill, name)
    raise AttributeError(name)
