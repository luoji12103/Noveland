from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_DIR = REPO_ROOT / "docs/agent/operations/runbooks"

EXPECTED_RUNBOOKS = {
    "provider-outage.md",
    "quota-exhaustion.md",
    "media-job-stuck.md",
    "migration-failure.md",
    "backup-restore.md",
    "rollback.md",
    "worldline-restore.md",
    "secret-rotation.md",
    "private-beta-incident.md",
    "import-export-recovery.md",
    "provider-fallback.md",
}

REQUIRED_SECTIONS = (
    "## Purpose",
    "## Scope",
    "## Immediate Actions",
    "## Evidence To Collect",
    "## Redaction Rules",
    "## Escalation",
    "## Closeout",
)

REQUIRED_REDACTION_MARKERS = (
    "resolved secrets",
    "storage paths",
    "raw prompts",
    "raw outputs",
    "bytes",
    "base64",
    "invite tokens",
    "provider credentials",
    "prompt snapshot internals",
    "local model paths",
)


def test_v1_1_operational_runbooks_exist() -> None:
    actual = {path.name for path in RUNBOOK_DIR.glob("*.md") if path.name != "README.md"}

    assert EXPECTED_RUNBOOKS <= actual


def test_v1_1_operational_runbooks_keep_consistent_operator_structure() -> None:
    for filename in EXPECTED_RUNBOOKS:
        text = (RUNBOOK_DIR / filename).read_text(encoding="utf-8")

        for section in REQUIRED_SECTIONS:
            assert section in text, f"{section} missing from {filename}"

        for marker in REQUIRED_REDACTION_MARKERS:
            assert marker in text, f"{marker} missing from {filename}"


def test_v1_1_operational_runbooks_reference_existing_controls() -> None:
    expected_references = {
        "provider-outage.md": (
            "/provider-profiles/health",
            "/worlds/<world-id>/providers/quota-status",
            "docs/agent/operations/provider-lab.md",
        ),
        "quota-exhaustion.md": (
            "/worlds/<world-id>/providers/quota-status",
            "/worlds/<world-id>/providers/budget-policies",
        ),
        "media-job-stuck.md": (
            "/worlds/<world-id>/media/jobs",
            "/cancel",
            "/retry",
        ),
        "migration-failure.md": (
            "uv run alembic current",
            "uv run alembic upgrade head",
            "uv run noveland-backup-verify",
        ),
        "backup-restore.md": (
            "docs/agent/operations/backup-restore.md",
            "/runtime/storage-audit",
            "fresh local/single-host target",
        ),
        "rollback.md": (
            "git status --short --branch",
            "uv run noveland-backup-verify",
        ),
        "worldline-restore.md": (
            "/worlds/<world-id>/snapshots/integrity",
            "/worlds/<world-id>/player-sessions/resume",
        ),
        "secret-rotation.md": (
            "/provider-profiles/health",
            "auth_ref",
        ),
        "private-beta-incident.md": (
            "/worlds/<world-id>/private-beta/invites",
            "/worlds/<world-id>/beta-feedback/reports",
            "/observability/readiness/private-beta",
        ),
        "import-export-recovery.md": (
            "/worlds/<world-id>/package-contracts/validate",
            "/provider-config-export",
            "/authoring/import-runs/<run-id>/preview",
        ),
        "provider-fallback.md": (
            "/provider-profiles/health",
            "/worlds/<world-id>/providers/quota-status",
            "provider lab worktree",
        ),
    }

    for filename, references in expected_references.items():
        text = (RUNBOOK_DIR / filename).read_text(encoding="utf-8")
        for reference in references:
            assert reference in text, f"{reference} missing from {filename}"


def test_v1_1_operational_runbooks_preserve_recovery_boundaries() -> None:
    combined = "\n".join(
        (RUNBOOK_DIR / filename).read_text(encoding="utf-8") for filename in EXPECTED_RUNBOOKS
    )

    for expected in [
        "Do not edit database rows directly",
        "Do not mutate persona, memory, visual, voice, provider, or dialogue state directly.",
        "Do not import directly into canon",
        "If fallback would bypass quota, stop and file a blocker.",
    ]:
        assert expected in combined

    prohibited_patterns = [
        "disable csrf",
        "paste the api key",
        "commit .env",
        "bypass preview/review/apply",
        "fallback is automatic by default",
    ]
    normalized = combined.lower()
    for pattern in prohibited_patterns:
        assert pattern not in normalized
