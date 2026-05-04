from __future__ import annotations

import argparse
from dataclasses import dataclass

from noveland.core.database import create_engine_from_settings
from noveland.core.settings import load_settings
from noveland.storage.local import LocalObjectStorage, ObjectStorageError
from sqlalchemy import text


@dataclass(frozen=True, slots=True)
class BackupVerificationResult:
    database_ok: bool
    object_storage_root_ok: bool
    snapshot_payloads_ok: bool
    checked_snapshot_count: int
    issues: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return self.database_ok and self.object_storage_root_ok and self.snapshot_payloads_ok


def verify_backup_readiness() -> BackupVerificationResult:
    settings = load_settings()
    issues: list[str] = []
    database_ok = False
    checked_snapshot_count = 0
    snapshot_payloads_ok = True

    object_root = settings.object_storage_root
    object_root.mkdir(parents=True, exist_ok=True)
    object_storage_root_ok = object_root.is_dir()
    if not object_storage_root_ok:
        issues.append(f"Object storage root is not a directory: {object_root}")

    storage = LocalObjectStorage(object_root)
    engine = create_engine_from_settings(settings)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            database_ok = True
            snapshot_rows = connection.execute(
                text(
                    "SELECT id, payload_uri FROM world_snapshots "
                    "WHERE payload_uri IS NOT NULL ORDER BY created_at DESC LIMIT 100",
                ),
            ).all()
            checked_snapshot_count = len(snapshot_rows)
            for snapshot_id, payload_uri in snapshot_rows:
                try:
                    storage.read_json(str(payload_uri))
                except ObjectStorageError as exc:
                    snapshot_payloads_ok = False
                    issues.append(f"Snapshot {snapshot_id} payload is not readable: {exc}")
    except Exception as exc:  # noqa: BLE001
        database_ok = False
        snapshot_payloads_ok = False
        issues.append(f"Database verification failed: {exc}")
    finally:
        engine.dispose()

    return BackupVerificationResult(
        database_ok=database_ok,
        object_storage_root_ok=object_storage_root_ok,
        snapshot_payloads_ok=snapshot_payloads_ok,
        checked_snapshot_count=checked_snapshot_count,
        issues=tuple(issues),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify local Noveland backup readiness.")
    parser.add_argument("--quiet", action="store_true", help="Only print failures.")
    args = parser.parse_args()

    result = verify_backup_readiness()
    if not args.quiet or not result.ok:
        print(f"database_ok={result.database_ok}")
        print(f"object_storage_root_ok={result.object_storage_root_ok}")
        print(f"snapshot_payloads_ok={result.snapshot_payloads_ok}")
        print(f"checked_snapshot_count={result.checked_snapshot_count}")
        for issue in result.issues:
            print(f"issue={issue}")
    raise SystemExit(0 if result.ok else 1)
