from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import text
from sqlalchemy.orm import Session


class ByteObjectReader(Protocol):
    def read_bytes(self, uri: str) -> bytes: ...


class JsonObjectReader(Protocol):
    def read_json(self, uri: str) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class StorageAuditFinding:
    record_kind: str
    record_id: str
    world_id: str | None
    worldline_id: str | None
    status: str
    reason: str
    expected_size_bytes: int | None = None
    actual_size_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class StorageAuditResult:
    status: str
    media_object_count: int
    snapshot_payload_count: int
    ok_count: int
    missing_count: int
    size_mismatch_count: int
    checksum_mismatch_count: int
    unreadable_count: int
    invalid_metadata_count: int
    finding_count: int
    findings: tuple[StorageAuditFinding, ...]


class StorageIntegrityAuditService:
    def __init__(
        self,
        session: Session,
        *,
        media_storage: ByteObjectReader,
        object_storage: JsonObjectReader,
    ) -> None:
        self._session = session
        self._media_storage = media_storage
        self._object_storage = object_storage

    def audit(
        self,
        *,
        limit: int = 1000,
        finding_limit: int = 100,
        include_ok: bool = False,
    ) -> StorageAuditResult:
        safe_limit = max(1, min(limit, 10_000))
        safe_finding_limit = max(1, min(finding_limit, 1000))
        findings: list[StorageAuditFinding] = []
        ok_count = 0
        missing_count = 0
        size_mismatch_count = 0
        checksum_mismatch_count = 0
        unreadable_count = 0
        invalid_metadata_count = 0

        media_rows = self._session.execute(
            text(
                "SELECT id, world_id, worldline_id, storage_uri, size_bytes, checksum_sha256 "
                "FROM media_objects ORDER BY created_at DESC LIMIT :limit",
            ),
            {"limit": safe_limit},
        ).mappings()
        media_object_count = 0
        for row in media_rows:
            media_object_count += 1
            result = self._audit_media_object(row, include_ok=include_ok)
            ok_count += result.ok_count
            missing_count += result.missing_count
            size_mismatch_count += result.size_mismatch_count
            checksum_mismatch_count += result.checksum_mismatch_count
            unreadable_count += result.unreadable_count
            invalid_metadata_count += result.invalid_metadata_count
            _extend_capped(findings, result.findings, safe_finding_limit)

        snapshot_rows = self._session.execute(
            text(
                "SELECT id, world_id, worldline_id, payload_uri "
                "FROM world_snapshots WHERE payload_uri IS NOT NULL "
                "ORDER BY created_at DESC LIMIT :limit",
            ),
            {"limit": safe_limit},
        ).mappings()
        snapshot_payload_count = 0
        for row in snapshot_rows:
            snapshot_payload_count += 1
            result = self._audit_snapshot_payload(row, include_ok=include_ok)
            ok_count += result.ok_count
            missing_count += result.missing_count
            unreadable_count += result.unreadable_count
            _extend_capped(findings, result.findings, safe_finding_limit)

        status = (
            "error"
            if missing_count
            or size_mismatch_count
            or checksum_mismatch_count
            or unreadable_count
            or invalid_metadata_count
            else "ok"
        )
        return StorageAuditResult(
            status=status,
            media_object_count=media_object_count,
            snapshot_payload_count=snapshot_payload_count,
            ok_count=ok_count,
            missing_count=missing_count,
            size_mismatch_count=size_mismatch_count,
            checksum_mismatch_count=checksum_mismatch_count,
            unreadable_count=unreadable_count,
            invalid_metadata_count=invalid_metadata_count,
            finding_count=len(findings),
            findings=tuple(findings),
        )

    def _audit_media_object(self, row: Any, *, include_ok: bool) -> StorageAuditResult:
        record_id = str(row["id"])
        world_id = _optional_str(row["world_id"])
        worldline_id = _optional_str(row["worldline_id"])
        expected_size = int(row["size_bytes"])
        expected_checksum = str(row["checksum_sha256"])
        findings: list[StorageAuditFinding] = []

        if len(expected_checksum) != 64:
            return _single_result(
                StorageAuditFinding(
                    record_kind="media_object",
                    record_id=record_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    status="media_object_invalid_checksum_metadata",
                    reason="Media object checksum metadata is invalid.",
                ),
                invalid_metadata_count=1,
            )

        try:
            data = self._media_storage.read_bytes(str(row["storage_uri"]))
        except Exception:  # noqa: BLE001
            return _single_result(
                StorageAuditFinding(
                    record_kind="media_object",
                    record_id=record_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    status="media_object_missing_or_unreadable",
                    reason="Media object payload is missing or unreadable.",
                ),
                missing_count=1,
            )

        actual_size = len(data)
        actual_checksum = hashlib.sha256(data).hexdigest()
        if actual_size != expected_size:
            findings.append(
                StorageAuditFinding(
                    record_kind="media_object",
                    record_id=record_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    status="media_object_size_mismatch",
                    reason="Media object payload size does not match recorded size.",
                    expected_size_bytes=expected_size,
                    actual_size_bytes=actual_size,
                ),
            )
        if actual_checksum != expected_checksum:
            findings.append(
                StorageAuditFinding(
                    record_kind="media_object",
                    record_id=record_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    status="media_object_checksum_mismatch",
                    reason="Media object payload checksum does not match recorded checksum.",
                ),
            )
        if findings:
            return StorageAuditResult(
                status="error",
                media_object_count=1,
                snapshot_payload_count=0,
                ok_count=0,
                missing_count=0,
                size_mismatch_count=sum(
                    1 for finding in findings if finding.status == "media_object_size_mismatch"
                ),
                checksum_mismatch_count=sum(
                    1
                    for finding in findings
                    if finding.status == "media_object_checksum_mismatch"
                ),
                unreadable_count=0,
                invalid_metadata_count=0,
                finding_count=len(findings),
                findings=tuple(findings),
            )
        ok_finding = (
            StorageAuditFinding(
                record_kind="media_object",
                record_id=record_id,
                world_id=world_id,
                worldline_id=worldline_id,
                status="ok",
                reason="Media object payload matches recorded size and checksum.",
            )
            if include_ok
            else None
        )
        return _ok_result(ok_finding)

    def _audit_snapshot_payload(self, row: Any, *, include_ok: bool) -> StorageAuditResult:
        record_id = str(row["id"])
        world_id = _optional_str(row["world_id"])
        worldline_id = _optional_str(row["worldline_id"])
        try:
            self._object_storage.read_json(str(row["payload_uri"]))
        except Exception:  # noqa: BLE001
            return _single_result(
                StorageAuditFinding(
                    record_kind="world_snapshot",
                    record_id=record_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    status="snapshot_payload_missing_or_unreadable",
                    reason="Snapshot object payload is missing or unreadable.",
                ),
                unreadable_count=1,
            )
        ok_finding = (
            StorageAuditFinding(
                record_kind="world_snapshot",
                record_id=record_id,
                world_id=world_id,
                worldline_id=worldline_id,
                status="ok",
                reason="Snapshot object payload is readable.",
            )
            if include_ok
            else None
        )
        return _ok_result(ok_finding)


def _single_result(
    finding: StorageAuditFinding,
    *,
    missing_count: int = 0,
    size_mismatch_count: int = 0,
    checksum_mismatch_count: int = 0,
    unreadable_count: int = 0,
    invalid_metadata_count: int = 0,
) -> StorageAuditResult:
    return StorageAuditResult(
        status="error",
        media_object_count=1 if finding.record_kind == "media_object" else 0,
        snapshot_payload_count=1 if finding.record_kind == "world_snapshot" else 0,
        ok_count=0,
        missing_count=missing_count,
        size_mismatch_count=size_mismatch_count,
        checksum_mismatch_count=checksum_mismatch_count,
        unreadable_count=unreadable_count,
        invalid_metadata_count=invalid_metadata_count,
        finding_count=1,
        findings=(finding,),
    )


def _ok_result(finding: StorageAuditFinding | None) -> StorageAuditResult:
    return StorageAuditResult(
        status="ok",
        media_object_count=(
            1 if finding is not None and finding.record_kind == "media_object" else 0
        ),
        snapshot_payload_count=1
        if finding is not None and finding.record_kind == "world_snapshot"
        else 0,
        ok_count=1,
        missing_count=0,
        size_mismatch_count=0,
        checksum_mismatch_count=0,
        unreadable_count=0,
        invalid_metadata_count=0,
        finding_count=1 if finding is not None else 0,
        findings=() if finding is None else (finding,),
    )


def _extend_capped(
    output: list[StorageAuditFinding],
    findings: tuple[StorageAuditFinding, ...],
    limit: int,
) -> None:
    remaining = limit - len(output)
    if remaining <= 0:
        return
    output.extend(findings[:remaining])


def _optional_str(value: object | None) -> str | None:
    return None if value is None else str(value)
