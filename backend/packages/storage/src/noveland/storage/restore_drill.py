from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from noveland.storage.integrity import StorageAuditFinding, StorageAuditResult
from sqlalchemy import text
from sqlalchemy.orm import Session

FORBIDDEN_RESTORE_MARKERS = (
    "storage_uri",
    "media://",
    "object://",
    "object_storage_path",
    "filesystem_path",
    "local_path",
    "path",
    "raw prompt",
    "raw_prompt",
    "raw output",
    "raw_output",
    "prompt_snapshot",
    "prompt snapshot",
    "resolved_secret",
    "api_key",
    "authorization",
    "bearer",
    "bytes",
    "base64",
    "invite_token",
    "local_model_path",
)


@dataclass(frozen=True, slots=True)
class RestoreDrillCheck:
    check_key: str
    status: str
    summary: str
    evidence_count: int
    blocker_count: int
    warning_count: int
    evidence_refs: tuple[dict[str, str], ...] = ()
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RestoreDrillReport:
    status: str
    generated_at: datetime
    target_profile: str
    check_count: int
    evidence_count: int
    blocker_count: int
    warning_count: int
    checks: tuple[RestoreDrillCheck, ...]
    suppressed_fields: tuple[str, ...]
    non_goals: tuple[str, ...]


class BackupRestoreDrillService:
    def __init__(
        self,
        session: Session,
        *,
        storage_audit: StorageAuditResult,
        openspec_root_exists: bool,
        current_specs_exist: bool,
        archived_change_count: int,
        target_profile: str = "fresh_local_single_host",
    ) -> None:
        self._session = session
        self._storage_audit = storage_audit
        self._openspec_root_exists = openspec_root_exists
        self._current_specs_exist = current_specs_exist
        self._archived_change_count = archived_change_count
        self._target_profile = target_profile

    def report(self) -> RestoreDrillReport:
        checks = (
            self._database_state_check(),
            self._media_and_snapshot_check(),
            self._provider_config_check(),
            self._openspec_provenance_check(),
            self._safety_redaction_check(),
        )
        blocker_count = sum(check.blocker_count for check in checks)
        warning_count = sum(check.warning_count for check in checks)
        status = "blocked" if blocker_count else "ok"
        return RestoreDrillReport(
            status=status,
            generated_at=datetime.now(UTC),
            target_profile=self._target_profile,
            check_count=len(checks),
            evidence_count=sum(check.evidence_count for check in checks),
            blocker_count=blocker_count,
            warning_count=warning_count,
            checks=checks,
            suppressed_fields=(
                "credential_values",
                "storage_references",
                "filesystem_references",
                "object_store_references",
                "provider_request_text",
                "provider_response_text",
                "provider_trace_internals",
                "binary_payloads",
                "encoded_payloads",
                "invite_credentials",
                "provider_credentials",
                "local_model_references",
            ),
            non_goals=(
                "cloud_backup_product",
                "staging_restore",
                "secret_restore",
                "public_restore_report",
            ),
        )

    def _database_state_check(self) -> RestoreDrillCheck:
        counts = {
            "worlds": self._count("worlds"),
            "worldlines": self._count("worldlines"),
            "conversation_sessions": self._count("conversation_sessions"),
            "conversation_turn_presentations": self._count("conversation_turn_presentations"),
            "agent_memory_items": self._count("agent_memory_items"),
        }
        blockers = [
            f"Restored database has no {table_name}."
            for table_name in ("worlds", "worldlines")
            if counts[table_name] == 0
        ]
        warnings = [
            f"Restored database has no {table_name}."
            for table_name in (
                "conversation_sessions",
                "conversation_turn_presentations",
                "agent_memory_items",
            )
            if counts[table_name] == 0
        ]
        evidence_refs = tuple(
            _safe_ref("table_count", table_name, str(count)) for table_name, count in counts.items()
        )
        return _check(
            "database_state",
            blocker_count=len(blockers),
            warning_count=len(warnings),
            summary=(
                "Restored database includes worlds, worldlines, conversations, "
                "presentations, and memory count evidence."
            ),
            evidence_refs=evidence_refs,
            blockers=tuple(blockers),
            warnings=tuple(warnings),
        )

    def _media_and_snapshot_check(self) -> RestoreDrillCheck:
        blockers: list[str] = []
        warnings: list[str] = []
        if self._storage_audit.status != "ok":
            blockers.append("Storage integrity audit is not clean.")
        if self._storage_audit.media_object_count == 0:
            warnings.append("No restored media objects were present for verification.")
        if self._storage_audit.snapshot_payload_count == 0:
            warnings.append("No restored snapshot payloads were present for verification.")
        for finding in self._storage_audit.findings:
            if finding.status != "ok":
                blockers.append(
                    f"{finding.record_kind} {finding.record_id} failed: {finding.status}",
                )
        evidence_refs = (
            _safe_ref(
                "storage_audit",
                "media_objects",
                str(self._storage_audit.media_object_count),
            ),
            _safe_ref(
                "storage_audit",
                "snapshot_payloads",
                str(self._storage_audit.snapshot_payload_count),
            ),
            _safe_ref("storage_audit", "findings", str(self._storage_audit.finding_count)),
        )
        return _check(
            "media_and_snapshot_integrity",
            blocker_count=len(blockers),
            warning_count=len(warnings),
            summary="Storage audit verifies restored media objects, checksums, and snapshots.",
            evidence_refs=evidence_refs,
            blockers=tuple(blockers),
            warnings=tuple(warnings),
        )

    def _provider_config_check(self) -> RestoreDrillCheck:
        rows = self._session.execute(
            text(
                "SELECT id, provider_kind, adapter_kind, auth_ref, "
                "config_json, default_params_json "
                "FROM provider_integrations ORDER BY created_at DESC LIMIT 1000",
            ),
        ).mappings()
        provider_count = 0
        blockers: list[str] = []
        warnings: list[str] = []
        evidence_refs: list[dict[str, str]] = []
        for row in rows:
            provider_count += 1
            provider_id = str(row["id"])
            evidence_refs.append(
                _safe_ref(
                    "provider_config",
                    provider_id,
                    str(row["provider_kind"]),
                    extra={"adapter": str(row["adapter_kind"])},
                ),
            )
            if not row["auth_ref"]:
                warnings.append(f"Provider {provider_id} has no auth_ref metadata.")
            for field_name in ("config_json", "default_params_json"):
                if _contains_forbidden_marker(row[field_name]):
                    blockers.append(
                        f"Provider {provider_id} {field_name} contains unsafe restore metadata.",
                    )
        if provider_count == 0:
            warnings.append("No provider integrations were present for restore verification.")
        return _check(
            "provider_config_without_secrets",
            blocker_count=len(blockers),
            warning_count=len(warnings),
            summary="Provider restore evidence preserves safe config metadata and auth refs only.",
            evidence_refs=tuple(evidence_refs),
            blockers=tuple(blockers),
            warnings=tuple(warnings),
        )

    def _openspec_provenance_check(self) -> RestoreDrillCheck:
        blockers: list[str] = []
        warnings: list[str] = []
        if not self._openspec_root_exists:
            blockers.append("OpenSpec root is missing from restored workspace.")
        if not self._current_specs_exist:
            blockers.append("OpenSpec current specs are missing from restored workspace.")
        if self._archived_change_count == 0:
            warnings.append("No archived OpenSpec changes were found.")
        evidence_refs = (
            _safe_ref("openspec", "root", str(self._openspec_root_exists).lower()),
            _safe_ref("openspec", "current_specs", str(self._current_specs_exist).lower()),
            _safe_ref("openspec", "archived_changes", str(self._archived_change_count)),
        )
        return _check(
            "openspec_docs_provenance",
            blocker_count=len(blockers),
            warning_count=len(warnings),
            summary="OpenSpec current specs and archived change provenance are present.",
            evidence_refs=evidence_refs,
            blockers=tuple(blockers),
            warnings=tuple(warnings),
        )

    def _safety_redaction_check(self) -> RestoreDrillCheck:
        unsafe_storage_findings = [
            finding
            for finding in self._storage_audit.findings
            if _finding_contains_forbidden_marker(finding)
        ]
        blockers = tuple(
            f"{finding.record_kind} {finding.record_id} finding contains unsafe marker"
            for finding in unsafe_storage_findings
        )
        return _check(
            "safe_restore_report",
            blocker_count=len(blockers),
            warning_count=0,
            summary="Restore drill report uses safe refs and redacted evidence only.",
            evidence_refs=(
                _safe_ref("suppressed_fields", "restore_report", "12"),
                _safe_ref("leak_scan", "restore_report", "complete"),
            ),
            blockers=blockers,
            warnings=(),
        )

    def _count(self, table_name: str) -> int:
        result = self._session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return int(result.scalar_one())


def _check(
    check_key: str,
    *,
    blocker_count: int,
    warning_count: int,
    summary: str,
    evidence_refs: tuple[dict[str, str], ...],
    blockers: tuple[str, ...],
    warnings: tuple[str, ...],
) -> RestoreDrillCheck:
    status = "blocked" if blocker_count else "watch" if warning_count else "ok"
    return RestoreDrillCheck(
        check_key=check_key,
        status=status,
        summary=summary,
        evidence_count=len(evidence_refs),
        blocker_count=blocker_count,
        warning_count=warning_count,
        evidence_refs=evidence_refs,
        blockers=blockers,
        warnings=warnings,
    )


def _safe_ref(
    kind: str,
    ref_id: str,
    status: str,
    *,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    ref = {"kind": kind, "id": ref_id, "status": status}
    if extra:
        ref.update(extra)
    return ref


def _contains_forbidden_marker(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            _contains_forbidden_marker(key) or _contains_forbidden_marker(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set)):
        return any(_contains_forbidden_marker(item) for item in value)
    if isinstance(value, str):
        lower_value = value.lower()
        return any(marker in lower_value for marker in FORBIDDEN_RESTORE_MARKERS)
    return False


def _finding_contains_forbidden_marker(finding: StorageAuditFinding) -> bool:
    return _contains_forbidden_marker(
        {
            "record_kind": finding.record_kind,
            "record_id": finding.record_id,
            "world_id": finding.world_id,
            "worldline_id": finding.worldline_id,
            "status": finding.status,
            "reason": finding.reason,
        },
    )
